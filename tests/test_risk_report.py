from pathlib import Path

from atlasanalytics.risk_report import build_risk_report_html, write_risk_report
from atlasanalytics.risk_synthetic import generate_synthetic_risk_observations


def test_synthetic_risk_scenario_is_reproducible_and_chronological() -> None:
    first = generate_synthetic_risk_observations(seed=17, observation_count=120)
    second = generate_synthetic_risk_observations(seed=17, observation_count=120)

    assert first == second
    assert len(first) == 120
    assert all(first[index].occurred_at < first[index + 1].occurred_at for index in range(119))
    assert all(0 <= row.score <= 1 for row in first)
    assert all(row.amount_minor > 0 for row in first)


def test_risk_report_contains_threshold_calibration_and_psi_panels() -> None:
    html = build_risk_report_html(
        generate_synthetic_risk_observations(seed=23, observation_count=180)
    )

    assert "SYNTHETIC SCORES" in html
    assert "Threshold trade-offs" in html
    assert "Calibration by score band" in html
    assert "Population Stability Index" in html
    assert "Selected operating point" in html
    assert 'class="best"><td>' in html
    assert "chronological holdout" in html.lower()
    assert "not a production loss estimate" in html


def test_risk_report_writer_creates_standalone_html(tmp_path: Path) -> None:
    output = write_risk_report(
        tmp_path / "risk.html",
        generate_synthetic_risk_observations(seed=31, observation_count=140),
    )

    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert content.startswith("<!doctype html>")
    assert "<style>" in content
    assert "Risk threshold evaluation" in content
