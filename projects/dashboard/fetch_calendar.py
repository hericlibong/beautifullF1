"""Régénère calendar_2026.json depuis FastF1.

À lancer ponctuellement (idéalement une seule fois en début de saison, et si le
calendrier officiel évolue). Le fichier produit est ensuite consommé par
build_dashboard_data.py.

Convention des noms de GP : définie une seule fois dans projects/gp_naming.py,
partagée avec race_chart_builder pour que les colonnes du CSV et les clés du
calendrier soient rigoureusement identiques.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import fastf1

HERE = Path(__file__).resolve().parent

# projects/ n'est pas un package installé : on l'ajoute à sys.path pour importer
# le nommage partagé (voir aussi race_chart_builder_fastf1.py).
_PROJECTS_DIR = str(HERE.parent)
if _PROJECTS_DIR not in sys.path:
    sys.path.insert(0, _PROJECTS_DIR)

from gp_naming import check_unique, col_name, short_name  # noqa: E402

OUT = HERE / "calendar_2026.json"
SEASON = 2026


def main() -> int:
    schedule = fastf1.get_event_schedule(SEASON, include_testing=False)
    rounds = []
    for _, row in schedule.iterrows():
        country = str(row.get("Country", ""))
        location = str(row.get("Location", ""))
        name = col_name(country, location)
        rounds.append(
            {
                "round": int(row["RoundNumber"]),
                "name": name,
                "shortName": short_name(name, location),
                "date": str(row["EventDate"])[:10],
                "isSprint": str(row.get("EventFormat", "")).startswith("sprint"),
            }
        )

    # Deux GP ne peuvent pas partager un "name" : c'est la clé de rapprochement
    # avec les colonnes du CSV race chart dans build_dashboard_data.py.
    check_unique([r["name"] for r in rounds], context="calendar_2026.json")

    payload = {
        "season": SEASON,
        "totalRaces": len(rounds),
        "rounds": rounds,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {OUT.relative_to(HERE.parents[1])} ({len(rounds)} GP)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
