"""KMeans와 Isolation Forest의 집계 결과를 pyplot과 Seaborn으로 그린다."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.font_manager import FontProperties, fontManager

ROOT = Path(__file__).resolve().parents[1]


def configure_style():
    font = Path("C:/Windows/Fonts/malgun.ttf")
    if font.exists():
        fontManager.addfont(str(font))
        plt.rcParams["font.family"] = FontProperties(fname=font).get_name()
    sns.set_theme(
        style="whitegrid",
        rc={
            "font.family": plt.rcParams["font.family"],
            "axes.unicode_minus": False,
        },
    )


def main():
    configure_style()
    clusters = json.loads(
        (ROOT / "artifacts/behavior_clusters/results.json").read_text(encoding="utf-8")
    )
    anomalies = json.loads(
        (ROOT / "artifacts/behavior_anomalies/results.json").read_text(encoding="utf-8")
    )
    output = ROOT / "reports/figures"
    output.mkdir(parents=True, exist_ok=True)

    figure, axes = plt.subplots(1, 2, figsize=(15, 5.8))
    candidate = pd.DataFrame(
        [
            {"군집 수": int(key), "실루엣": value["silhouette"]}
            for key, value in clusters["candidates"].items()
        ]
    )
    sns.barplot(data=candidate, x="군집 수", y="실루엣", ax=axes[0], color="#3975a8")
    axes[0].bar_label(axes[0].containers[0], fmt="%.3f", padding=4)
    axes[0].set_ylim(0, 0.4)
    axes[0].set_title("학습 표본에서 3개 그룹의 분리도가 가장 높음", pad=15)

    medians = pd.DataFrame(
        {
            f"그룹 {key}": group["history_medians"]
            for key, group in clusters["validation"].items()
            if key != "-1"
        }
    ).T
    # 서로 단위가 다른 열은 색상 범위만 맞추고 셀에는 원래 중앙값을 쓴다.
    ranges = medians.max() - medians.min()
    colors = (medians - medians.min()) / ranges.replace(0, 1)
    colors.columns = ["1시간 건수", "7일 건수", "7일 평균 금액", "7일 표준편차"]
    sns.heatmap(
        colors,
        annot=medians.to_numpy(),
        fmt=".2f",
        cmap="Blues",
        linewidths=2,
        cbar=False,
        ax=axes[1],
    )
    axes[1].set_title("검증 거래의 직전 이력 중앙값", pad=15)
    axes[1].tick_params(axis="x", rotation=15)
    axes[1].tick_params(axis="y", rotation=0)
    figure.suptitle("카드 사용 상태를 묶은 KMeans 결과", fontsize=19, y=1.02)
    figure.text(
        0.5,
        -0.03,
        "학습은 2019년, 검증은 2020년 상반기 · 색상은 열 안에서의 상대 크기 · 이력 없는 검증 148건은 별도 집계",
        ha="center",
        fontsize=11,
    )
    figure.tight_layout()
    figure.savefig(output / "behavior_clusters.png", dpi=150, bbox_inches="tight")
    plt.close(figure)

    bands = ["낮은 50%", "50~90%", "90~99%", "상위 약 1%"]
    data = pd.DataFrame(
        [
            {
                "학습 점수 구간": label,
                "정상": group["rows"] - group["fraud"],
                "사기": group["fraud"],
                "사기 비율": group["fraud_rate"] * 100,
            }
            for index, label in enumerate(bands)
            for group in [anomalies["validation"][str(index)]]
        ]
    )
    figure, axes = plt.subplots(1, 2, figsize=(15, 6))
    counts = data.melt(
        id_vars=["학습 점수 구간"],
        value_vars=["정상", "사기"],
        var_name="라벨",
        value_name="거래 수",
    )
    sns.barplot(
        data=counts,
        x="학습 점수 구간",
        y="거래 수",
        hue="라벨",
        palette={"정상": "#9bb5c8", "사기": "#c65348"},
        ax=axes[0],
    )
    axes[0].set_yscale("log")
    for container in axes[0].containers:
        axes[0].bar_label(container, fmt="%.0f", fontsize=10, padding=3)
    axes[0].set_ylim(100, 600000)
    axes[0].set_ylabel("거래 수 (로그 눈금)")
    axes[0].set_title("높은 이상 점수 구간에도 정상 거래가 많음", pad=15)
    sns.barplot(
        data=data,
        x="학습 점수 구간",
        y="사기 비율",
        color="#c65348",
        ax=axes[1],
    )
    axes[1].bar_label(axes[1].containers[0], fmt="%.2f%%", padding=4)
    axes[1].set_ylim(0, 15)
    axes[1].set_ylabel("실제 사기 비율 (%)")
    axes[1].set_title("상위 약 1% 구간의 사기 비율은 12.36%", pad=15)
    figure.suptitle("Isolation Forest 이상 점수와 실제 라벨", fontsize=19, y=1.02)
    figure.text(
        0.5,
        -0.03,
        "2019년 점수로 경계 고정 → 2020년 상반기 검증 · 상위 구간 4,150건 = 정상 3,637건 + 사기 513건",
        ha="center",
        fontsize=11,
    )
    for axis in axes:
        axis.set_xlabel("학습 데이터에서 정한 점수 구간")
        axis.tick_params(axis="x", rotation=12)
    figure.tight_layout()
    figure.savefig(output / "behavior_anomalies.png", dpi=150, bbox_inches="tight")
    plt.close(figure)
    print(output)


if __name__ == "__main__":
    main()
