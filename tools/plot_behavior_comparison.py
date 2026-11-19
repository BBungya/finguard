"""행동 정보 조합별 탐지 건수와 개선폭을 pyplot·Seaborn으로 그린다."""

import json

import pandas as pd
from plot_behavior_analysis import ROOT, configure_style, plt, sns


def main():
    configure_style()
    results = json.loads(
        (ROOT / "artifacts/behavior_ablation/results.json").read_text(encoding="utf-8")
    )
    labels = {
        "baseline": "기준선",
        "cluster": "군집 추가",
        "anomaly": "이상 점수 추가",
        "both": "둘 다 추가",
    }
    base_test = results["variants"]["baseline"]["test"]["budgets"]["20"]["tp"]
    data = pd.DataFrame(
        [
            {
                "조합": labels[name],
                "검증 탐지": metrics["validation"]["budgets"]["20"]["tp"],
                "테스트 변화": metrics["test"]["budgets"]["20"]["tp"] - base_test,
            }
            for name, metrics in results["variants"].items()
        ]
    )
    figure, axes = plt.subplots(1, 2, figsize=(14, 5.6))
    sns.barplot(data=data, x="조합", y="검증 탐지", color="#3975a8", ax=axes[0])
    axes[0].bar_label(axes[0].containers[0], fmt="%.0f", padding=4)
    axes[0].set_ylim(0, 2300)
    axes[0].set_ylabel("찾은 사기 건수")
    axes[0].set_title("상반기 검증에서 선택한 조합은 군집 추가", pad=15)
    sns.barplot(data=data, x="조합", y="테스트 변화", color="#4e9a87", ax=axes[1])
    axes[1].bar_label(axes[1].containers[0], fmt="%+.0f", padding=5)
    axes[1].axhline(0, color="#444444", linewidth=1)
    axes[1].set_ylim(-5, 5)
    axes[1].set_ylabel("기준선 대비 사기 탐지 건수 변화")
    axes[1].set_title("하반기에서 군집 추가의 개선은 1건", pad=15)
    for axis in axes:
        axis.set_xlabel("")
        axis.tick_params(axis="x", rotation=12)
    figure.suptitle("같은 XGBoost에서 행동 정보의 추가 효과", fontsize=18)
    figure.text(
        0.5,
        0.01,
        "상반기 상위 20건에서 동률이면 AP로 선택 · 하반기는 조합별로 같은 3,680건 조사 · 기준선 탐지 1,711건",
        ha="center",
        fontsize=10,
    )
    figure.tight_layout(rect=(0, 0.055, 1, 0.95))
    output = ROOT / "reports/figures/behavior_ablation.png"
    figure.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(figure)
    print(output)


if __name__ == "__main__":
    main()
