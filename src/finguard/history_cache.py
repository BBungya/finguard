"""DB에서 다시 만들 수 있는 Redis 카드 이력. 캐시 실패는 DB로 우회한다."""

import hashlib
import json
import logging

from redis import Redis, RedisError
from redis.backoff import NoBackoff
from redis.retry import Retry

from finguard.features import HistoryFeatureCalculator

logger = logging.getLogger(__name__)
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

# 상태와 거래 번호, 만료 시간을 한 번에 바꾼다.
# bigint를 Lua 실수로 바꾸면 큰 번호가 반올림되므로 문자열로 비교한다.
PUBLISH_SCRIPT = """
local kind = redis.call('TYPE', KEYS[1]).ok
if kind ~= 'none' and kind ~= 'hash' then
    redis.call('DEL', KEYS[1])
end
local previous = redis.call('HGET', KEYS[1], 'revision')
local incoming = ARGV[1]
if previous and string.match(previous, '^[1-9][0-9]*$') then
    if #previous > #incoming or
       (#previous == #incoming and previous > incoming) then
        return 0
    end
end
redis.call('HSET', KEYS[1], 'revision', incoming, 'state', ARGV[2])
redis.call('EXPIRE', KEYS[1], ARGV[3])
return 1
"""


class RedisHistoryCache:
    def __init__(self, redis_url: str, database_url: str):
        self.client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
            retry=Retry(NoBackoff(), 0),
        )
        # DB와 테스트 스키마별로 분리하고 카드 번호를 키에 직접 넣지 않는다.
        namespace = hashlib.sha256(database_url.encode()).hexdigest()
        self.prefix = f"finguard:history:v1:{namespace}:"

    def key(self, card_id: str) -> str:
        return self.prefix + hashlib.sha256(card_id.encode()).hexdigest()

    def load(self, card_id: str, revision: int, latest_time):
        try:
            saved_revision, state = self.client.hmget(
                self.key(card_id), "revision", "state"
            )
            expected = str(revision)
            # 이 함수는 DB 카드 잠금 안에서 호출한다. DB보다 큰 번호는
            # 손상되었거나 DB 복원 전 캐시이므로 지워서 새 발행을 허용한다.
            if saved_revision is not None and (
                not saved_revision.isascii()
                or not saved_revision.isdecimal()
                or saved_revision.startswith("0")
                or len(saved_revision) > len(expected)
                or (len(saved_revision) == len(expected) and saved_revision > expected)
            ):
                self.client.delete(self.key(card_id))
                return None
            if saved_revision != expected or state is None:
                return None
            data = json.loads(state)
            if data["last_time"] != latest_time.isoformat():
                return None
            return HistoryFeatureCalculator.from_snapshot(card_id, data)
        except (RedisError, ValueError, TypeError, KeyError, OverflowError):
            logger.warning("history_cache_read_failed; rebuilding_from_database")
            return None

    def publish(self, card_id: str, revision: int, calculator):
        state = json.dumps(calculator.snapshot(card_id), ensure_ascii=True)
        try:
            return bool(
                self.client.eval(
                    PUBLISH_SCRIPT,
                    1,
                    self.key(card_id),
                    str(revision),
                    state,
                    str(CACHE_TTL_SECONDS),
                )
            )
        except RedisError:
            # DB 저장은 완료됐다. 다음 신규 거래에서 DB로 복구할 수 있다.
            logger.warning("history_cache_write_failed; database_commit_preserved")
            return False

    def close(self):
        self.client.close()
