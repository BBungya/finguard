"""같은 XGBoost에서 군집·이상 점수 추가 효과를 비교한다."""

import json
import platform
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from train_baselines import ROOT, inputs, load_periods, make_preprocessor
from tune_history_models import add_history, history_inputs, read_settings
from xgboost import XGBClassifier

from finguard.baseline_metrics import (
    choose_threshold,
    daily_rank,
    evaluate,
    outcome,
    select_daily,
)
from finguard.model_diagnostics import subgroup_errors


def behavior_values(history, scaler, cluster, anomaly):
    known = history[:, 1] > 0
    groups = np.full(len(history), -1, dtype=int)
    scores = np.full((len(history), 1), -1.0, dtype=np.float32)
    if known.any():
        transformed = scaler.transform(np.log1p(history[known])).astype(
            cluster.cluster_centers_.dtype, copy=False
        )
        groups[known] = cluster.predict(transformed)
        scores[known, 0] = -anomaly.score_samples(transformed)
    # 각 군집은 별도 열이다. 번호의 크기로 위험 순서를 학습시키지 않는다.
    membership = np.eye(cluster.n_clusters + 1, dtype=np.float32)[groups + 1]
    return groups, membership, scores


def variant_inputs(base, membership, scores, name):
    if name == "cluster":
        return add_history(base, membership)
    if name == "anomaly":
        return add_history(base, scores)
    if name == "both":
        return add_history(base, np.column_stack((membership, scores)))
    return base


def card_impact(frame, scores, reference, budget):
    chosen = select_daily(daily_rank(frame, scores), budget)
    previous = select_daily(daily_rank(frame, reference), budget)
    labels = frame["is_fraud"].to_numpy()
    changes = (
        pd.DataFrame(
            {
                "card": frame["cc_num"].to_numpy(),
                "caught_change": labels * (chosen.astype(int) - previous.astype(int)),
                "normal_review_change": (1 - labels)
                * (chosen.astype(int) - previous.astype(int)),
            }
        )
        .groupby("card")
        .sum()
    )
    return {
        "cards_more_frauds_found": int((changes["caught_change"] > 0).sum()),
        "cards_fewer_frauds_found": int((changes["caught_change"] < 0).sum()),
        "cards_equal_frauds_found": int((changes["caught_change"] == 0).sum()),
        "cards_more_normal_reviews": int((changes["normal_review_change"] > 0).sum()),
        "cards_fewer_normal_reviews": int((changes["normal_review_change"] < 0).sum()),
        "net_frauds_found": int(changes["caught_change"].sum()),
    }


def main():
    config = read_settings("behavior_ablation.toml")
    cluster_config = read_settings("behavior_clusters.toml")
    anomaly_config = read_settings("behavior_anomalies.toml")
    baseline = read_settings("baseline.toml")
    split = read_settings("ml_split.toml")
    evaluation = split["evaluation"]
    budget = config["selection_daily_budget"]
    train, validation, test = load_periods(split)
    unseen = set(pd.concat([validation["cc_num"], test["cc_num"]])) - set(
        train["cc_num"]
    )
    preprocessor = make_preprocessor()
    base_train = preprocessor.fit_transform(inputs(train))
    base_validation = preprocessor.transform(inputs(validation))
    histories = history_inputs((train, validation, test))
    print("Computing training history", flush=True)
    train_history = next(histories)
    known = train_history[:, 1] > 0
    scaler = StandardScaler()
    scaled = scaler.fit_transform(np.log1p(train_history[known]))
    with threadpool_limits(limits=baseline["workers"]):
        cluster = KMeans(
            n_clusters=config["cluster_count"],
            n_init=cluster_config["n_init"],
            random_state=cluster_config["seed"],
        ).fit(scaled)
        anomaly = IsolationForest(
            n_estimators=anomaly_config["n_estimators"],
            max_samples=anomaly_config["max_samples"],
            random_state=anomaly_config["seed"],
            n_jobs=anomaly_config["workers"],
            contamination="auto",
        ).fit(scaled)
    _, train_membership, train_scores = behavior_values(
        train_history, scaler, cluster, anomaly
    )
    base_train = add_history(base_train, train_history)
    print("Computing validation history", flush=True)
    validation_history = next(histories)
    _, validation_membership, validation_scores = behavior_values(
        validation_history, scaler, cluster, anomaly
    )
    base_validation = add_history(base_validation, validation_history)
    models = {}
    results = {
        "environment": {
            "python": platform.python_version(),
            **{
                name: version(name)
                for name in ("numpy", "pandas", "scikit-learn", "xgboost")
            },
        },
        "selection_daily_budget": budget,
        "xgboost": config["xgboost"],
        "variants": {},
    }
    for name in config["variants"]:
        print(f"Validating {name}", flush=True)
        model = XGBClassifier(
            random_state=baseline["seed"],
            n_jobs=baseline["workers"],
            **config["xgboost"],
        )
        with threadpool_limits(limits=baseline["workers"]):
            model.fit(
                variant_inputs(base_train, train_membership, train_scores, name),
                train["is_fraud"].to_numpy(),
            )
        scores = model.predict_proba(
            variant_inputs(
                base_validation, validation_membership, validation_scores, name
            )
        )[:, 1]
        threshold = choose_threshold(
            validation["is_fraud"].to_numpy(),
            scores,
            evaluation["review_cost_units"],
            evaluation["primary_missed_fraud_cost_units"],
        )
        results["variants"][name] = {
            "threshold": threshold,
            "validation": evaluate(validation, scores, threshold, evaluation, unseen),
        }
        models[name] = model

    def selection_key(name):
        metrics = results["variants"][name]["validation"]
        return metrics["budgets"][str(budget)]["tp"], metrics["ap"]

    selected = max(config["variants"], key=selection_key)
    results["selected"] = selected
    print(f"Selected {selected}; evaluating fixed comparisons on test", flush=True)
    test_history = next(histories)
    groups, membership, anomaly_scores = behavior_values(
        test_history, scaler, cluster, anomaly
    )
    base_test = add_history(preprocessor.transform(inputs(test)), test_history)
    test_scores = {}
    for name, model in models.items():
        scores = model.predict_proba(
            variant_inputs(base_test, membership, anomaly_scores, name)
        )[:, 1]
        test_scores[name] = scores
        result = results["variants"][name]
        result["test"] = evaluate(test, scores, result["threshold"], evaluation, unseen)
        result["errors"] = subgroup_errors(test, scores, budget, unseen)
        chosen = select_daily(daily_rank(test, scores), budget)
        labels = test["is_fraud"].to_numpy()
        result["cluster_errors"] = {
            str(group): outcome(labels[groups == group], chosen[groups == group])
            for group in np.unique(groups)
        }
        result["card_impact"] = card_impact(
            test, scores, test_scores["baseline"], budget
        )

    output = ROOT / "artifacts/behavior_ablation"
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "preprocessor": preprocessor,
            "scaler": scaler,
            "cluster": cluster,
            "anomaly": anomaly,
            "xgboost": models[selected],
            "variant": selected,
            "threshold": results["variants"][selected]["threshold"],
        },
        output / "selected_model.joblib",
    )
    (output / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(output / "results.json")


if __name__ == "__main__":
    main()
