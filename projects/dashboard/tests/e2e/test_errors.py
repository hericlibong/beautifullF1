"""Tests E2E de la gestion d'erreur : une ressource requise manquante doit
afficher une bannière visible (et non une page blanche silencieuse)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


def test_missing_required_resource_shows_banner(page, base_url):
    # Simule l'indisponibilité d'une ressource REQUISE
    page.route("**/dashboard_2026.json", lambda route: route.abort())
    page.goto(base_url)
    banner = page.locator("#dash-error-banner")
    banner.wait_for(state="visible", timeout=10000)
    assert banner.inner_text().strip() != ""


def test_missing_optional_resource_degrades_gracefully(page, base_url):
    # Une ressource OPTIONNELLE manquante ne doit PAS bloquer le rendu ni afficher la bannière
    page.route("**/qualifying_2026.json", lambda route: route.abort())
    page.goto(base_url)
    page.wait_for_selector(".dash-kpi")
    assert page.locator(".dash-kpi").count() == 4
    assert page.locator("#dash-error-banner").count() == 0
    # L'onglet Coéquipiers affiche un état "indisponible", pas une erreur globale
    page.click('.dash-tab[data-tab="teammates"]')
    page.wait_for_selector("#dash-teammates-content .dash-duel-empty")
