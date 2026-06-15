"""Tests des fonctions pures du builder qualifying (duels coéquipiers).

On ne touche pas au réseau (FastF1) : on teste le formatage des temps et la
logique d'agrégation des duels `build_teammate_pairs` sur des données simulées.
"""

from __future__ import annotations

from projects.dashboard import build_qualifying_data as bq

# ---------- format_lap / to_seconds ----------


def test_format_lap_with_minutes() -> None:
    assert bq.format_lap(75.234) == "1:15.234"


def test_format_lap_sub_minute() -> None:
    assert bq.format_lap(59.5) == "59.500"


def test_format_lap_none() -> None:
    assert bq.format_lap(None) is None


def test_to_seconds_none() -> None:
    assert bq.to_seconds(None) is None


# ---------- build_teammate_pairs ----------


def _driver(full: str, team: str, best: float | None, q3: bool = False, pos: int = 1) -> dict:
    return {
        "fullName": full,
        "abbr": full.split()[-1][:3].upper(),
        "team": team,
        "position": pos,
        "bestTimeSec": best,
        "bestTimeStr": bq.format_lap(best) if best is not None else None,
        "q3": q3,
    }


def _session(round_no: int, gp: str, short: str, stype: str, drivers: list[dict]) -> dict:
    return {"round": round_no, "gp": gp, "shortName": short, "type": stype, "drivers": drivers}


def test_build_teammate_pairs_basic_duel() -> None:
    sessions = [
        _session(
            1,
            "Australia",
            "Melbourne",
            "Q",
            [
                _driver("George Russell", "Mercedes", 80.100, q3=True, pos=1),
                _driver("Kimi Antonelli", "Mercedes", 80.350, q3=True, pos=2),
            ],
        )
    ]
    teams = bq.build_teammate_pairs(sessions)
    assert len(teams) == 1
    team = teams[0]
    assert team["team"] == "Mercedes"
    # Ordre alpha des pilotes : George avant Kimi
    assert team["drivers"] == ["George Russell", "Kimi Antonelli"]
    assert len(team["sessions"]) == 1
    s = team["sessions"][0]
    # Russell plus rapide (80.100 < 80.350)
    assert s["fastest"] == "George Russell"
    assert s["gapSec"] == 0.25
    assert s["type"] == "Q"
    # H2H : 1 victoire Russell en Q
    assert team["h2h"]["Q"]["George Russell"] == 1
    # Compteur Q3 : les deux ont atteint Q3
    assert team["q3Count"]["George Russell"] == 1
    assert team["q3Count"]["Kimi Antonelli"] == 1


def test_build_teammate_pairs_skips_missing_time() -> None:
    """Un duel où un pilote n'a pas de temps n'est pas comptabilisé en session."""
    sessions = [
        _session(
            1,
            "Australia",
            "Melbourne",
            "Q",
            [
                _driver("George Russell", "Mercedes", 80.100, q3=True),
                _driver("Kimi Antonelli", "Mercedes", None, q3=False),
            ],
        )
    ]
    teams = bq.build_teammate_pairs(sessions)
    team = teams[0]
    assert team["sessions"] == []  # pas de duel exploitable
    # Mais le compteur Q3 de Russell est tout de même enregistré
    assert team["q3Count"]["George Russell"] == 1


def test_build_teammate_pairs_sprint_quali_no_q3() -> None:
    """En SQ, q3 ne doit jamais incrémenter le compteur Q3."""
    sessions = [
        _session(
            2,
            "China",
            "Shanghai",
            "SQ",
            [
                _driver("George Russell", "Mercedes", 90.000, q3=False),
                _driver("Kimi Antonelli", "Mercedes", 90.200, q3=False),
            ],
        )
    ]
    teams = bq.build_teammate_pairs(sessions)
    team = teams[0]
    assert team["q3Count"] == {}
    assert team["sessions"][0]["type"] == "SQ"
    assert team["h2h"]["SQ"]["George Russell"] == 1
