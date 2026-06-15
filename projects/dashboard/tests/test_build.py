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


# ---------- compute_standings ----------


def test_compute_standings_drivers_ranked_and_gapped(fake_csv: Path) -> None:
    rows, gps = bd.load_drivers(fake_csv)
    standings = bd.compute_standings(rows, gps)
    drivers = standings["drivers"]
    # Trois pilotes, triés par points décroissants
    assert [d["name"] for d in drivers] == [
        "Kimi Antonelli",
        "George Russell",
        "Charles Leclerc",
    ]
    # Rangs séquentiels
    assert [d["rank"] for d in drivers] == [1, 2, 3]
    # Le leader a un écart nul, les autres négatifs
    assert drivers[0]["leaderGap"] == 0
    assert drivers[1]["leaderGap"] == 80 - 100
    assert drivers[2]["leaderGap"] == 59 - 100
    # shortName généré
    assert drivers[0]["shortName"] == "K. Antonelli"


def test_compute_standings_delta_last_gp(fake_csv: Path) -> None:
    rows, gps = bd.load_drivers(fake_csv)
    drivers = bd.compute_standings(rows, gps)["drivers"]
    by_name = {d["name"]: d for d in drivers}
    # Antonelli : 100 - 72 = 28 ; Russell : 80 - 60 = 20 ; Leclerc : 59 - 50 = 9
    assert by_name["Kimi Antonelli"]["deltaLastGp"] == 28
    assert by_name["George Russell"]["deltaLastGp"] == 20
    assert by_name["Charles Leclerc"]["deltaLastGp"] == 9


def test_compute_standings_constructors_aggregated(fake_csv: Path) -> None:
    rows, gps = bd.load_drivers(fake_csv)
    constructors = bd.compute_standings(rows, gps)["constructors"]
    by_team = {c["team"]: c for c in constructors}
    # Mercedes = Antonelli (100) + Russell (80) = 180 ; Ferrari = Leclerc (59)
    assert by_team["Mercedes"]["points"] == 180
    assert by_team["Ferrari"]["points"] == 59
    assert by_team["Mercedes"]["rank"] == 1
    assert by_team["Mercedes"]["leaderGap"] == 0
    assert by_team["Ferrari"]["leaderGap"] == 59 - 180


def test_compute_standings_progress_cumulative(fake_csv: Path) -> None:
    rows, gps = bd.load_drivers(fake_csv)
    drivers = bd.compute_standings(rows, gps)["drivers"]
    leader = drivers[0]  # Antonelli
    cumuls = [p["cumulative"] for p in leader["progress"]]
    gains = [p["gain"] for p in leader["progress"]]
    assert cumuls == [18, 47, 72, 100]
    assert gains == [18, 29, 25, 28]


def test_compute_standings_empty_gp_columns() -> None:
    assert bd.compute_standings([], []) == {"drivers": [], "constructors": []}


# ---------- Calendrier & collision "Spain" ----------


def test_calendar_status_and_winner(fake_csv: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bd, "CSV_SRC", fake_csv)
    payload = bd.build(today=date(2026, 5, 8))
    cal = {c["name"]: c for c in payload["calendar"]}
    # Les 4 GP du CSV sont "played" avec un vainqueur
    assert cal["Australia"]["status"] == "played"
    assert cal["Australia"]["winner"] is not None
    # Le GP juste après le dernier joué est "next"
    next_name = payload["nextGp"]["name"]
    assert cal[next_name]["status"] == "next"
    assert cal[next_name]["winner"] is None


def test_spain_collision_two_distinct_rounds(
    fake_csv: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Les deux GP espagnols (Barcelone r7 / Madrid r14) doivent rester distincts."""
    monkeypatch.setattr(bd, "CSV_SRC", fake_csv)
    payload = bd.build(today=date(2026, 5, 8))
    spain_entries = [c for c in payload["calendar"] if c["name"].startswith("Spain")]
    # Deux entrées distinctes, jamais fusionnées
    assert len(spain_entries) == 2
    names = {c["name"] for c in spain_entries}
    assert names == {"Spain", "Spain - Madrid"}
    rounds = {c["round"] for c in spain_entries}
    assert rounds == {7, 14}
    shorts = {c["shortName"] for c in spain_entries}
    assert shorts == {"Barcelona", "Madrid"}


def test_calendar_covers_full_season(fake_csv: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bd, "CSV_SRC", fake_csv)
    payload = bd.build(today=date(2026, 5, 8))
    assert len(payload["calendar"]) == payload["kpis"]["totalRaces"]
    # Rounds uniques et séquentiels
    rounds = sorted(c["round"] for c in payload["calendar"])
    assert rounds == list(range(1, len(rounds) + 1))
