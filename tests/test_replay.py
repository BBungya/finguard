import json
import subprocess
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from finguard import replay as replay_module
from finguard.transactions import Transaction

HEADER = "trans_num,trans_date_trans_time,cc_num,category,amt,is_fraud"


def run_cli(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "finguard.replay", str(path), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_cli_reports_bad_rows_and_replays_in_stable_order(tmp_path):
    source = tmp_path / "transactions.csv"
    source.write_text(
        HEADER + "\n"
        "tx-b,2026-01-01 10:05:00,0001,food,1.25,0\n"
        "tx-a,2026-01-01 10:00:00,0001,food,0,0\n"
        "tx-a,2026-01-01 10:00:00,0001,food,3.00,1\n"
        "tx-a,2026-01-01 09:59:00,0001,food,5.00,0\n"
        "tx-0,2026-01-01 10:05:00,0002,food,2,\n"
        "tx-c,2026-02-30 10:05:00,0002,food,3,1\n"
        "tx-d,2026-01-01 10:05:00,,food,4,2\n"
        "tx-e,2026-01-01 10:05:00,0002,food,4,2\n"
        "tx-f,2026-01-01 10:05:00\n",
        encoding="utf-8-sig",
    )
    first = run_cli(source, "--speed", "0")
    second = run_cli(source, "--speed", "0")

    assert first.returncode == second.returncode == 0
    assert (first.stdout, first.stderr) == (second.stdout, second.stderr)
    events = [json.loads(line) for line in first.stdout.splitlines()]
    assert [event["transaction_id"] for event in events] == ["tx-a", "tx-b", "tx-0"]
    assert events[0]["card_id"] == "0001"
    assert events[0]["amount"] == "3.00"
    assert [event["is_fraud"] for event in events] == [1, 0, None]
    summary = json.loads(first.stderr)
    assert summary["rows_read"] == 9
    assert summary["emitted"] == 3
    assert summary["out_of_order"] == 1
    assert summary["skipped"] == {
        "invalid_amount": 1,
        "duplicate_transaction_id": 1,
        "invalid_transaction_time": 1,
        "missing_required_fields": 1,
        "invalid_fraud_label": 1,
        "invalid_column_count": 1,
    }
    assert [issue["line"] for issue in summary["issues"]] == [3, 5, 7, 8, 9, 10]


def test_replay_applies_speed_to_event_gap(monkeypatch):
    first = Transaction(
        "tx-a", datetime(2026, 1, 1, 10), "0001", "food", Decimal(1), None
    )
    second = Transaction(
        "tx-b", datetime(2026, 1, 1, 10, 5), "0001", "food", Decimal(1), None
    )
    delays = []
    monkeypatch.setattr(replay_module.time, "sleep", delays.append)

    assert list(replay_module.replay([first, second], speed=2)) == [first, second]
    assert delays == [150]


def test_cli_rejects_invalid_header_and_speed(tmp_path):
    source = tmp_path / "transactions.csv"
    source.write_text("trans_num\n", encoding="utf-8")

    result = run_cli(source)
    assert result.returncode == 2
    assert not result.stdout
    assert "missing_csv_columns" in json.loads(result.stderr)["error"]

    result = run_cli(source, "--speed", "nan")
    assert result.returncode == 2
    assert not result.stdout
    assert "--speed" in result.stderr
