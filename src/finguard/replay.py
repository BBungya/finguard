"""CSV 검증 결과를 기록하고 거래를 시간순으로 로컬 출력한다."""

import argparse
import csv
import json
import math
import sys
import time
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from finguard.transactions import REQUIRED_COLUMNS, Transaction


@dataclass
class ReplayInput:
    transactions: list[Transaction] = field(default_factory=list)
    rows_read: int = 0
    out_of_order: int = 0
    skipped: Counter[str] = field(default_factory=Counter)
    issues: list[dict[str, int | str]] = field(default_factory=list)

    def skip(self, line_number: int, reason: str) -> None:
        self.skipped[reason.split(":", 1)[0]] += 1
        self.issues.append({"line": line_number, "reason": reason})


def load_transactions(path: Path) -> ReplayInput:
    result = ReplayInput()
    seen_ids: set[str] = set()
    latest_time: datetime | None = None

    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source, strict=True)
        header = next(reader, [])
        if len(header) != len(set(header)):
            raise ValueError("duplicate_csv_columns")
        missing_columns = sorted(REQUIRED_COLUMNS.difference(header))
        if missing_columns:
            raise ValueError(f"missing_csv_columns: {', '.join(missing_columns)}")

        while True:
            line_number = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            result.rows_read += 1
            if len(row) != len(header):
                result.skip(line_number, "invalid_column_count")
                continue
            try:
                transaction = Transaction.from_csv_row(dict(zip(header, row)))
            except ValueError as error:
                result.skip(line_number, str(error))
                continue

            # 검증에 통과한 첫 행을 보존한다. 잘못된 행은 ID를 선점하지 않는다.
            if transaction.transaction_id in seen_ids:
                result.skip(line_number, "duplicate_transaction_id")
                continue
            seen_ids.add(transaction.transaction_id)

            # 파일에서 뒤늦게 나온 과거 거래는 집계한 뒤 제시간 위치에 배치한다.
            if latest_time is None or transaction.occurred_at >= latest_time:
                latest_time = transaction.occurred_at
            else:
                result.out_of_order += 1
            result.transactions.append(transaction)

    # Python의 안정 정렬은 같은 시각의 거래에 CSV의 행 순서를 유지한다.
    result.transactions.sort(key=lambda transaction: transaction.occurred_at)
    return result


def replay(transactions: list[Transaction], speed: float = 0) -> Iterator[Transaction]:
    if not math.isfinite(speed) or speed < 0:
        raise ValueError("speed_must_be_finite_and_nonnegative")
    previous: Transaction | None = None
    for transaction in transactions:
        if speed and previous is not None:
            gap = (transaction.occurred_at - previous.occurred_at).total_seconds()
            delay = gap / speed
            if delay:
                time.sleep(delay)
        yield transaction
        previous = transaction


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CSV 거래를 검증해 시간순으로 로컬 출력합니다."
    )
    parser.add_argument("csv_file", type=Path)
    parser.add_argument(
        "--speed", type=float, default=0, help="0은 즉시, 1은 실제 간격, 2는 2배속"
    )
    args = parser.parse_args()
    if not math.isfinite(args.speed) or args.speed < 0:
        parser.error("--speed는 유한한 0 이상의 숫자여야 합니다.")

    try:
        loaded = load_transactions(args.csv_file)
        for transaction in replay(loaded.transactions, args.speed):
            # 거래와 검증 결과를 각각 stdout과 stderr로 보내 따로 저장할 수 있게 한다.
            event = {
                "transaction_id": transaction.transaction_id,
                "occurred_at": transaction.occurred_at.isoformat(),
                "card_id": transaction.card_id,
                "category": transaction.category,
                "amount": format(transaction.amount, "f"),
                "is_fraud": transaction.is_fraud,
            }
            print(json.dumps(event), flush=True)
    except (OSError, ValueError, csv.Error, OverflowError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2

    summary = {
        "rows_read": loaded.rows_read,
        "emitted": len(loaded.transactions),
        "out_of_order": loaded.out_of_order,
        "skipped": dict(loaded.skipped),
        "issues": loaded.issues,
        "settings": {"speed": args.speed, "same_time_order": "csv_order"},
    }
    print(json.dumps(summary), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
