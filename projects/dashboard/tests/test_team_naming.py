"""Nommage canonique des écuries — alignement avec teams.json.

FastF1 renvoie la même écurie sous plusieurs libellés selon la session
("Red Bull" en course, "Red Bull Racing" en sprint qualif). Le front résout les
couleurs via teams.json, keyé par le nom canonique : toute variante qui passe
retombe sur le gris de fallback et, côté duels, crée une écurie fantôme.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from projects.team_naming import _ALIASES, canonical_team

TEAMS_JSON = Path(__file__).resolve().parents[1] / "web" / "assets" / "teams.json"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Red Bull", "Red Bull Racing"),
        ("RB F1 Team", "Racing Bulls"),
        ("Alpine F1 Team", "Alpine"),
        ("Cadillac F1 Team", "Cadillac"),
        ("red bull", "Red Bull Racing"),
        ("  Red Bull  ", "Red Bull Racing"),
    ],
)
def test_variants_resolve_to_canonical(raw: str, expected: str) -> None:
    assert canonical_team(raw) == expected


def test_canonical_names_are_stable() -> None:
    """Un nom déjà canonique reste inchangé."""
    for canonical in _ALIASES:
        assert canonical_team(canonical) == canonical


def test_unknown_team_is_passed_through() -> None:
    """Une écurie inconnue doit apparaître telle quelle, pas disparaître."""
    assert canonical_team("Nouvelle Ecurie") == "Nouvelle Ecurie"
    assert canonical_team(None) == ""
    assert canonical_team("") == ""


def test_canonical_names_exist_in_teams_json() -> None:
    """Les clés canoniques doivent être celles que le front sait colorer."""
    known = set(json.loads(TEAMS_JSON.read_text(encoding="utf-8"))["teams"])
    unknown = sorted(name for name in _ALIASES if name not in known)
    assert not unknown, f"absentes de teams.json : {unknown}"
