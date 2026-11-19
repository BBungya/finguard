"""개별 검증 거래의 이력과 이상 점수 분포를 그린다."""

import joblib
import numpy as np
import pandas as pd
from plot_behavior_analysis import ROOT, configure_style, plt, sns
from train_baselines import load_periods
from tune_history_models import HISTORY_COLUMNS, history_inputs, read_settings


def main():
    configure_style()
    train, validation, _ = load_periods(read_settings("ml_split.toml"))
    history = history_inputs((train, validation))
    print("Computing chronological history", flush=True)
    next(history)
    validation_history = next(history)
    known = validation_history[:, 1] > 0
    values = validation_history[known]
    logged = np.log1p(values)
    cluster = joblib.load(ROOT / "artifacts/behavior_clusters/cluster_model.joblib")
    anomaly = joblib.load(ROOT / "artifacts/behavior_anomalies/anomaly_model.joblib")
    groups = cluster["kmeans"].predict(cluster["scaler"].transform(logged))
    scores = -anomaly["isolation_forest"].score_samples(
        anomaly["scaler"].transform(logged)
    )
    data = pd.DataFrame(logged, columns=HISTORY_COLUMNS)
    data["그룹"] = [f"그룹 {index}" for index in groups]
    data["점수"] = scores
    data["실제 라벨"] = np.where(validation.loc[known, "is_fraud"] == 1, "사기", "정상")
    output = ROOT / "reports/figures"
    output.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(2, 2, figsize=(14, 9))
    titles = [
        "최근 1시간 거래 건수",
        "최근 7일 거래 건수",
        "최근 7일 평균 금액",
        "최근 7일 표준편차",
    ]
    palette = {"그룹 0": "#3b7ca8", "그룹 1": "#db8a36", "그룹 2": "#41957a"}
    for axis, column, title in zip(axes.flat, HISTORY_COLUMNS, titles, strict=True):
        sns.histplot(
            data=data,
            x=column,
            hue="그룹",
            hue_order=list(palette),
            palette=palette,
            stat="density",
            common_norm=False,
            element="step",
            fill=False,
            bins=45,
            ax=axis,
        )
        axis.set_title(title, fontsize=14)
        axis.set_xlabel("log(1 + 원래 값)")
        axis.set_ylabel("그룹별 확률 밀도")
    figure.suptitle("군집별 거래 직전 이력의 분포", fontsize=19)
    figure.text(
        0.5,
        0.01,
        "2020년 상반기 검증 · 이력이 있는 401,735건 · 각 그룹의 면적을 1로 맞춰 분포 모양 비교",
        ha="center",
        fontsize=11,
    )
    figure.tight_layout(rect=(0, 0.035, 1, 0.96))
    figure.savefig(
        output / "behavior_history_distributions.png", dpi=150, bbox_inches="tight"
    )
    plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(15, 5.8))
    labels = {"정상": "#3b7ca8", "사기": "#c65348"}
    sns.histplot(
        data=data,
        x="점수",
        hue="실제 라벨",
        palette=labels,
        hue_order=list(labels),
        bins=65,
        element="step",
        fill=False,
        ax=axes[0],
    )
    axes[0].set_yscale("log")
    axes[0].set_ylabel("거래 수 (로그 눈금)")
    axes[0].set_title("정상·사기 거래의 실제 건수 분포", pad=15)
    sns.histplot(
        data=data,
        x="점수",
        hue="실제 라벨",
        palette=labels,
        hue_order=list(labels),
        stat="density",
        common_norm=False,
        bins=65,
        element="step",
        fill=False,
        ax=axes[1],
    )
    axes[1].set_ylabel("라벨별 확률 밀도")
    axes[1].set_title("정상·사기 각각의 면적을 1로 맞춘 분포", pad=15)
    for axis in axes:
        axis.axvline(
            anomaly["score_boundaries"][-1],
            color="#6b5b82",
            linestyle="--",
            linewidth=1,
        )
        axis.set_xlabel("이상 점수 (클수록 드문 행동)")
    figure.suptitle("정상 거래와 사기 거래의 이상 점수 분포", fontsize=19)
    figure.text(
        0.5,
        0.01,
        "학습 경계 고정 → 상반기 검증 · 점선은 학습 점수 99백분위 · 이력이 없는 148건은 별도 집계",
        ha="center",
        fontsize=11,
    )
    figure.tight_layout(rect=(0, 0.045, 1, 0.95))
    figure.savefig(
        output / "behavior_score_distributions.png", dpi=150, bbox_inches="tight"
    )
    plt.close(figure)
    assert len(data) == 401735
    assert data["실제 라벨"].value_counts().to_dict() == {"정상": 399341, "사기": 2394}
    print(output)


if __name__ == "__main__":
    main()
