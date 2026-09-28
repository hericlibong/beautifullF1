"""Décide si la pipeline de refresh doit tourner aujourd'hui.

Principe : on ne regarde PAS le calendrier du cron, on regarde l'écart entre
ce qui a été couru et ce qui a été publié. La pipeline doit tourner dès qu'un
GP déjà disputé n'apparaît pas encore dans `dashboard_2026.json`.

Pourquoi pas une fenêtre glissante de N jours (l'implémentation d'origine) :
un cron GitHub Actions est *best-effort* — il peut être retardé de plusieurs
heures ou purement abandonné en période de charge. Avec une fenêtre de 2 jours,
un cron sauté = un GP perdu définitivement, en silence. Avec une comparaison
couru/publié, n'importe quel run ultérieur rattrape le retard, et un run de
trop ne coûte que quelques dizaines de secondes.

Le script ne s'arrête JAMAIS avec un code d'erreur — il écrit simplement la
décision dans la variable de sortie GitHub Actions :
    should-refresh=true   → la pipeline doit tourner
    should-refresh=false  → on saute

Utilisation locale (debug) :
    python projects/dashboard/check_should_refresh.py
        → affiche la décision sur stdout
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CALENDAR_PATH = HERE / "calendar_2026.json"
DASHBOARD_PATH = HERE / "web" / "data" / "dashboard_2026.json"

# Délai laissé à FastF1 pour publier les résultats d'une course. Un GP couru
# hier est considéré comme "attendu dans les données" ; un GP couru aujourd'hui
# ne l'est pas encore.
PUBLISH_DELAY_DAYS = 1


def _played_gp_names(dashboard: dict) -> set[str]:
    """Noms des GP que le dashboard publié considère comme disputés."""
    return {
        entry.get("name")
        for entry in dashboard.get("calendar", [])
        if entry.get("status") == "played" and entry.get("name")
    }


def should_refresh(today: date | None = None) -> tuple[bool, str]:
    today = today or date.today()

    if not CALENDAR_PATH.exists():
        return False, f"calendar introuvable ({CALENDAR_PATH})"

    calendar = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    cutoff = today - timedelta(days=PUBLISH_DELAY_DAYS)

    raced: list[tuple[str, str]] = []
    for r in calendar.get("rounds", []):
        gp_date_str = r.get("date")
        name = r.get("name")
        if not gp_date_str or not name:
            continue
        try:
            gp_date = date.fromisoformat(gp_date_str)
        except ValueError:
            continue
        if gp_date <= cutoff:
            raced.append((name, gp_date_str))

    if not raced:
        return False, f"aucun GP disputé à ce jour (today={today.isoformat()})"

    if not DASHBOARD_PATH.exists():
        return True, f"dashboard absent ({DASHBOARD_PATH}) — première génération"

    try:
        dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return True, f"dashboard illisible ({exc}) — régénération"

    published = _played_gp_names(dashboard)
    missing = [(name, d) for name, d in raced if name not in published]

    if missing:
        detail = ", ".join(f"{name} ({d})" for name, d in missing)
        return True, f"{len(missing)} GP disputé(s) absent(s) des données : {detail}"

    last_name, last_date = raced[-1]
    return False, f"données à jour ({len(raced)} GP publiés, dernier : {last_name} {last_date})"


def main() -> int:
    ok, reason = should_refresh()
    print(f"should-refresh={'true' if ok else 'false'} — {reason}")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"should-refresh={'true' if ok else 'false'}\n")
            f.write(f"reason={reason}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
