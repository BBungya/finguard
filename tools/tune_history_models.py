"""같은 거래열에서 이력 추가 효과와 XGBoost 설정을 따로 비교한다."""

import json
import tomllib
from decimal import Decimal
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import RandomForestClassifier
from threadpoolctl import threadpool_limits
from train_baselines import ROOT, inputs, load_periods, make_preprocessor
from xgboost import XGBClassifier

from finguard.baseline_metrics import choose_threshold, evaluate
from finguard.features import FEATURE_VERSION, HistoryFeatureCalculator
from finguard.transactions import Transaction

HISTORY_COLUMNS = ("count_1h", "count_7d", "mean_amount_7d", "std_amount_7d")


def history_inputs(periods):
    calculator = HistoryFeatureCalculator()
    for frame in periods:
        values = np.empty((len(frame), len(HISTORY_COLUMNS)), dtype=np.float32)
        # 원본 순서를 동시각 기준으로 유지하고, 계산 결과는 원래 행에 돌려놓는다.
        order = frame["trans_date_trans_time"].argsort(kind="stable").to_numpy()
        rows = frame[
            ["trans_num", "trans_date_trans_time", "cc_num", "category", "amt"]
        ]
        for position, row in zip(
            order, rows.iloc[order].itertuples(index=False, name=None), strict=True
        ):
            transaction_id, time, card, category, amount = row
            result = calculator.process(
                Transaction(
                    transaction_id,
                    time.to_pydatetime(),
                    card,
                    category,
                    Decimal(str(amount)),
                    None,
                )
            )
            values[position] = (
                result.count_1h,
                result.count_7d,
                result.mean_amount_7d if result.mean_amount_7d is not None else -1,
                result.std_amount_7d if result.std_amount_7d is not None else -1,
            )
        yield values


def add_history(base, history):
    # XGBoost는 희소 행렬의 생략된 값을 결측으로 본다. 이력의 0은 실제 값이다.
    rows, columns = history.shape
    explicit_history = csr_matrix(
        (
            history.ravel(),
            np.tile(np.arange(columns), rows),
            np.arange(0, (rows + 1) * columns, columns),
        ),
        shape=history.shape,
    )
    return hstack((base, explicit_history), format="csr")


def read_settings(name):
    with (ROOT / "configs" / name).open("rb") as source:
        return tomllib.load(source)


def main():
    split = read_settings("ml_split.toml")
    baseline = read_settings("baseline.toml")
    trials = read_settings("history_tuning.toml")["xgboost_trials"]
    settings = split["evaluation"]
    train, validation, test = load_periods(split)
    active_cards = set(train["cc_num"])
    unseen = set(pd.concat([validation["cc_num"], test["cc_num"]])) - active_cards
    preprocessor = make_preprocessor()
    base_train = preprocessor.fit_transform(inputs(train))
    base_validation = preprocessor.transform(inputs(validation))
    history = history_inputs((train, validation, test))
    print("Computing train and validation history", flush=True)
    history_train = add_history(base_train, next(history))
    history_validation = add_history(base_validation, next(history))
    seed, workers = baseline["seed"], baseline["workers"]
    candidates = [
        (
            "rf_base",
            False,
            RandomForestClassifier(
                random_state=seed, n_jobs=workers, **baseline["random_forest"]
            ),
        ),
        (
            "rf_history",
            True,
            RandomForestClassifier(
                random_state=seed, n_jobs=workers, **baseline["random_forest"]
            ),
        ),
        (
            "xgb_base",
            False,
            XGBClassifier(random_state=seed, n_jobs=workers, **baseline["xgboost"]),
        ),
        (
            "xgb_history",
            True,
            XGBClassifier(random_state=seed, n_jobs=workers, **baseline["xgboost"]),
        ),
    ]
    for trial in trials:
        overrides = {key: value for key, value in trial.items() if key != "name"}
        candidates.append(
            (
                trial["name"],
                True,
                XGBClassifier(
                    random_state=seed,
                    n_jobs=workers,
                    **(baseline["xgboost"] | overrides),
                ),
            )
        )

    results = {"history_feature_version": FEATURE_VERSION, "candidates": {}}
    models = {}
    budget = str(settings["primary_daily_review_budget"])
    train_labels = train["is_fraud"].to_numpy()
    validation_labels = validation["is_fraud"].to_numpy()
    for name, uses_history, model in candidates:
        print(f"Validating {name}", flush=True)
        start = perf_counter()
        with threadpool_limits(limits=workers):
            model.fit(history_train if uses_history else base_train, train_labels)
        elapsed = perf_counter() - start
        if isinstance(model, RandomForestClassifier):
            model.set_params(n_jobs=1)
        scores = model.predict_proba(
            history_validation if uses_history else base_validation
        )[:, 1]
        threshold = choose_threshold(
            validation_labels,
            scores,
            settings["review_cost_units"],
            settings["primary_missed_fraud_cost_units"],
        )
        results["candidates"][name] = {
            "threshold_from_validation": threshold,
            "fit_seconds": elapsed,
            "validation": evaluate(validation, scores, threshold, settings, unseen),
        }
        models[name] = (uses_history, model)

    def selection_key(name):
        metrics = results["candidates"][name]["validation"]
        return metrics["budgets"][budget]["tp"], metrics["ap"]

    # 기준선도 선택지에 남겨 두고 테스트 점수는 선택이 끝난 뒤 계산한다.
    winner = max(models, key=selection_key)
    results["selected"] = winner
    print(f"Selected {winner}; evaluating comparison models", flush=True)
    base_test = preprocessor.transform(inputs(test))
    history_test = add_history(base_test, next(history))
    for name in dict.fromkeys(
        ("rf_base", "rf_history", "xgb_base", "xgb_history", winner)
    ):
        uses_history, model = models[name]
        scores = model.predict_proba(history_test if uses_history else base_test)[:, 1]
        candidate = results["candidates"][name]
        candidate["test"] = evaluate(
            test, scores, candidate["threshold_from_validation"], settings, unseen
        )

    output = ROOT / "artifacts/history_tuning"
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, output / "preprocessor.joblib")
    joblib.dump(models[winner][1], output / "selected_model.joblib")
    (output / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(output / "results.json")


if __name__ == "__main__":
    main()
