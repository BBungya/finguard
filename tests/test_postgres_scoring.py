"""실제 PostgreSQL에서 저장·재시작·경합·롤백을 확인한다."""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
pytest.importorskip("fastapi")
pytest.importorskip("sklearn")

from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from test_score_api import ExampleModel, payload

from finguard import database
from finguard.api import ScoreRequest, create_app
from finguard.database import PostgresScoringService, initialize
from finguard.scoring import InMemoryScoringService, TransactionConflict


@pytest.fixture
def database_url():
    base = os.environ.get("TEST_DATABASE_URL")
    if not base:
        pytest.skip("실제 DB 검증에는 TEST_DATABASE_URL이 필요합니다.")
    # 개발용 테이블을 지우지 않고 테스트마다 별도 스키마를 사용한다.
    schema = "test_" + uuid4().hex
    with psycopg.connect(base, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    url = make_conninfo(base, options=f"-c search_path={schema}")
    try:
        initialize(url)
        initialize(url)
        yield url
    finally:
        with psycopg.connect(base, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


def count_rows(url):
    with psycopg.connect(url) as connection:
        return connection.execute(
            "SELECT count(*) FROM scored_transactions"
        ).fetchone()[0]


def test_restart_preserves_original_response_and_history(database_url):
    first_model = ExampleModel()
    with TestClient(create_app(first_model, database_url=database_url)) as client:
        first = client.post("/transactions/score", json=payload())
        assert first.status_code == 200
    restarted_model = ExampleModel()
    restarted_model.version = "new-model"
    with TestClient(create_app(restarted_model, database_url=database_url)) as client:
        duplicate = client.post("/transactions/score", json=payload(amount="10.0"))
        assert duplicate.json() == first.json()
        assert restarted_model.calls == 0
        second = client.post("/transactions/score", json=payload("second"))
        assert second.json()["features"]["count_7d"] == 1
        assert second.json()["model_version"] == "new-model"
        assert (
            client.post(
                "/transactions/score", json=payload(card_id="different-card")
            ).status_code
            == 409
        )
        assert (
            client.post("/transactions/score", json=payload(amount="11.00")).status_code
            == 409
        )
        assert (
            client.post(
                "/transactions/score", json=payload("older", "2025-12-31 10:00:00")
            ).status_code
            == 409
        )
    assert count_rows(database_url) == 2


@pytest.mark.parametrize("at_commit", [False, True])
def test_insert_and_commit_failure_leave_no_history(database_url, at_commit):
    # 저장할 때와 COMMIT할 때 각각 실제 DB 오류를 발생시킨다.
    with psycopg.connect(database_url) as connection:
        connection.execute("""
            CREATE FUNCTION reject_test_transaction() RETURNS trigger AS $$
            BEGIN
                IF NEW.transaction_id = 'failed' THEN
                    RAISE EXCEPTION 'injected storage failure';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        if at_commit:
            connection.execute("""
                CREATE CONSTRAINT TRIGGER reject_test_transaction
                AFTER INSERT ON scored_transactions
                DEFERRABLE INITIALLY DEFERRED
                FOR EACH ROW EXECUTE FUNCTION reject_test_transaction()
            """)
        else:
            connection.execute("""
                CREATE TRIGGER reject_test_transaction BEFORE INSERT
                ON scored_transactions FOR EACH ROW
                EXECUTE FUNCTION reject_test_transaction()
            """)
    with TestClient(create_app(ExampleModel(), database_url=database_url)) as client:
        assert client.post("/transactions/score", json=payload()).status_code == 200
        future = payload("failed", "2026-01-10 10:00:00")
        failed = client.post("/transactions/score", json=future)
        assert failed.status_code == 503
        assert failed.json()["detail"] == "database_unavailable"
        assert count_rows(database_url) == 1
        second = client.post(
            "/transactions/score", json=payload("second", "2026-01-01 10:30:00")
        )
        assert second.json()["features"]["count_7d"] == 1
        with psycopg.connect(database_url) as connection:
            connection.execute(
                "DROP TRIGGER reject_test_transaction ON scored_transactions"
            )
        assert client.post("/transactions/score", json=future).status_code == 200
    assert count_rows(database_url) == 3


def test_connection_and_model_failure_do_not_fall_back_to_memory(
    database_url, monkeypatch
):
    model = ExampleModel()
    with TestClient(create_app(model, database_url=database_url)) as client:
        with monkeypatch.context() as patch:

            def disconnected(*args, **kwargs):
                raise psycopg.OperationalError("injected disconnect")

            patch.setattr(database, "connect", disconnected)
            assert client.post("/transactions/score", json=payload()).status_code == 503
        assert model.calls == 0
        model.fail = True
        assert client.post("/transactions/score", json=payload()).status_code == 503
        assert count_rows(database_url) == 0
        model.fail = False
        response = client.post("/transactions/score", json=payload())
        assert response.json()["features"]["count_7d"] == 0


def test_separate_services_serialize_duplicates_and_same_card(database_url):
    model = ExampleModel()
    services = [PostgresScoringService(model, database_url) for _ in range(8)]
    transaction = ScoreRequest(**payload()).transaction()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda service: service.score(transaction), services))
    assert all(result == results[0] for result in results)
    assert model.calls == 1
    assert count_rows(database_url) == 1

    def score_next(index):
        transaction = ScoreRequest(**payload(f"next-{index}")).transaction()
        return services[index].score(transaction)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(score_next, range(8)))
    assert sorted(result.features.count_7d for result in results) == list(range(1, 9))
    assert count_rows(database_url) == 9


def test_conflicting_same_id_on_different_cards_commits_once(database_url):
    services = [PostgresScoringService(ExampleModel(), database_url) for _ in range(2)]

    def score(index):
        transaction = ScoreRequest(**payload(card_id=f"card-{index}")).transaction()
        try:
            return services[index].score(transaction)
        except TransactionConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(score, range(2)))
    assert sum(result is not None for result in results) == 1
    assert count_rows(database_url) == 1


def test_database_history_matches_memory_at_window_boundaries(database_url):
    memory = InMemoryScoringService(ExampleModel())
    postgres = PostgresScoringService(ExampleModel(), database_url)
    samples = [
        payload("minimum", "0001-01-01 00:00:00", card_id="ancient"),
        payload("first", "2026-01-01 10:00:00", amount="10.01"),
        payload("same-time", "2026-01-01 10:00:00", amount="30.03"),
        payload("one-hour", "2026-01-01 11:00:00"),
        payload("after-hour", "2026-01-01 11:00:01"),
        payload("seven-days", "2026-01-08 10:00:00"),
        payload("after-seven-days", "2026-01-08 10:00:01"),
        payload("expired", "2026-02-01 10:00:00"),
        payload("other", "2026-01-01 10:00:00", card_id="other"),
    ]
    for values in samples:
        transaction = ScoreRequest(**values).transaction()
        expected = memory.score(transaction)
        assert postgres.score(transaction) == expected
        # JSONB에서 다시 읽을 때에도 Decimal과 버전이 보존되어야 한다.
        assert postgres.score(transaction) == expected
