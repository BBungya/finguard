"""교육용 CSV 한 행을 FinGuard 거래로 변환한다."""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = frozenset(
    {"trans_num", "trans_date_trans_time", "cc_num", "category", "amt"}
)
TIMESTAMP_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}"
)
AMOUNT_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    occurred_at: datetime
    card_id: str
    category: str
    amount: Decimal
    is_fraud: int | None

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "Transaction":
        values = {column: row[column].strip() for column in REQUIRED_COLUMNS}
        missing = sorted(column for column, value in values.items() if not value)
        if missing:
            raise ValueError(f"missing_required_fields: {', '.join(missing)}")

        timestamp = values["trans_date_trans_time"]
        # 교육 데이터의 시각에는 시간대가 없다. 임의로 UTC를 붙이지 않는다.
        if not TIMESTAMP_PATTERN.fullmatch(timestamp):
            raise ValueError("invalid_transaction_time")
        try:
            occurred_at = datetime.fromisoformat(timestamp)
        except ValueError:
            raise ValueError("invalid_transaction_time") from None

        raw_amount = values["amt"]
        if not AMOUNT_PATTERN.fullmatch(raw_amount):
            raise ValueError("invalid_amount")
        try:
            # float로 변환하면 일부 금액을 정확히 표현할 수 없다.
            amount = Decimal(raw_amount)
        except InvalidOperation:
            raise ValueError("invalid_amount") from None
        if amount <= 0:
            raise ValueError("invalid_amount")

        label = row.get("is_fraud", "").strip()
        if label not in {"", "0", "1"}:
            raise ValueError("invalid_fraud_label")

        return cls(
            transaction_id=values["trans_num"],
            occurred_at=occurred_at,
            card_id=values["cc_num"],
            category=values["category"],
            amount=amount,
            is_fraud=int(label) if label else None,
        )
