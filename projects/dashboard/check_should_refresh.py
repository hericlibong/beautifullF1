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

Le script écrit la décision dans la variable de sortie GitHub Actions :
    should-refresh=true   → la pipeline doit tourner
    should-refresh=false  → on saute
Une erreur de calendrier retourne un code non nul : l'absence de décision doit
être visible, jamais transformée silencieusement en ``false``.

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


class RefreshCheckError(RuntimeError):
    """Le contrôle ne peut pas rendre une décision fiable."""


def _load_calendar() -> dict:
    """Charge et valide les champs indispensables du calendrier.

    Une erreur de calendrier doit faire échouer le workflow : répondre
    silencieusement ``should-refresh=false`` masquerait exactement le type de
    panne que ce contrôle est censé rendre visible.
    """
    if not CALENDAR_PATH.exists():
        raise RefreshCheckError(f"calendar introuvable ({CALENDAR_PATH})")

    try:
        calendar = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RefreshCheckError(f"calendar illisible ({CALENDAR_PATH}) : {exc}") from exc

    rounds = calendar.get("rounds") if isinstance(calendar, dict) else None
    if not isinstance(rounds, list) or not rounds:
        raise RefreshCheckError("calendar invalide : 'rounds' doit être une liste non vide")

    for index, race in enumerate(rounds, start=1):
        if not isinstance(race, dict):
            raise RefreshCheckError(f"calendar invalide : entrée #{index} non structurée")
        name = race.get("name")
        gp_date = race.get("date")
        if not isinstance(name, str) or not name.strip():
            raise RefreshCheckError(f"calendar invalide : nom absent à l'entrée #{index}")
        if not isinstance(gp_date, str):
            raise RefreshCheckError(f"calendar invalide : date absente pour {name}")
        try:
            date.fromisoformat(gp_date)
        except ValueError as exc:
            raise RefreshCheckError(f"calendar invalide : date '{gp_date}' pour {name}") from exc

    return calendar


def _played_gp_names(dashboard: dict) -> set[str]:
    """Noms des GP que le dashboard publié considère comme disputés."""
    return {
        entry.get("name")
        for entry in dashboard.get("calendar", [])
        if entry.get("status") == "played" and entry.get("name")
    }


def should_refresh(today: date | None = None) -> tuple[bool, str]:
    today = today or date.today()
    calendar = _load_calendar()
    cutoff = today - timedelta(days=PUBLISH_DELAY_DAYS)

    raced: list[tuple[str, str]] = []
    for r in calendar.get("rounds", []):
        gp_date_str = r.get("date")
        name = r.get("name")
        gp_date = date.fromisoformat(gp_date_str)
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
    try:
        ok, reason = should_refresh()
    except RefreshCheckError as exc:
        print(f"check-error={exc}", file=sys.stderr)
        return 1
    print(f"should-refresh={'true' if ok else 'false'} — {reason}")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"should-refresh={'true' if ok else 'false'}\n")
            f.write(f"reason={reason}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
