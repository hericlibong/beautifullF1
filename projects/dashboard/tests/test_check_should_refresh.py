"""Tests de la décision de refresh.

Le point sensible : la décision ne doit dépendre QUE de l'écart entre GP
disputés et GP publiés, jamais du jour de la semaine ni de la fraîcheur du
dernier cron — c'est ce qui a fait perdre le GP de Bakou le 28/09/2026.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from projects.dashboard import check_should_refresh as mod

CALENDAR = {
    "rounds": [
        {"round": 13, "name": "Italy - Monza", "shortName": "Monza", "date": "2026-09-06"},
        {"round": 14, "name": "Spain - Madrid", "shortName": "Madrid", "date": "2026-09-13"},
        # Bakou tombe un SAMEDI : c'est le cas qu'une fenêtre glissante rate.
        {"round": 15, "name": "Azerbaijan", "shortName": "Baku", "date": "2026-09-26"},
        {"round": 16, "name": "Bahrain", "shortName": "Sepang", "date": "2026-10-04"},
    ]
}


def _write(tmp_path, monkeypatch, calendar=CALENDAR, played=()):
    cal = tmp_path / "calendar_2026.json"
    cal.write_text(json.dumps(calendar), encoding="utf-8")
    monkeypatch.setattr(mod, "CALENDAR_PATH", cal)

    dash = tmp_path / "dashboard_2026.json"
    if played is not None:
        entries = [
            {"name": r["name"], "status": "played" if r["name"] in played else "upcoming"}
            for r in calendar["rounds"]
        ]
        dash.write_text(json.dumps({"calendar": entries}), encoding="utf-8")
    monkeypatch.setattr(mod, "DASHBOARD_PATH", dash)
    return dash


UP_TO_MADRID = ("Italy - Monza", "Spain - Madrid")
UP_TO_BAKU = UP_TO_MADRID + ("Azerbaijan",)


def test_refresh_quand_un_gp_dispute_manque(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, played=UP_TO_MADRID)
    ok, reason = mod.should_refresh(date(2026, 9, 28))
    assert ok
    assert "Azerbaijan" in reason


def test_pas_de_refresh_quand_les_donnees_sont_a_jour(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, played=UP_TO_BAKU)
    ok, reason = mod.should_refresh(date(2026, 9, 28))
    assert not ok
    assert "à jour" in reason


@pytest.mark.parametrize("day", [29, 30])
def test_rattrapage_les_jours_suivants(tmp_path, monkeypatch, day):
    """Un cron sauté le lundi doit être rattrapé mardi, mercredi, n'importe quand.

    C'est la régression de l'incident du 28/09/2026 : avec l'ancienne fenêtre de
    2 jours, un GP couru le samedi 26 sortait de la fenêtre dès le mardi 29.
    """
    _write(tmp_path, monkeypatch, played=UP_TO_MADRID)
    ok, reason = mod.should_refresh(date(2026, 9, day))
    assert ok, reason


def test_pas_de_refresh_le_jour_meme_de_la_course(tmp_path, monkeypatch):
    """FastF1 n'a pas encore propagé les résultats — on attend le lendemain."""
    _write(tmp_path, monkeypatch, played=UP_TO_MADRID)
    ok, _ = mod.should_refresh(date(2026, 9, 26))
    assert not ok


def test_refresh_des_le_lendemain_de_la_course(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, played=UP_TO_MADRID)
    ok, _ = mod.should_refresh(date(2026, 9, 27))
    assert ok


def test_dashboard_absent_declenche_une_generation(tmp_path, monkeypatch):
    dash = _write(tmp_path, monkeypatch, played=UP_TO_BAKU)
    dash.unlink()
    ok, reason = mod.should_refresh(date(2026, 9, 28))
    assert ok
    assert "absent" in reason


def test_dashboard_illisible_declenche_une_generation(tmp_path, monkeypatch):
    dash = _write(tmp_path, monkeypatch, played=UP_TO_BAKU)
    dash.write_text("{ pas du json", encoding="utf-8")
    ok, reason = mod.should_refresh(date(2026, 9, 28))
    assert ok
    assert "illisible" in reason


def test_calendar_absent_fait_echouer_le_controle(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "CALENDAR_PATH", tmp_path / "nope.json")
    with pytest.raises(mod.RefreshCheckError, match="introuvable"):
        mod.should_refresh(date(2026, 9, 28))


def test_avant_le_premier_gp(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, played=())
    ok, reason = mod.should_refresh(date(2026, 1, 15))
    assert not ok
    assert "aucun GP disputé" in reason


def test_date_invalide_fait_echouer_le_controle(tmp_path, monkeypatch):
    calendar = {"rounds": [{"name": "Bogus", "date": "pas-une-date"}, *CALENDAR["rounds"]]}
    _write(tmp_path, monkeypatch, calendar=calendar, played=UP_TO_BAKU)
    with pytest.raises(mod.RefreshCheckError, match="date 'pas-une-date'"):
        mod.should_refresh(date(2026, 9, 28))


def test_calendar_json_invalide_fait_echouer_le_controle(tmp_path, monkeypatch):
    cal = tmp_path / "calendar_2026.json"
    cal.write_text("{ pas du json", encoding="utf-8")
    monkeypatch.setattr(mod, "CALENDAR_PATH", cal)

    with pytest.raises(mod.RefreshCheckError, match="illisible"):
        mod.should_refresh(date(2026, 9, 28))


def test_calendar_sans_rounds_fait_echouer_le_controle(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch, calendar={"rounds": []}, played=())
    with pytest.raises(mod.RefreshCheckError, match="liste non vide"):
        mod.should_refresh(date(2026, 9, 28))


def test_main_retourne_un_code_erreur_si_le_controle_est_impossible(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "CALENDAR_PATH", tmp_path / "nope.json")
    assert mod.main() == 1
