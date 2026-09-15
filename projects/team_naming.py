"""Nommage des écuries — source de vérité partagée par tous les builders.

FastF1 ne renvoie pas un nom d'écurie stable : selon la session (Race, Sprint,
Qualifying, Sprint Qualifying) et selon la source interrogée, la même écurie
arrive sous "Red Bull" ou "Red Bull Racing", "RB F1 Team" ou "Racing Bulls",
"Alpine F1 Team" ou "Alpine", "Cadillac F1 Team" ou "Cadillac".

Deux conséquences si on laisse passer les variantes :
  - le front-end résout les couleurs via ``web/assets/teams.json``, keyé par le
    nom canonique : toute variante retombe sur le gris de fallback ;
  - les duels coéquipiers regroupent par écurie : une variante = une écurie
    fantôme de plus, et les duels se retrouvent éclatés sur deux clés.

Les clés canoniques ci-dessous sont exactement celles de
``projects/dashboard/web/assets/teams.json`` — les deux fichiers doivent rester
alignés (cf. test_team_naming.py).
"""

from __future__ import annotations

# Nom canonique (== clé de teams.json) -> variantes rencontrées côté FastF1.
_ALIASES: dict[str, tuple[str, ...]] = {
    "Red Bull Racing": ("Red Bull",),
    "Racing Bulls": ("RB F1 Team", "RB", "Visa Cash App RB"),
    "Alpine": ("Alpine F1 Team",),
    "Cadillac": ("Cadillac F1 Team",),
    "Haas F1 Team": ("Haas",),
    "Audi": ("Audi F1 Team", "Sauber", "Kick Sauber"),
    "Aston Martin": ("Aston Martin F1 Team",),
    "Mercedes": ("Mercedes-AMG Petronas", "Mercedes F1 Team"),
}

# Index inverse, comparé en minuscules pour absorber la casse.
_CANONICAL_BY_VARIANT: dict[str, str] = {}
for _canonical, _variants in _ALIASES.items():
    _CANONICAL_BY_VARIANT[_canonical.lower()] = _canonical
    for _variant in _variants:
        _CANONICAL_BY_VARIANT[_variant.lower()] = _canonical


def canonical_team(name: str | None) -> str:
    """Retourne le nom d'écurie canonique (celui de teams.json).

    Un nom inconnu est renvoyé tel quel : une nouvelle écurie doit apparaître
    dans le dashboard, pas disparaître — c'est la couleur de fallback qui
    signalera qu'il faut l'ajouter ici et dans teams.json.
    """
    if not name:
        return ""
    return _CANONICAL_BY_VARIANT.get(str(name).strip().lower(), str(name).strip())
