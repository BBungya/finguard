"""PostgreSQL 원본 기록과 선택적인 Redis 이력 캐시를 연결한다."""

import json
import os
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from importlib.resources import files

import psycopg
from psycopg import IsolationLevel
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from finguard.features import AMOUNT_WINDOW, HistoryFeatureCalculator, HistoryFeatures
from finguard.scoring import (
    ScoreResult,
    ScoringUnavailable,
    TransactionConflict,
    evaluate,
)
from finguard.transactions import Transaction


@contextmanager
def connect(database_url):
    connection = psycopg.connect(
        database_url,
        connect_timeout=3,
        row_factory=dict_row,
    )
    try:
        connection.isolation_level = IsolationLevel.READ_COMMITTED
        with connection:
            yield connection
    finally:
        # 최종 저장 확정 중 오류가 나더라도 연결을 반드시 정리한다.
        connection.close()


def initialize(database_url):
    """최초 저장 테이블을 준비한다. 기존 거래는 변경하지 않는다."""
    schema = (
        files("finguard")
        .joinpath("sql/001_scored_transactions.sql")
        .read_text(encoding="utf-8")
    )
    with connect(database_url) as connection:
        connection.execute(schema)


def stored_transaction(row):
    return Transaction(
        transaction_id=row["transaction_id"],
        occurred_at=row["occurred_at"],
        card_id=row["card_id"],
        category=row["category"],
        amount=row["amount"],
        is_fraud=None,
    )


def stored_result(data):
    # 평균과 표준편차는 문자열로 저장해 Decimal의 자릿수를 보존한다.
    values = dict(data["features"])
    for key in ("mean_amount_7d", "std_amount_7d"):
        if values[key] is not None:
            values[key] = Decimal(values[key])
    return ScoreResult(**{**data, "features": HistoryFeatures(**values)})


def dump_result(data):
    return json.dumps(data, default=str, allow_nan=False)


class PostgresScoringService:
    def __init__(self, model, database_url, *, history_cache=None):
        self.model = model
        self.database_url = database_url
        self.history_cache = history_cache

    def load_history(self, connection, transaction):
        calculator = HistoryFeatureCalculator()
        # 7일보다 오래된 거래는 이번 계산에서 제외하되 원본은 남긴다.
        start = datetime.min
        if transaction.occurred_at - start >= AMOUNT_WINDOW:
            start = transaction.occurred_at - AMOUNT_WINDOW
        rows = connection.execute(
            "SELECT transaction_id, card_id, occurred_at, amount, category "
            "FROM scored_transactions WHERE card_id = %s AND occurred_at >= %s "
            "ORDER BY occurred_at, sequence",
            (transaction.card_id, start),
        )
        for row in rows:
            calculator.process(stored_transaction(row))
        return calculator

    def score(self, transaction: Transaction) -> ScoreResult:
        try:
            # 블록을 정상적으로 벗어나야 COMMIT된다. 실패하면 전부 취소한다.
            with connect(self.database_url) as connection:
                connection.execute("SET LOCAL lock_timeout = '10s'")
                connection.execute("SET LOCAL statement_timeout = '30s'")
                # ID 잠금과 카드 잠금의 영역을 분리하고 항상 같은 순서로 잡는다.
                # 여러 API 프로세스에서도 같은 ID와 같은 카드 처리를 순서화한다.
                connection.execute(
                    "SELECT pg_advisory_xact_lock(1, hashtext(%s))",
                    (transaction.transaction_id,),
                )
                previous = connection.execute(
                    "SELECT * FROM scored_transactions WHERE transaction_id = %s",
                    (transaction.transaction_id,),
                ).fetchone()
                if previous is not None:
                    if stored_transaction(previous) != transaction:
                        raise TransactionConflict("transaction_id_payload_conflict")
                    return stored_result(previous["result"])

                connection.execute(
                    "SELECT pg_advisory_xact_lock(2, hashtext(%s))",
                    (transaction.card_id,),
                )
                latest = connection.execute(
                    "SELECT occurred_at, sequence FROM scored_transactions "
                    "WHERE card_id = %s "
                    "ORDER BY occurred_at DESC, sequence DESC LIMIT 1",
                    (transaction.card_id,),
                ).fetchone()
                if latest and transaction.occurred_at < latest["occurred_at"]:
                    raise TransactionConflict("out_of_order_card_transaction")

                calculator = None
                if latest and self.history_cache is not None:
                    # DB 잠금 아래에서 마지막 확정 거래 번호와 일치할 때만 사용한다.
                    calculator = self.history_cache.load(
                        transaction.card_id, latest["sequence"], latest["occurred_at"]
                    )
                if calculator is None:
                    calculator = self.load_history(connection, transaction)
                features = calculator.process(transaction)
                result = evaluate(self.model, transaction, features)
                saved = connection.execute(
                    "INSERT INTO scored_transactions "
                    "(transaction_id, card_id, occurred_at, amount, category, result) "
                    "VALUES (%s, %s, %s, %s, %s, %s) RETURNING sequence",
                    (
                        transaction.transaction_id,
                        transaction.card_id,
                        transaction.occurred_at,
                        transaction.amount,
                        transaction.category,
                        Jsonb(asdict(result), dumps=dump_result),
                    ),
                ).fetchone()
            # COMMIT 실패도 503으로 바꾸도록 with 바깥에서 응답을 반환한다.
            if self.history_cache is not None:
                # 반드시 DB 확정 뒤 발행한다. 늦게 끝난 이전 발행은 Redis가 거부한다.
                self.history_cache.publish(
                    transaction.card_id, saved["sequence"], calculator
                )
            return result
        except psycopg.Error as error:
            raise ScoringUnavailable("database_unavailable") from error


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL을 설정한 뒤 실행하세요.")
    initialize(database_url)
    print("PostgreSQL 거래 저장 테이블을 준비했습니다.")
