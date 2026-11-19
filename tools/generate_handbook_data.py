"""공식 Handbook 노트북의 생성 부분을 고정 버전으로 실행한다."""

import hashlib
import json
import random
import time
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads(
        (ROOT / "data/manifests/handbook_benchmark.json").read_text(encoding="utf-8")
    )
    directory = ROOT / manifest["local_directory"]
    directory.mkdir(parents=True, exist_ok=True)
    notebook = directory / "SimulatedDataset.ipynb"
    if notebook.exists():
        content = notebook.read_bytes()
    else:
        with urlopen(manifest["notebook_url"], timeout=60) as response:
            content = response.read()

    if hashlib.sha256(content).hexdigest() != manifest["notebook_sha256"]:
        raise ValueError("공식 노트북의 SHA-256이 매니페스트와 다릅니다.")
    notebook.write_bytes(content)
    cells = json.loads(content)["cells"]
    environment = {"np": np, "pd": pd, "random": random, "time": time}
    # 검토한 생성·라벨링 코드만 실행한다. 예시, 그림, pickle 저장 셀은 생략한다.
    for index in (5, 9, 13, 25, 33, 35, 45):
        source = "".join(cells[index]["source"])
        exec(compile(source, f"{notebook.name}:cell-{index}", "exec"), environment)  # noqa: S102
    transactions = environment["add_frauds"](
        environment["customer_profiles_table"],
        environment["terminal_profiles_table"],
        environment["transactions_df"],
    )
    print(f"Rows: {len(transactions):,}; frauds: {transactions['TX_FRAUD'].sum():,}")
    output = directory / manifest["file"]
    pending = output.with_suffix(".part")
    transactions.to_csv(pending, index=False, lineterminator="\n", float_format="%.2f")
    pending.replace(output)
    with output.open("rb") as source:
        print(f"{output}: {hashlib.file_digest(source, 'sha256').hexdigest()}")


if __name__ == "__main__":
    main()
