"""카드의 직전 이력으로 학습과 한 건 처리에 공통으로 쓰는 값을 계산한다."""

from collections import deque
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Context, Decimal

from finguard.transactions import Transaction

FEATURE_VERSION = "1"
COUNT_WINDOW = timedelta(hours=1)
AMOUNT_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class HistoryFeatures:
    transaction_id: str
    count_1h: int
    count_7d: int
    mean_amount_7d: Decimal | None
    std_amount_7d: Decimal | None
    feature_version: str = FEATURE_VERSION


@dataclass
class _CardHistory:
    times_1h: deque[datetime] = field(default_factory=deque)
    amounts_7d: deque[tuple[datetime, int]] = field(default_factory=deque)
    sum_cents: int = 0
    sum_squared_cents: int = 0
    last_time: datetime | None = None

    def expire(self, now: datetime) -> None:
        # 정확히 1시간 또는 7일 전 거래는 남겨 둔다.
        while self.times_1h and now - self.times_1h[0] > COUNT_WINDOW:
            self.times_1h.popleft()
        while self.amounts_7d and now - self.amounts_7d[0][0] > AMOUNT_WINDOW:
            _, cents = self.amounts_7d.popleft()
            self.sum_cents -= cents
            self.sum_squared_cents -= cents * cents

    def append(self, now: datetime, cents: int) -> None:
        self.times_1h.append(now)
        self.amounts_7d.append((now, cents))
        self.sum_cents += cents
        self.sum_squared_cents += cents * cents
        self.last_time = now


class HistoryFeatureCalculator:
    """검증된 거래를 카드별 시각 순서대로 한 건씩 받는다."""

    def __init__(self) -> None:
        self._cards: dict[str, _CardHistory] = {}

    def process(self, transaction: Transaction) -> HistoryFeatures:
        now = transaction.occurred_at
        if not transaction.card_id.strip():
            raise ValueError("missing_card_id")
        if now.tzinfo is not None:
            raise ValueError("expected_timestamp_without_timezone")
        if not transaction.amount.is_finite() or transaction.amount <= 0:
            raise ValueError("invalid_amount")
        numerator, denominator = transaction.amount.as_integer_ratio()
        cents, remainder = divmod(numerator * 100, denominator)
        if remainder:
            raise ValueError("invalid_amount_precision")

        history = self._cards.setdefault(transaction.card_id, _CardHistory())
        if history.last_time is not None and now < history.last_time:
            raise ValueError("out_of_order_card_transaction")
        history.expire(now)
        count = len(history.amounts_7d)
        mean = stddev = None
        if count:
            # 합과 제곱합을 정수로 관리해 작은 금액 차이도 반올림으로 잃지 않는다.
            context = Context(prec=28)
            divisor = Decimal(count * 100)
            mean = context.divide(Decimal(history.sum_cents), divisor)
            variance_numerator = (
                count * history.sum_squared_cents - history.sum_cents**2
            )
            stddev = context.divide(context.sqrt(Decimal(variance_numerator)), divisor)

        features = HistoryFeatures(
            transaction_id=transaction.transaction_id,
            count_1h=len(history.times_1h),
            count_7d=count,
            mean_amount_7d=mean,
            std_amount_7d=stddev,
        )
        # 이번 거래는 계산을 끝낸 뒤 추가해야 다음 거래부터 이력에 들어간다.
        history.append(now, cents)
        return features


def compute_history_features(
    transactions: Iterable[Transaction],
) -> Iterator[HistoryFeatures]:
    """학습용 거래열도 같은 계산기에 같은 순서로 넣는다."""
    calculator = HistoryFeatureCalculator()
    for transaction in transactions:
        yield calculator.process(transaction)
