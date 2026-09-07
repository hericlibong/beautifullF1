"""Nommage canonique des GP — non-régression sur la collision "Spain".

2026 compte deux GP espagnols : Barcelone (round 7, publié sous "Spain") et
Madrid (round 14). Tant que les deux portaient le même libellé, la colonne de
cumul de Barcelone était écrasée par celle de Madrid et Madrid n'apparaissait
jamais comme disputé. Ces tests verrouillent la règle de nommage à la source.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from projects.dashboard import build_dashboard_data as bd
from projects.dashboard import fetch_calendar
from projects.gp_naming import check_unique, col_name, find_duplicates, short_name

# ---------- col_name ----------


def test_barcelona_keeps_country_only_name() -> None:
    """Barcelone reste "Spain" : la colonne est déjà publiée sous ce nom."""
    assert col_name("Spain", "Barcelona") == "Spain"


def test_madrid_gets_its_own_name() -> None:
    assert col_name("Spain", "Madrid") == "Spain - Madrid"


def test_two_spanish_gps_are_distinct() -> None:
    assert col_name("Spain", "Barcelona") != col_name("Spain", "Madrid")


@pytest.mark.parametrize(
    ("country", "location", "expected"),
    [
        ("United States", "Miami Gardens", "United States - Miami Gardens"),
        ("United States", "Austin", "United States - Austin"),
        ("United States", "Las Vegas", "United States - Las Vegas"),
        ("Italy", "Monza", "Italy - Monza"),
        ("Monaco", "Monte Carlo", "Monaco"),
        ("Netherlands", "Zandvoort", "Netherlands"),
        ("Japan", "Suzuka", "Japan"),
    ],
)
def test_col_name_rules(country: str, location: str, expected: str) -> None:
    assert col_name(country, location) == expected


def test_col_name_tolerates_blank_location() -> None:
    assert col_name("Spain", "") == "Spain"
    assert col_name("  Italy  ", "  Monza  ") == "Italy - Monza"


# ---------- short_name ----------


def test_short_names_of_both_spanish_gps() -> None:
    assert short_name("Spain", "Barcelona") == "Barcelona"
    assert short_name("Spain - Madrid", "Madrid") == "Madrid"


def test_short_name_falls_back_on_location() -> None:
    """GP absent de SHORT_NAMES (saison antérieure, circuit ajouté) : on retombe
    sur la localité, puis sur le nom canonique."""
    assert short_name("France", "Le Castellet") == "Le Castellet"
    assert short_name("France", "") == "France"


# ---------- détection de collision ----------


def test_find_duplicates() -> None:
    assert find_duplicates(["Spain", "Italy", "Spain"]) == ["Spain"]
    assert find_duplicates(["Spain", "Spain - Madrid"]) == []


def test_check_unique_raises_on_collision() -> None:
    with pytest.raises(ValueError, match="Collision de noms de GP"):
        check_unique(["Spain", "Austria", "Spain"], context="test")


def test_check_unique_passes_on_distinct_names() -> None:
    check_unique(["Spain", "Spain - Madrid", "Italy - Monza"])


# ---------- cohérence avec le calendrier publié ----------


def _calendar() -> dict:
    return json.loads(
        (Path(fetch_calendar.__file__).parent / "calendar_2026.json").read_text(encoding="utf-8")
    )


def test_published_calendar_has_no_duplicate_name() -> None:
    check_unique([r["name"] for r in _calendar()["rounds"]], context="calendar_2026.json")


def test_published_calendar_matches_naming_rules() -> None:
    """Chaque shortName du calendrier publié est celui que produirait le builder."""
    for r in _calendar()["rounds"]:
        assert short_name(r["name"]) == r["shortName"], r["name"]


def test_published_race_chart_csv_has_no_duplicate_column() -> None:
    csv_path = bd.CSV_SRC
    header = csv_path.read_text(encoding="utf-8-sig").splitlines()[0]
    check_unique(header.split(","), context="le CSV race chart publié")


# ---------- bout en bout : le dashboard après Madrid ----------


@pytest.fixture
def csv_through_madrid(tmp_path: Path) -> Path:
    """CSV race chart couvrant les 14 premiers GP 2026, Barcelone et Madrid inclus."""
    gps = [
        "Australia",
        "China",
        "Japan",
        "United States - Miami Gardens",
        "Canada",
        "Monaco",
        "Spain",
        "Austria",
        "United Kingdom",
        "Belgium",
        "Hungary",
        "Netherlands",
        "Italy - Monza",
        "Spain - Madrid",
    ]
    # Cumuls strictement croissants : +25 par GP pour le leader, +18 pour le second.
    leader = [25 * (i + 1) for i in range(len(gps))]
    second = [18 * (i + 1) for i in range(len(gps))]
    p = tmp_path / "race_chart.csv"
    p.write_text(
        "Pilote,image,team,start," + ",".join(gps) + "\n"
        "Kimi Antonelli,img,Mercedes,0," + ",".join(str(float(v)) for v in leader) + "\n"
        "George Russell,img,Mercedes,0," + ",".join(str(float(v)) for v in second) + "\n",
        encoding="utf-8",
    )
    return p


def test_dashboard_after_madrid(csv_through_madrid: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bd, "CSV_SRC", csv_through_madrid)
    payload = bd.build(today=date(2026, 9, 14))

    # Madrid est le dernier GP disputé, et il est reconnu par le calendrier.
    assert payload["lastGp"]["name"] == "Spain - Madrid"
    assert payload["lastGp"]["shortName"] == "Madrid"
    assert payload["lastGp"]["date"] == "2026-09-13"
    assert payload["kpis"]["raceCount"] == 14

    cal = {c["name"]: c for c in payload["calendar"]}
    # Les deux GP espagnols sont joués, distinctement, chacun avec son vainqueur.
    assert cal["Spain"]["status"] == "played"
    assert cal["Spain"]["round"] == 7
    assert cal["Spain - Madrid"]["status"] == "played"
    assert cal["Spain - Madrid"]["round"] == 14
    assert cal["Spain"]["winner"] is not None
    assert cal["Spain - Madrid"]["winner"] is not None

    # Barcelone conserve son cumul (7e GP), non écrasé par celui de Madrid (14e).
    leader = payload["standings"]["drivers"][0]
    progress = {p["gp"]: p["cumulative"] for p in leader["progress"]}
    assert progress["Spain"] == 175
    assert progress["Spain - Madrid"] == 350
