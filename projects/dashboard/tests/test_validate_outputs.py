"""Contrôle de cohérence inter-builders — rejoue l'incident du 14/09/2026.

Le refresh post-Madrid a publié un classement amputé du GP de Belgique sans
qu'aucune alarme ne se déclenche : le CSV race chart avait 13 GP, celui de la
heatmap 14. Ces tests verrouillent la détection de cet écart.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from projects.dashboard import validate_outputs as vo

RC_HEADER = ["Pilote", "image", "team", "start", "Australia", "Belgium"]
HM_HEADER = ["Driver", "DriverName", "Team", "EventNameFull", "Points", "TotalPoints"]


def _write_race_chart(path: Path, gp_columns: list[str], totals: dict[str, int]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Pilote", "image", "team", "start", *gp_columns])
        for name, total in totals.items():
            cumulative = [str(float(total))] * len(gp_columns)
            writer.writerow([name, "", "Mercedes", "0", *cumulative])


def _write_heatmap(path: Path, events: list[str], totals: dict[str, int]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HM_HEADER)
        writer.writeheader()
        for name, total in totals.items():
            for event in events:
                writer.writerow(
                    {
                        "Driver": name[:3].upper(),
                        "DriverName": name,
                        "Team": "Mercedes",
                        "EventNameFull": event,
                        "Points": 0,
                        "TotalPoints": total,
                    }
                )


@pytest.fixture()
def csvs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(vo, "RACE_CHART_CSV", tmp_path / "rc.csv")
    monkeypatch.setattr(vo, "HEATMAP_CSV", tmp_path / "hm.csv")
    return tmp_path


def test_consistent_sources_pass(csvs: Path) -> None:
    _write_race_chart(csvs / "rc.csv", ["Australia", "Belgium"], {"Kimi Antonelli": 292})
    _write_heatmap(csvs / "hm.csv", ["Australian GP", "Belgian GP"], {"Kimi Antonelli": 292})
    errors: list[str] = []
    vo.check_race_chart_vs_heatmap(errors)
    assert errors == []


def test_missing_gp_is_detected(csvs: Path) -> None:
    """Le scénario exact du run #35 : un GP perdu d'un seul côté."""
    _write_race_chart(csvs / "rc.csv", ["Australia"], {"Kimi Antonelli": 267})
    _write_heatmap(csvs / "hm.csv", ["Australian GP", "Belgian GP"], {"Kimi Antonelli": 292})
    errors: list[str] = []
    vo.check_race_chart_vs_heatmap(errors)
    assert any("nombre de GP divergent" in e for e in errors)
    assert any("267" in e and "292" in e for e in errors)


def test_point_mismatch_is_detected(csvs: Path) -> None:
    """Même nombre de GP mais totaux divergents : anomalie tout de même."""
    _write_race_chart(csvs / "rc.csv", ["Australia", "Belgium"], {"Kimi Antonelli": 280})
    _write_heatmap(csvs / "hm.csv", ["Australian GP", "Belgian GP"], {"Kimi Antonelli": 292})
    errors: list[str] = []
    vo.check_race_chart_vs_heatmap(errors)
    assert any("Kimi Antonelli" in e for e in errors)


def test_driver_absent_from_heatmap_is_detected(csvs: Path) -> None:
    _write_race_chart(csvs / "rc.csv", ["Australia"], {"Pilote Fantome": 10})
    _write_heatmap(csvs / "hm.csv", ["Australian GP"], {"Kimi Antonelli": 10})
    errors: list[str] = []
    vo.check_race_chart_vs_heatmap(errors)
    assert any("absent de la heatmap" in e for e in errors)


def test_dashboard_totals_must_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Total pilotes != total constructeurs = agrégation cassée."""
    payload = {
        "kpis": {"raceCount": 1},
        "lastGp": {"date": "2026-03-08"},
        "standings": {
            "drivers": [
                {
                    "name": "Kimi Antonelli",
                    "points": 25,
                    "progress": [{"gp": "Australia"}],
                }
            ],
            "constructors": [{"team": "Mercedes", "points": 18}],
        },
    }
    dashboard = tmp_path / "dashboard.json"
    dashboard.write_text(json.dumps(payload), encoding="utf-8")
    calendar = tmp_path / "calendar.json"
    calendar.write_text(
        json.dumps({"rounds": [{"round": 1, "name": "Australia", "date": "2026-03-08"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(vo, "DASHBOARD_JSON", dashboard)
    monkeypatch.setattr(vo, "CALENDAR_PATH", calendar)

    errors: list[str] = []
    vo.check_dashboard(errors)
    assert any("total pilotes" in e for e in errors)


def test_dashboard_detects_uncounted_past_gp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un GP déjà couru au calendrier mais absent du décompte doit alerter."""
    payload = {
        "kpis": {"raceCount": 1},
        "lastGp": {"date": "2026-03-15"},
        "standings": {
            "drivers": [
                {"name": "Kimi Antonelli", "points": 25, "progress": [{"gp": "Australia"}]}
            ],
            "constructors": [{"team": "Mercedes", "points": 25}],
        },
    }
    dashboard = tmp_path / "dashboard.json"
    dashboard.write_text(json.dumps(payload), encoding="utf-8")
    calendar = tmp_path / "calendar.json"
    calendar.write_text(
        json.dumps(
            {
                "rounds": [
                    {"round": 1, "name": "Australia", "date": "2026-03-08"},
                    {"round": 2, "name": "China", "date": "2026-03-15"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vo, "DASHBOARD_JSON", dashboard)
    monkeypatch.setattr(vo, "CALENDAR_PATH", calendar)

    errors: list[str] = []
    vo.check_dashboard(errors)
    assert any("China" in e for e in errors)
