"""Tests E2E responsive : aucun débordement horizontal aux largeurs cibles.

On vérifie que le document et les conteneurs clés ne débordent pas (scrollWidth
<= clientWidth, à 1px près) à 375 / 768 / 1024 px, sur chaque onglet.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

WIDTHS = [375, 768, 1024]
TABS = ["drivers", "constructors", "calendar", "duel", "teammates"]


def _no_horizontal_overflow(page) -> bool:
    # +1 px de tolérance pour les arrondis sub-pixel
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
    )


@pytest.mark.parametrize("width", WIDTHS)
def test_no_page_overflow_on_each_tab(page, base_url, width):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(base_url)
    page.wait_for_selector(".dash-kpi")
    for tab in TABS:
        page.click(f'.dash-tab[data-tab="{tab}"]')
        page.wait_for_timeout(150)
        assert _no_horizontal_overflow(page), f"débordement à {width}px sur l'onglet {tab}"


@pytest.mark.parametrize("width", WIDTHS)
def test_no_overflow_with_driver_drilldown(page, base_url, width):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(base_url)
    row = page.locator("#standings-drivers tr.t-clickable").first
    row.wait_for()
    row.click()
    page.wait_for_selector("tr.t-detail .dash-driver-detail")
    assert _no_horizontal_overflow(page), f"débordement à {width}px (drill-down pilote)"
