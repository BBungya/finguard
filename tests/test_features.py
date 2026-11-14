from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from finguard.features import HistoryFeatureCalculator, compute_history_features
from finguard.transactions import Transaction

NOW = datetime(2026, 1, 8, 10)


def transaction(identifier, offset=timedelta(), amount="10", card="0001"):
    return Transaction(identifier, NOW + offset, card, "food", Decimal(amount), None)


def test_window_edges_and_same_time_follow_replay_order():
    rows = [
        transaction("too-old", -timedelta(days=7, seconds=1), "100"),
        transaction("seven-days", -timedelta(days=7), "10"),
        transaction("outside-hour", -timedelta(hours=1, seconds=1), "20"),
        transaction("one-hour", -timedelta(hours=1), "30"),
        transaction("different-card", amount="900", card="0002"),
        transaction("first-at-now", amount="40"),
        transaction("second-at-now", amount="900"),
        transaction("next-second", timedelta(seconds=1)),
    ]
    features = list(compute_history_features(rows))
    before, tied, later = features[-3:]

    assert (before.count_1h, before.count_7d, before.mean_amount_7d) == (1, 3, 20)
    assert before.std_amount_7d == pytest.approx(Decimal("8.16496580927726032732"))
    assert (tied.count_1h, tied.count_7d, tied.mean_amount_7d) == (2, 4, 25)
    assert (later.count_1h, later.count_7d, later.mean_amount_7d) == (
        2,
        4,
        Decimal("247.5"),
    )
    assert features[4].count_7d == 0


def test_batch_and_one_at_a_time_match_and_future_does_not_leak():
    rows = [
        transaction("first", amount="10"),
        transaction("second", timedelta(minutes=15), "30"),
        transaction("third", timedelta(minutes=30), "100"),
        transaction("future", timedelta(minutes=45), "1000"),
    ]
    expected = list(compute_history_features(rows))
    calculator = HistoryFeatureCalculator()
    assert [calculator.process(row) for row in rows] == expected

    first, second, third, _ = expected
    assert (first.count_7d, first.mean_amount_7d, first.std_amount_7d) == (
        0,
        None,
        None,
    )
    assert (second.count_7d, second.mean_amount_7d, second.std_amount_7d) == (1, 10, 0)
    assert (third.count_7d, third.mean_amount_7d, third.std_amount_7d) == (2, 20, 10)

    changed = [*rows[:2], replace(rows[2], amount=Decimal(900)), rows[3]]
    changed_features = list(compute_history_features(changed))
    assert changed_features[:3] == expected[:3]
    assert changed_features[3] != expected[3]


def test_invalid_and_late_transactions_do_not_change_card_history():
    calculator = HistoryFeatureCalculator()
    calculator.process(transaction("valid"))
    for invalid, reason in [
        (transaction("empty-card", card=""), "missing_card_id"),
        (transaction("non-finite", amount="NaN"), "invalid_amount"),
        (transaction("invalid-precision", amount="0.001"), "invalid_amount_precision"),
        (transaction("older", -timedelta(seconds=1)), "out_of_order_card_transaction"),
    ]:
        with pytest.raises(ValueError, match=reason):
            calculator.process(invalid)
    features = calculator.process(transaction("next"))
    assert features.count_7d == 1
    assert features.mean_amount_7d == 10


def test_large_amounts_with_one_cent_difference_keep_their_variation():
    rows = [
        transaction("one", amount="99999999999999999999999999999.01"),
        transaction("two", amount="99999999999999999999999999999.02"),
        transaction("next"),
    ]
    assert list(compute_history_features(rows))[-1].std_amount_7d == Decimal("0.005")
