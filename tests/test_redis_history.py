"""실제 PostgreSQL과 Redis에서 카드 이력 공유·장애 복구를 검증한다."""

import json
import os
from concurrent.futures import ThreadPoolExecutor

import pytest

redis = pytest.importorskip("redis")
psycopg = pytest.importorskip("psycopg")
pytest.importorskip("fastapi")
pytest.importorskip("sklearn")

from fastapi.testclient import TestClient
from test_postgres_scoring import count_rows
from test_score_api import ExampleModel, payload

from finguard import database
from finguard.api import ScoreRequest, create_app
from finguard.database import PostgresScoringService
from finguard.features import HistoryFeatureCalculator
from finguard.history_cache import CACHE_TTL_SECONDS, RedisHistoryCache
from finguard.scoring import InMemoryScoringService, ScoringUnavailable


@pytest.fixture
def cache(database_url):
    url = os.environ.get("TEST_REDIS_URL")
    if not url:
        pytest.skip("실제 Redis 검증에는 TEST_REDIS_URL이 필요합니다.")
    instance = RedisHistoryCache(url, database_url)
    instance.client.ping()
    try:
        yield instance
    finally:
        # 테스트 전용 DB 스키마에서 파생한 키만 지운다. FLUSHDB는 사용하지 않는다.
        for key in instance.client.scan_iter(match=instance.prefix + "*"):
            instance.client.delete(key)
        instance.close()


def transaction(identifier="first", time="2026-01-01 10:00:00", **overrides):
    return ScoreRequest(**payload(identifier, time, **overrides)).transaction()


def revision(url, card_id="0001"):
    with psycopg.connect(url) as connection:
        return connection.execute(
            "SELECT sequence FROM scored_transactions WHERE card_id = %s "
            "ORDER BY occurred_at DESC, sequence DESC LIMIT 1",
            (card_id,),
        ).fetchone()[0]


def test_shared_cache_hit_skips_history_query_and_duplicates_do_not_change_state(
    database_url, cache, monkeypatch
):
    model = ExampleModel()
    first_service = PostgresScoringService(model, database_url, history_cache=cache)
    first = first_service.score(transaction())
    other_cache = RedisHistoryCache(os.environ["TEST_REDIS_URL"], database_url)
    second_service = PostgresScoringService(
        model, database_url, history_cache=other_cache
    )
    try:

        def unexpected_query(*args):
            raise AssertionError("캐시 적중 시 최근 거래 조회가 발생함")

        monkeypatch.setattr(second_service, "load_history", unexpected_query)
        second = second_service.score(transaction("second"))
        assert second.features.count_7d == 1
        before = cache.client.hgetall(cache.key("0001"))
        assert second_service.score(transaction()) == first
        assert cache.client.hgetall(cache.key("0001")) == before
        assert model.calls == 2
        assert int(before["revision"]) == revision(database_url)
        assert 0 < cache.client.ttl(cache.key("0001")) <= CACHE_TTL_SECONDS
    finally:
        other_cache.close()


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "invalid-json",
        "version",
        "entry",
        "wrong-type",
        "future-revision",
        "invalid-revision",
    ],
)
def test_lost_or_corrupt_cache_rebuilds_from_database(database_url, cache, damage):
    service = PostgresScoringService(ExampleModel(), database_url, history_cache=cache)
    service.score(transaction())
    key = cache.key("0001")
    if damage == "missing":
        cache.client.delete(key)
    elif damage == "wrong-type":
        cache.client.set(key, "unexpected string")
    elif damage == "future-revision":
        cache.client.hset(key, "revision", "9223372036854775807")
    elif damage == "invalid-revision":
        cache.client.hset(key, "revision", "not-a-number")
    else:
        state = json.loads(cache.client.hget(key, "state"))
        if damage == "version":
            state["feature_version"] = "obsolete"
        elif damage == "entry":
            state["amounts"][0][1] = "-100"
        cache.client.hset(
            key, "state", "{" if damage == "invalid-json" else json.dumps(state)
        )
    assert service.score(transaction("second")).features.count_7d == 1
    restored = cache.load("0001", revision(database_url), transaction().occurred_at)
    assert restored.process(transaction("third")).count_7d == 2


def test_missed_publication_after_commit_rebuilds_on_next_transaction(
    database_url, cache, monkeypatch
):
    service = PostgresScoringService(ExampleModel(), database_url, history_cache=cache)
    service.score(transaction())
    old_revision = cache.client.hget(cache.key("0001"), "revision")
    with monkeypatch.context() as patch:

        def failed_write(*args):
            raise redis.ConnectionError("injected write failure")

        patch.setattr(cache.client, "eval", failed_write)
        second = service.score(transaction("second"))
        assert second.features.count_7d == 1
    assert count_rows(database_url) == 2
    assert cache.client.hget(cache.key("0001"), "revision") == old_revision
    assert service.score(transaction("third")).features.count_7d == 2
    assert int(cache.client.hget(cache.key("0001"), "revision")) == revision(
        database_url
    )


def test_unavailable_redis_falls_back_and_recovers(database_url, cache):
    unavailable = RedisHistoryCache("redis://127.0.0.1:1/0", database_url)
    try:
        service = PostgresScoringService(
            ExampleModel(), database_url, history_cache=unavailable
        )
        assert service.score(transaction()).features.count_7d == 0
        assert service.score(transaction("second")).features.count_7d == 1
    finally:
        unavailable.close()
    recovered = PostgresScoringService(
        ExampleModel(), database_url, history_cache=cache
    )
    assert recovered.score(transaction("third")).features.count_7d == 2
    assert (
        cache.load("0001", revision(database_url), transaction().occurred_at)
        is not None
    )


