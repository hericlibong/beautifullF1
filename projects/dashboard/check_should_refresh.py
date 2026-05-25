"""Décide si la pipeline de refresh doit tourner aujourd'hui.

Lit calendar_<season>.json et regarde si un GP a eu lieu dans les 2 derniers
jours (cron du lundi + filet de sécurité du mardi).

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
LOOKBACK_DAYS = 2  # accepte les GP de J-1 et J-2 (lundi + mardi en filet)


def should_refresh(today: date | None = None) -> tuple[bool, str]:
    today = today or date.today()
    if not CALENDAR_PATH.exists():
        return False, f"calendar introuvable ({CALENDAR_PATH})"

    data = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    window = {today - timedelta(days=d) for d in range(1, LOOKBACK_DAYS + 1)}

    for r in data.get("rounds", []):
        gp_date_str = r.get("date")
        if not gp_date_str:
            continue
        try:
            gp_date = date.fromisoformat(gp_date_str)
        except ValueError:
            continue
        if gp_date in window:
            return True, f"GP détecté : {r.get('shortName', r.get('name'))} ({gp_date_str})"

    return False, f"aucun GP dans les {LOOKBACK_DAYS} derniers jours (today={today.isoformat()})"


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
