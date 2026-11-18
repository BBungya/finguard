"""평가용 CSV의 시간 분할과 카드별 라벨 분포를 집계한다."""

import csv
import hashlib
import json
import tomllib
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]


def profile(config: dict) -> dict:
    manifest = json.loads(
        (ROOT / config["dataset_manifest"]).read_text(encoding="utf-8")
    )
    periods = config["periods"]
    start = periods["train_start"]
    validation = periods["validation_start"]
    test = periods["test_start"]
    end = periods["end_exclusive"]
    if not start < validation < test < end:
        raise ValueError("학습·검증·테스트 경계가 시간순이어야 합니다.")

    by_split = {name: defaultdict(Counter) for name in ("train", "validation", "test")}
    by_day = {name: Counter() for name in by_split}
    seen_transactions = set()
    source_rows = {}
    for entry in manifest["files"]:
        path = ROOT / manifest["local_directory"] / entry["file"]
        with path.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != entry["sha256"]:
                raise ValueError(f"{path.name}의 SHA-256이 매니페스트와 다릅니다.")
        counts = Counter()
        with path.open(encoding="utf-8-sig", newline="") as source:
            for line, row in enumerate(csv.DictReader(source, strict=True), start=2):
                timestamp = datetime.fromisoformat(row[config["timestamp_column"]])
                card = row[config["customer_key"]]
                label = row[config["label_column"]]
                transaction_id = row["trans_num"]
                if not card or not transaction_id or label not in {"0", "1"}:
                    raise ValueError(
                        f"{path.name} {line}행의 카드·거래 ID 또는 라벨 오류"
                    )
                if transaction_id in seen_transactions:
                    raise ValueError(f"{path.name} {line}행의 거래 ID 중복")
                seen_transactions.add(transaction_id)
                if timestamp.tzinfo is not None or not start <= timestamp < end:
                    raise ValueError(
                        f"{path.name} {line}행의 거래 시각이 설정 범위를 벗어남"
                    )
                # 파일 이름이나 행 순서 대신 거래 시각으로 각 행의 기간을 정한다.
                split = "train"
                if timestamp >= test:
                    split = "test"
                elif timestamp >= validation:
                    split = "validation"
                counts[split] += 1
                by_split[split][card][label] += 1
                by_day[split][timestamp.date()] += 1
        source_rows[path.name] = dict(counts)

    train_cards = set(by_split["train"])
    split_stats = {}
    for split, cards in by_split.items():
        known, unseen = Counter(), Counter()
        for card, labels in cards.items():
            group = known if card in train_cards else unseen
            group.update(labels)
        totals = known + unseen
        if not totals["0"] or not totals["1"]:
            raise ValueError(f"{split} 기간에 정상·사기 거래가 모두 필요합니다.")
        daily_counts = by_day[split].values()
        split_stats[split] = {
            "rows": totals.total(),
            "fraud": totals["1"],
            "cards": len(cards),
            "unseen_card_rows": unseen.total(),
            "unseen_card_fraud": unseen["1"],
            "unseen_cards": len(cards.keys() - train_cards),
            "days_with_transactions": len(daily_counts),
            "daily_rows_min": min(daily_counts),
            "daily_rows_median": median(daily_counts),
            "daily_rows_max": max(daily_counts),
        }
    return {"splits": split_stats, "source_rows": source_rows}


if __name__ == "__main__":
    with (ROOT / "configs/ml_split.toml").open("rb") as file:
        print(json.dumps(profile(tomllib.load(file)), indent=2))