@pytest.mark.parametrize("failure", ["model", "insert", "commit"])
def test_failed_transaction_never_publishes_new_history(database_url, cache, failure):
    model = ExampleModel()
    service = PostgresScoringService(model, database_url, history_cache=cache)
    service.score(transaction())
    before = cache.client.hgetall(cache.key("0001"))
    if failure == "model":
        model.fail = True
    else:
        with psycopg.connect(database_url) as connection:
            connection.execute("""
                CREATE FUNCTION reject_failed() RETURNS trigger AS $$
                BEGIN
                    IF NEW.transaction_id = 'failed' THEN
                        RAISE EXCEPTION 'injected failure';
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql
            """)
            if failure == "commit":
                connection.execute("""
                    CREATE CONSTRAINT TRIGGER reject_failed
                    AFTER INSERT ON scored_transactions DEFERRABLE INITIALLY DEFERRED
                    FOR EACH ROW EXECUTE FUNCTION reject_failed()
                """)
            else:
                connection.execute("""
                    CREATE TRIGGER reject_failed BEFORE INSERT ON scored_transactions
                    FOR EACH ROW EXECUTE FUNCTION reject_failed()
                """)
    with pytest.raises(ScoringUnavailable):
        service.score(transaction("failed", "2026-01-10 10:00:00"))
    assert cache.client.hgetall(cache.key("0001")) == before
    assert count_rows(database_url) == 1
    model.fail = False
    assert service.score(transaction("second")).features.count_7d == 1


def test_cache_never_allows_scoring_without_database(database_url, cache, monkeypatch):
    service = PostgresScoringService(ExampleModel(), database_url, history_cache=cache)
    service.score(transaction())
    before = cache.client.hgetall(cache.key("0001"))

    def disconnected(*args, **kwargs):
        raise psycopg.OperationalError("injected database disconnect")

    monkeypatch.setattr(database, "connect", disconnected)
    with pytest.raises(ScoringUnavailable, match="database_unavailable"):
        service.score(transaction("second"))
    assert cache.client.hgetall(cache.key("0001")) == before


def test_atomic_publication_rejects_delayed_old_revision_without_float_rounding(cache):
    calculator = HistoryFeatureCalculator()
    calculator.process(transaction())
    assert cache.publish("0001", 9007199254740993, calculator)
    before = cache.client.hgetall(cache.key("0001"))
    assert not cache.publish("0001", 9007199254740992, calculator)
    assert cache.client.hgetall(cache.key("0001")) == before
    calculator.process(transaction("second"))
    assert cache.publish("0001", 9007199254740994, calculator)


def test_concurrent_workers_commit_each_transaction_once(database_url, cache):
    workers = [
        PostgresScoringService(ExampleModel(), database_url, history_cache=cache)
        for _ in range(8)
    ]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda worker: worker.score(transaction()), workers))
    assert all(result == results[0] for result in results)
    assert count_rows(database_url) == 1

    def score_next(index):
        return workers[index].score(transaction(f"next-{index}"))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(score_next, range(8)))
    assert sorted(result.features.count_7d for result in results) == list(range(1, 9))
    assert count_rows(database_url) == 9
    restored = cache.load("0001", revision(database_url), transaction().occurred_at)
    assert restored.process(transaction("last")).count_7d == 9


def test_cached_features_match_memory_at_boundaries_and_after_eviction(
    database_url, cache
):
    memory = InMemoryScoringService(ExampleModel())
    cached = PostgresScoringService(ExampleModel(), database_url, history_cache=cache)
    samples = [
        transaction("minimum", "0001-01-01 00:00:00", card_id="ancient"),
        transaction("first", amount="10.01"),
        transaction("same", amount="30.03"),
        transaction("hour", "2026-01-01 11:00:00"),
        transaction("after-hour", "2026-01-01 11:00:01"),
        transaction("seven-days", "2026-01-08 10:00:00"),
        transaction("after-seven-days", "2026-01-08 10:00:01"),
        transaction("expired", "2026-02-01 10:00:00"),
        transaction("other", card_id="other"),
    ]
    for index, item in enumerate(samples):
        if index == 4:
            cache.client.delete(cache.key(item.card_id))
        expected = memory.score(item)
        assert cached.score(item) == expected
        assert cached.score(item) == expected


def test_api_restart_shares_history_and_rejects_redis_without_database(
    database_url, cache
):
    url = os.environ["TEST_REDIS_URL"]
    with TestClient(
        create_app(ExampleModel(), database_url=database_url, redis_url=url)
    ) as client:
        first = client.post("/transactions/score", json=payload())
        assert first.status_code == 200
    with TestClient(
        create_app(ExampleModel(), database_url=database_url, redis_url=url)
    ) as client:
        assert client.post("/transactions/score", json=payload()).json() == first.json()
        second = client.post("/transactions/score", json=payload("second"))
        assert second.json()["features"]["count_7d"] == 1
    with (
        pytest.raises(ValueError, match="DATABASE_URL"),
        TestClient(create_app(ExampleModel(), database_url="", redis_url=url)),
    ):
        pass
