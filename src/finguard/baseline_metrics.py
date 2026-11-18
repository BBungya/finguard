"""검증에서 고른 기준과 일일 조사 한도를 평가한다."""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


def choose_threshold(labels, scores, review_cost, missed_cost):
    # 동점 거래는 한꺼번에 포함한다. 비용이 같으면 더 높은 기준을 유지한다.
    order = np.argsort(-scores, kind="stable")
    ordered = scores[order]
    ends = np.flatnonzero(np.r_[ordered[:-1] != ordered[1:], True])
    reviewed = ends + 1
    total_fraud = int(labels.sum())
    found = np.cumsum(labels[order])[ends]
    costs = reviewed * review_cost + (total_fraud - found) * missed_cost
    best = int(costs.argmin())
    return (
        float(ordered[ends[best]]) if costs[best] < total_fraud * missed_cost else None
    )


def outcome(labels, selected):
    found = int(labels[selected].sum())
    reviewed = int(selected.sum())
    missed = int(labels.sum()) - found
    false_alerts = reviewed - found
    return {
        "tp": found,
        "fp": false_alerts,
        "fn": missed,
        "tn": len(labels) - reviewed - missed,
        "reviewed": reviewed,
        "precision": found / reviewed if reviewed else None,
        "recall": found / (found + missed) if found + missed else None,
    }


def daily_rank(frame, scores):
    ranked = pd.DataFrame(
        {
            "score": scores,
            "time": frame["trans_date_trans_time"].to_numpy(),
            "id": frame["trans_num"].to_numpy(),
        }
    ).sort_values(["score", "time", "id"], ascending=[False, True, True])
    return ranked.groupby(ranked["time"].dt.normalize()).cumcount()


def select_daily(rank, budget):
    selected = np.zeros(len(rank), dtype=bool)
    selected[rank.index[rank < budget]] = True
    return selected


def evaluate(frame, scores, threshold, settings, unseen_cards):
    labels = frame["is_fraud"].to_numpy()
    unseen = frame["cc_num"].isin(unseen_cards).to_numpy()
    selected = (
        scores >= threshold
        if threshold is not None
        else np.zeros(len(scores), dtype=bool)
    )
    # 전체 거래에서 먼저 순위를 정해야 신규 카드만으로 한도를 다시 채우지 않는다.
    day_rank = daily_rank(frame, scores)
    budgets = [
        settings["primary_daily_review_budget"],
        *settings["comparison_daily_review_budgets"],
    ]
    misses = [
        settings["primary_missed_fraud_cost_units"],
        *settings["comparison_missed_fraud_cost_units"],
    ]

    def with_cost(result):
        result["cost"] = {
            str(missed): result["reviewed"] * settings["review_cost_units"]
            + result["fn"] * missed
            for missed in misses
        }
        return result

    result = {
        "ap": float(average_precision_score(labels, scores)),
        "threshold": with_cost(outcome(labels, selected)),
        "threshold_unseen": outcome(labels[unseen], selected[unseen]),
        "budgets": {},
        "budgets_unseen": {},
    }
    for budget in sorted(budgets):
        chosen = select_daily(day_rank, budget)
        result["budgets"][str(budget)] = with_cost(outcome(labels, chosen))
        result["budgets_unseen"][str(budget)] = outcome(labels[unseen], chosen[unseen])
    return result
