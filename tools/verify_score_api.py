"""실제 모델·HTTP·DB·Redis를 연결해 정합성과 로컬 응답 시간을 확인한다."""

import argparse
import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from finguard.api import ScoreRequest, ScoreResponse
from finguard.database import (
    PostgresScoringService,
    initialize,
    stored_result,
    stored_transaction,
)
from finguard.features import FEATURE_VERSION
from finguard.history_cache import RedisHistoryCache
from finguard.scoring import POLICY_VERSION, InMemoryScoringService, ScoringModel

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


class Server:
    """사용자 API와 다른 포트에서 검증용 단일 프로세스를 실행한다."""

    def __init__(self, database_url, redis_url, model_path, log_path):
        self.url = f"http://127.0.0.1:{free_port()}"
        self.environment = {
            **os.environ,
            "DATABASE_URL": database_url,
            "REDIS_URL": redis_url,
            "SCORING_MODEL_PATH": str(model_path),
        }
        self.log_path = log_path
        self.process = None
        self.log = None

    def __enter__(self):
        self.log = self.log_path.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "finguard.api:app",
                "--host",
                "127.0.0.1",
                "--port",
                self.url.rsplit(":", 1)[1],
                "--workers",
                "1",
                "--log-level",
                "error",
            ],
            cwd=ROOT,
            env=self.environment,
            stdout=self.log,
            stderr=self.log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError(f"검증 서버 시작 실패. 로그: {self.log_path}")
                try:
                    with urllib.request.urlopen(self.url + "/docs", timeout=1):
                        return self
                except OSError:
                    time.sleep(0.1)
            raise TimeoutError("검증 서버 시작 제한 시간 초과")
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log is not None:
            self.log.close()


