"""Garde-fou anti-régression du CSV race chart.

Le CSV est reconstruit intégralement à chaque refresh. Après le GP de Madrid,
la session de Spa n'a pas pu être chargée côté CI : le `except: continue` du
builder l'a traitée comme une course non courue, la colonne "Belgium" a disparu
et tous les pilotes ont perdu les points de ce GP — classement pilotes,
constructeurs et duels qualif étaient faux d'un coup. Mieux vaut échouer et
conserver le fichier précédent que publier un classement amputé.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from projects.race_chart_builder.race_chart_builder_fastf1 import RaceChartBuilderFastF1

HEADER = ["Pilote", "image", "team", "start", "Australia", "Belgium"]
ROW = ["Max Verstappen", "", "Red Bull Racing", "0", "25.0", "43.0"]


def _builder(tmp_path: Path) -> RaceChartBuilderFastF1:
    builder = RaceChartBuilderFastF1(season=2026)
    builder.output_file = str(tmp_path / "race_chart.csv")
    return builder


def _write_existing(path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerow(ROW)


def test_missing_gp_aborts_the_export(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    _write_existing(builder.output_file)
    builder.race_keys = ["Australia"]  # Belgium a disparu du run courant
    builder.failed_rounds = [(10, "Belgium")]

    with pytest.raises(SystemExit) as excinfo:
        builder._assert_no_regression()
    message = str(excinfo.value)
    assert "Belgium" in message
    assert "round 10" in message


def test_same_gp_set_passes(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    _write_existing(builder.output_file)
    builder.race_keys = ["Australia", "Belgium"]
    builder._assert_no_regression()  # ne lève pas


def test_new_gp_appended_passes(tmp_path: Path) -> None:
    """Ajouter un GP est le cas nominal d'un refresh après course."""
    builder = _builder(tmp_path)
    _write_existing(builder.output_file)
    builder.race_keys = ["Australia", "Belgium", "Spain - Madrid"]
    builder._assert_no_regression()


def test_no_existing_file_passes(tmp_path: Path) -> None:
    """Première génération : aucun historique à préserver."""
    builder = _builder(tmp_path)
    builder.race_keys = ["Australia"]
    builder._assert_no_regression()
