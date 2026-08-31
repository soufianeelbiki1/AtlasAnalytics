from pathlib import Path

from atlasanalytics.dashboard import build_dashboard_html, write_dashboard
from atlasanalytics.warehouse import build_warehouse


def test_dashboard_is_generated_from_warehouse_metrics() -> None:
    connection = build_warehouse()
    try:
        html = build_dashboard_html(connection)
        attempts = connection.execute("select count(*) from fact_authorization").fetchone()[0]
        issuer = connection.execute(
            "select issuer_name from dim_issuer order by issuer_id limit 1"
        ).fetchone()[0]
    finally:
        connection.close()

    assert "SYNTHETIC DATA" in html
    assert f"{int(attempts):,}" in html
    assert str(issuer) in html
    assert "Issuer performance" in html
    assert "Decline mix" in html
    assert "Issuer anomaly signals" in html
    assert "diagnostic flag" in html


def test_dashboard_writer_creates_standalone_html(tmp_path: Path) -> None:
    output = write_dashboard(tmp_path / "dashboard.html")

    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert content.startswith("<!doctype html>")
    assert "<style>" in content
    assert "Payments operations" in content
