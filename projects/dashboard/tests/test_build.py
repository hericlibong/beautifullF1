"""Tests minimaux du builder dashboard.

On simule un mini-CSV race chart et on vérifie la structure et les KPI.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from projects.dashboard import build_dashboard_data as bd


@pytest.fixture
def fake_csv(tmp_path: Path) -> Path:
    p = tmp_path / "race_chart.csv"
    p.write_text(
        "Pilote,image,team,start,Australia,China,Japan,United States - Miami Gardens\n"
        "Kimi Antonelli,img,Mercedes,0,18.0,47.0,72.0,100.0\n"
        "George Russell,img,Mercedes,0,15.0,40.0,60.0,80.0\n"
        "Charles Leclerc,img,Ferrari,0,12.0,30.0,50.0,59.0\n",
        encoding="utf-8",
    )
    return p


def test_compute_kpis(fake_csv: Path) -> None:
    rows, gps = bd.load_drivers(fake_csv)
    kpis, last_gp = bd.compute_kpis(rows, gps)
    assert last_gp == "United States - Miami Gardens"
    assert kpis["leader"]["name"] == "Kimi Antonelli"
    assert kpis["leader"]["points"] == 100
    assert kpis["second"]["name"] == "George Russell"
    assert kpis["leaderGap"] == 20
    # Le vainqueur du dernier GP : celui qui a le plus gagné entre Japan et Miami.
    # Antonelli +28, Russell +20, Leclerc +9 → Antonelli.
    assert kpis["lastWinner"]["name"] == "Kimi Antonelli"
    assert kpis["raceCount"] == 4


def test_build_payload_shape(fake_csv: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bd, "CSV_SRC", fake_csv)
    payload = bd.build(today=date(2026, 5, 8))
    assert payload["season"] == 2026
    assert payload["generatedAt"] == "2026-05-08"
    assert payload["lastGp"]["shortName"] == "Miami"
    assert payload["lastGp"]["isSprint"] is True
    assert payload["nextGp"]["shortName"] == "Canada"
    assert "kpis" in payload
    assert payload["kpis"]["totalRaces"] >= 22


def test_payload_is_json_serialisable(fake_csv: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bd, "CSV_SRC", fake_csv)
    payload = bd.build()
    json.dumps(payload, ensure_ascii=False)
