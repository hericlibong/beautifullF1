"""Tests E2E du dashboard (Playwright) — non-régression après la refacto ES6.

Servent à garantir que le découpage en modules reste iso-fonctionnel : chargement
des données, navigation par onglets, drill-downs, switch de langue, embed viz.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


def test_kpis_and_header_load(page, base_url):
    page.goto(base_url)
    # 4 tuiles KPI rendues
    page.wait_for_selector(".dash-kpi")
    assert page.locator(".dash-kpi").count() == 4
    # Le sous-titre n'est plus "Chargement…" (données chargées)
    subtitle = page.locator("#dash-subtitle").inner_text()
    assert "Chargement" not in subtitle and subtitle.strip() != ""


def test_standings_drivers_table_populated(page, base_url):
    page.goto(base_url)
    page.wait_for_selector("#standings-drivers tr.t-clickable")
    assert page.locator("#standings-drivers tr.t-clickable").count() > 0


def test_tabs_switch(page, base_url):
    page.goto(base_url)
    page.wait_for_selector(".dash-tab")
    for tab in ("constructors", "calendar", "duel", "teammates", "drivers"):
        page.click(f'.dash-tab[data-tab="{tab}"]')
        pane = page.locator(f"#standings-pane-{tab}")
        assert "active" in (pane.get_attribute("class") or "")


def test_driver_drilldown_opens_detail(page, base_url):
    page.goto(base_url)
    row = page.locator("#standings-drivers tr.t-clickable").first
    row.wait_for()
    row.click()
    page.wait_for_selector("tr.t-detail .dash-driver-detail")
    assert page.locator("tr.t-detail .dash-driver-detail").count() == 1


def test_circuit_drilldown_with_history(page, base_url):
    page.goto(base_url)
    page.click('.dash-tab[data-tab="calendar"]')
    # Les données circuit sont chargées à la demande : attendre que la ligne
    # devienne cliquable (classe ajoutée après le fetch paresseux).
    spain = page.locator('#dash-calendar li[data-gp="Spain"].dash-cal-clickable')
    spain.wait_for()
    spain.click()
    page.wait_for_selector(".dash-circuit-detail .dash-history")
    # Le scatter chronologie et les barres palmarès sont présents
    assert page.locator(".dash-history-svg").count() >= 1
    assert page.locator(".dash-history-bars").count() >= 1


def test_duel_renders_panel(page, base_url):
    page.goto(base_url)
    page.click('.dash-tab[data-tab="duel"]')
    page.wait_for_selector("#dash-duel-content .dash-duel-headers")
    assert page.locator("#dash-duel-content .dash-duel-metrics").count() == 1


def test_lang_switch_persists(page, base_url):
    page.goto(base_url)
    page.wait_for_selector(".dash-kpi")
    page.click('#lang-switch button[data-lang="en"]')
    # Le rechargement applique la langue
    page.wait_for_function("document.documentElement.lang === 'en'")
    assert page.evaluate("localStorage.getItem('bf1-lang')") == "en"
    # Remet en FR pour ne pas polluer l'état partagé
    page.click('#lang-switch button[data-lang="fr"]')
    page.wait_for_function("document.documentElement.lang === 'fr'")


def test_embed_viz_open_and_back(page, base_url):
    page.goto(base_url)
    shortcut = page.locator(".dash-shortcut:not(.is-disabled)").first
    shortcut.wait_for()
    shortcut.click()
    page.wait_for_selector("#dash-embed-host:not([hidden])")
    assert page.locator("#dash-embed-frame").is_visible()
    page.click("#dash-embed-back")
    page.wait_for_selector("#dash-embed-host[hidden]", state="attached")
