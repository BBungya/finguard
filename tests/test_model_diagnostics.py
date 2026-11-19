import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
pytest.importorskip("sklearn")

from finguard.model_diagnostics import calibration, subgroup_errors


def test_subgroups_share_the_daily_budget():
    frame = pd.DataFrame(
        {
            "trans_num": ["a", "b", "c"],
            "trans_date_trans_time": pd.to_datetime(
                ["2020-07-01 01:00", "2020-07-01 12:00", "2020-07-01 20:00"]
            ),
            "cc_num": ["seen", "new", "seen"],
            "amt": [40, 200, 500],
            "is_fraud": [0, 1, 1],
        }
    )
    grouped = subgroup_errors(frame, np.array([0.9, 0.8, 0.7]), 1, {"new"})

    assert grouped["card"]["seen"]["fp"] == 1
    assert grouped["card"]["unseen"]["reviewed"] == 0
    assert grouped["card"]["unseen"]["fn"] == 1
    assert grouped["amount"]["200–<500"]["fn"] == 1
    assert grouped["hour"]["18–23"]["fn"] == 1


def test_calibration_includes_scores_at_interval_edges():
    measured = calibration(np.array([0, 0, 1]), np.array([0.0, 0.2, 1.0]))

    assert measured["brier"] == pytest.approx(0.04 / 3)
    assert measured["ece"] == pytest.approx(0.2 / 3)
    assert [item["lower"] for item in measured["bins"]] == [0.0, 0.2, 0.8]
    assert sum(item["count"] for item in measured["bins"]) == 3