def send(server, payload, expected_status=200):
    request = urllib.request.Request(
        server.url + "/transactions/score",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        status, body = response.status, json.load(response)
    elapsed = (time.perf_counter() - started) * 1000
    if status != expected_status:
        raise AssertionError(f"예상 HTTP {expected_status}, 실제 {status}")
    if status == 200 and body["transaction_id"] != payload["transaction_id"]:
        raise AssertionError("다른 거래의 응답을 반환함")
    return elapsed, body


def payload(phase, kind, index, cards):
    # 같은 카드의 동시 요청은 처리 순서가 달라도 같은 이력을 만들도록
    # 같은 시각·금액·업종을 사용한다. 성능 측정용 합성 거래다.
    return {
        "transaction_id": f"{phase}-{kind}-{index}",
        "card_id": f"{phase}-card-{index % cards}",
        "occurred_at": "2026-01-01T10:00:00",
        "amount": "10.00",
        "category": "shopping_net",
    }


def measure(phase, servers, args, model, database_url):
    service = PostgresScoringService(model, database_url)
    for index in range(args.cards * args.history_per_card):
        service.score(
            ScoreRequest(**payload(phase, "seed", index, args.cards)).transaction()
        )
    # 두 모드 모두 같은 카드당 이력과 준비 요청을 사용한다.
    for index in range(args.cards):
        send(servers[index % len(servers)], payload(phase, "warm", index, args.cards))

    def one(index):
        return send(
            servers[index % len(servers)], payload(phase, "measured", index, args.cards)
        )

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        responses = list(pool.map(one, range(args.requests)))
    seconds = time.perf_counter() - started
    # 응답 시간 측정이 끝난 뒤 HTTP 내용과 DB의 최초 응답도 비교한다.
    with psycopg.connect(database_url) as connection:
        stored = dict(
            connection.execute(
                "SELECT transaction_id, result FROM scored_transactions "
                "WHERE transaction_id = ANY(%s)",
                ([body["transaction_id"] for _, body in responses],),
            ).fetchall()
        )
    for _, body in responses:
        if (
            ScoreResponse(**stored[body["transaction_id"]]).model_dump(mode="json")
            != body
        ):
            raise AssertionError("HTTP 응답과 DB 최초 응답이 다름")
    latencies = sorted(elapsed for elapsed, _ in responses)
    return {
        "mode": phase,
        "requests": args.requests,
        "successful_requests": len(responses),
        "api_processes": len(servers),
        "concurrency": args.concurrency,
        "elapsed_seconds": round(seconds, 3),
        "throughput_rps": round(args.requests / seconds, 2),
        "p50_ms": round(median(latencies), 2),
        "p95_ms": round(latencies[math.ceil(0.95 * len(latencies)) - 1], 2),
        "max_ms": round(max(latencies), 2),
    }


def verify_replay(model, database_url):
    """DB가 확정한 순서로 처음부터 계산해 당시 응답·버전을 대조한다."""
    reference = InMemoryScoringService(model)
    with psycopg.connect(database_url, row_factory=psycopg.rows.dict_row) as connection:
        rows = connection.execute(
            "SELECT * FROM scored_transactions ORDER BY sequence"
        ).fetchall()
    for row in rows:
        expected = reference.score(stored_transaction(row))
        actual = stored_result(row["result"])
        if abs(actual.risk_score - expected.risk_score) > 1e-7:
            raise AssertionError("저장 점수가 순차 계산과 다름")
        if replace(actual, risk_score=expected.risk_score) != expected:
            raise AssertionError("저장 이력·조사 여부·군집·버전이 순차 계산과 다름")
    return len(rows)


def write_report(report, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# 거래 API 통합 검증과 로컬 성능 기준선",
        "",
        f"측정 시각: {report['measured_at_kst']}",
        "",
        "## 측정 조건",
        "",
        f"- Python {report['python']} / {report['os']}",
        f"- PostgreSQL {report['postgres_version']} / Redis {report['redis_version']}",
        f"- 모델 SHA-256: `{report['model_version']}`",
        f"- 피처 버전: `{report['feature_version']}` / 정책 버전: `{report['policy_version']}`",
        f"- 카드 {report['cards']}개, 카드당 사전 이력 {report['history_per_card']}건과 준비 요청 1건",
        "- 모드별 독립 API 프로세스 2개, 같은 모델·요청 수·동시 요청 수",
        "- 금액 10.00·동일 시각·동일 업종의 합성 거래. 실제 사기 탐지 정확도 평가는 포함하지 않음",
        "",
        "## 응답 시간",
        "",
        "| 모드 | 성공/요청 | 동시 요청 | 처리량(건/초) | 중앙값(ms) | p95(ms) | 최대(ms) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in report["measurements"]:
        lines.append(
            f"| {result['mode']} | {result['successful_requests']}/{result['requests']} | "
            f"{result['concurrency']} | {result['throughput_rps']} | {result['p50_ms']} | "
            f"{result['p95_ms']} | {result['max_ms']} |"
        )
    lines += [
        "",
        (
            "처리량은 측정 요청 수를 전체 실행 시간으로 나눈 값이다. 중앙값은 중간 응답 시간이고, "
            "p95는 응답 시간순으로 95% 위치에 해당하는 값이다. 클라이언트 작업 대기열에 머문 시간은 "
            "개별 응답 시간에 포함하지 않는다. 준비 요청과 모델 시작 시간도 측정에서 제외했다."
        ),
        "",
        "## 정합성과 복구",
        "",
        f"- DB 확정 순서로 {report['replayed_transactions']}건을 다시 계산해 점수·피처·판단·버전이 일치함",
        "- 두 API 프로세스에 같은 거래를 동시에 8번 보내도 DB에 한 건만 추가됨",
        "- 같은 ID의 내용 변경은 409, 잘못된 금액은 422, 늦은 과거 거래는 409임",
        "- Redis 접속 불가 상태에서도 DB에 거래를 저장하고 같은 요청의 최초 응답을 반환함",
        "- API 재시작 후 최초 응답이 유지되고, 캐시 유실 후 신규 거래에서 DB로 복구함",
        "- 외부 LLM 호출 없이 실행함. 개발 거래와 다른 DB 스키마·Redis 키를 사용 후 정리함",
        "",
        "## 해석 범위",
        "",
        (
            "이번 결과는 로컬의 작은 합성 작업량을 한 번 측정한 기준선이다. 모드 실행 순서는 DB 단독, "
            "Redis 공유 순서이며 서버 부하·DB 연결·운영체제 캐시의 영향을 받는다. Redis를 사용해도 "
            "중복 확인·최신 거래 조회·DB 저장과 이력 직렬화 비용은 남는다. 이 수치로 운영 처리량이나 "
            "Redis의 일반적인 성능 우위를 단정하지 않는다. 큰 이력·여러 반복·실제 환경의 부하 시험은 후속 작업이다."
        ),
        "",
    ]
    output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--redis-url", default=os.environ.get("REDIS_URL"))
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(
            os.environ.get(
                "SCORING_MODEL_PATH",
                "artifacts/behavior_ablation/selected_model.joblib",
            )
        ),
    )
    parser.add_argument("--requests", type=int, default=64)
    parser.add_argument("--cards", type=int, default=4)
    parser.add_argument("--history-per-card", type=int, default=32)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "reports/score_api_verification"
    )
    args = parser.parse_args()
    if not args.database_url or not args.redis_url:
        parser.error("DATABASE_URL과 REDIS_URL을 설정하세요.")
    if min(args.requests, args.cards, args.history_per_card, args.concurrency) < 1:
        parser.error("요청·카드·이력·동시 요청 수는 모두 양수여야 합니다.")
    schema = "verify_" + uuid4().hex
    url = make_conninfo(args.database_url, options=f"-c search_path={schema}")
    log_directory = ROOT / ".uv-cache" / schema
    log_directory.mkdir(parents=True, exist_ok=True)
    model = ScoringModel(args.model.resolve())
    cache = RedisHistoryCache(args.redis_url, url)
    created = False
    try:
        with psycopg.connect(args.database_url, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
            )
        created = True
        initialize(url)
        cache.client.ping()
        measurements = []
        for phase, redis_url in (
            ("postgres_only", ""),
            ("redis_shared", args.redis_url),
        ):
            print(f"{phase}: 독립 API 2개로 측정 시작", flush=True)
            with ExitStack() as stack:
                servers = [
                    stack.enter_context(
                        Server(
                            url,
                            redis_url,
                            args.model.resolve(),
                            log_directory / f"{phase}-{index}.log",
                        )
                    )
                    for index in range(2)
                ]
                measurements.append(measure(phase, servers, args, model, url))
                if phase == "redis_shared":
                    duplicate = payload(phase, "duplicate", 0, args.cards)
                    with ThreadPoolExecutor(max_workers=8) as pool:
                        duplicates = list(
                            pool.map(
                                lambda index, endpoints=servers, request=duplicate: (
                                    send(endpoints[index % 2], request)[1]
                                ),
                                range(8),
                            )
                        )
                    assert all(item == duplicates[0] for item in duplicates)
                    with psycopg.connect(url) as connection:
                        count = connection.execute(
                            "SELECT count(*) FROM scored_transactions WHERE transaction_id = %s",
                            (duplicate["transaction_id"],),
                        ).fetchone()[0]
                    assert count == 1
                    send(servers[0], {**duplicate, "amount": "20.00"}, 409)
                    send(
                        servers[0],
                        {**duplicate, "transaction_id": "invalid", "amount": "0"},
                        422,
                    )
                    send(
                        servers[0],
                        {
                            **duplicate,
                            "transaction_id": "late",
                            "occurred_at": "2025-12-31T10:00:00",
                        },
                        409,
                    )

        print("Redis 접속 실패·API 재시작·캐시 복구 검증 시작", flush=True)
        outage = payload("redis_shared", "outage", 0, args.cards)
        with Server(
            url,
            f"redis://127.0.0.1:{free_port()}/0",
            args.model.resolve(),
            log_directory / "outage.log",
        ) as server:
            first = send(server, outage)[1]
            assert send(server, outage)[1] == first
        cache.client.delete(cache.key(outage["card_id"]))
        with Server(
            url, args.redis_url, args.model.resolve(), log_directory / "recovery.log"
        ) as server:
            assert send(server, outage)[1] == first
            restored = send(server, payload("redis_shared", "restored", 0, args.cards))[
                1
            ]
            assert restored["features"]["count_7d"] == first["features"]["count_7d"] + 1
            assert cache.client.exists(cache.key(outage["card_id"]))
        print("DB 순서로 전체 점수·피처·버전 대조 시작", flush=True)
        replayed = verify_replay(model, url)
        with psycopg.connect(url) as connection:
            postgres_version = connection.execute("SHOW server_version").fetchone()[0]
        report = {
            "measured_at_kst": datetime.now(timezone(timedelta(hours=9))).isoformat(),
            "python": platform.python_version(),
            "os": platform.system() + " " + platform.release(),
            "postgres_version": postgres_version,
            "redis_version": cache.client.info("server")["redis_version"],
            "model_version": model.version,
            "feature_version": FEATURE_VERSION,
            "policy_version": POLICY_VERSION,
            "cards": args.cards,
            "history_per_card": args.history_per_card,
            "measurements": measurements,
            "replayed_transactions": replayed,
            "checks": {
                "concurrent_duplicates": True,
                "input_conflicts": True,
                "redis_unavailable": True,
                "restart": True,
                "cache_recovery": True,
                "score_feature_version_parity": True,
                "llm_calls": 0,
            },
        }
    finally:
        try:
            for key in cache.client.scan_iter(match=cache.prefix + "*"):
                cache.client.delete(key)
        finally:
            cache.close()
            if created:
                with psycopg.connect(args.database_url, autocommit=True) as connection:
                    connection.execute(
                        sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
                    )
    write_report(report, args.output)
    print(
        f"검증 완료: {replayed}건 일치. 결과: {args.output.with_suffix('.md')}",
        flush=True,
    )


if __name__ == "__main__":
    main()
