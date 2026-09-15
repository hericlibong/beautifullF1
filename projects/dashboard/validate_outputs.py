"""Contrôle de cohérence des données produites — dernière barrière avant publication.

Lancé par build_all.py après les builders et avant la propagation vers docs/.
Sort en code 1 dès qu'une incohérence est détectée : en CI, le job échoue et
l'étape de commit n'est jamais atteinte, donc le site continue de servir les
dernières données saines.

Pourquoi ce filet existe
------------------------
Les builders sont indépendants et reconstruisent tout à chaque run. Chacun
traite une session FastF1 illisible comme un GP « non couru » (`except:
continue`) : un incident réseau passager suffit à faire disparaître un GP et,
le cumul étant recalculé de zéro, à retirer ses points à tous les pilotes.

C'est arrivé le 14/09/2026 : Spa a disparu du seul CSV race chart, la heatmap
l'a conservé, et un classement faux (Antonelli 267 au lieu de 292) a été publié
sans qu'aucune alarme ne se déclenche. Les deux sources dérivant des mêmes
résultats, les confronter détecte l'anomalie quel que soit le builder fautif.

Lance :
    python projects/dashboard/validate_outputs.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RACE_CHART_CSV = (
    ROOT / "projects" / "race_chart_builder" / "outputs" / "f1_race_chart_fastf1_2026.csv"
)
HEATMAP_CSV = (
    ROOT / "projects" / "season_summary_heatmap" / "outputs" / "f1_2026_leaders_heatmap.csv"
)
DASHBOARD_JSON = HERE / "web" / "data" / "dashboard_2026.json"
CALENDAR_PATH = HERE / "calendar_2026.json"

META_COLS = {"Pilote", "image", "team", "start"}


def _to_int(value: str | None) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def check_race_chart_vs_heatmap(errors: list[str]) -> None:
    """Les deux CSV doivent couvrir le même nombre de GP et les mêmes totaux."""
    if not RACE_CHART_CSV.exists() or not HEATMAP_CSV.exists():
        errors.append("CSV manquant : impossible de croiser race chart et heatmap")
        return

    with RACE_CHART_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rc_rows = list(reader)
        gp_columns = [c for c in reader.fieldnames or [] if c not in META_COLS]

    with HEATMAP_CSV.open(encoding="utf-8", newline="") as f:
        hm_rows = list(csv.DictReader(f))

    hm_events: list[str] = []
    for row in hm_rows:
        event = row.get("EventNameFull", "")
        if event and event not in hm_events:
            hm_events.append(event)

    if len(gp_columns) != len(hm_events):
        errors.append(
            f"nombre de GP divergent : race chart={len(gp_columns)} "
            f"({gp_columns[-1] if gp_columns else '-'} en dernier), "
            f"heatmap={len(hm_events)} ({hm_events[-1] if hm_events else '-'} en dernier). "
            "Un builder a perdu un GP — relancer avant de publier."
        )

    if not gp_columns:
        errors.append("aucune colonne de GP dans le CSV race chart")
        return

    last_gp = gp_columns[-1]
    hm_totals = {r["DriverName"]: _to_int(r.get("TotalPoints")) for r in hm_rows}
    for row in rc_rows:
        name = row["Pilote"]
        rc_points = _to_int(row.get(last_gp))
        hm_points = hm_totals.get(name)
        if hm_points is None:
            errors.append(f"{name} absent de la heatmap")
        elif hm_points != rc_points:
            errors.append(f"{name} : {rc_points} pts (race chart) vs {hm_points} pts (heatmap)")


def check_dashboard(errors: list[str]) -> None:
    """Le JSON publié doit être interne­ment cohérent et couvrir tous les GP courus."""
    if not DASHBOARD_JSON.exists():
        errors.append("dashboard_2026.json manquant")
        return

    data = json.loads(DASHBOARD_JSON.read_text(encoding="utf-8"))
    drivers = data["standings"]["drivers"]
    constructors = data["standings"]["constructors"]

    race_count = data["kpis"]["raceCount"]
    progress_len = len(drivers[0]["progress"]) if drivers else 0
    if race_count != progress_len:
        errors.append(
            f"raceCount={race_count} mais {progress_len} GP dans la progression des pilotes"
        )

    total_drivers = sum(d["points"] for d in drivers)
    total_teams = sum(c["points"] for c in constructors)
    if total_drivers != total_teams:
        errors.append(f"total pilotes ({total_drivers}) != total constructeurs ({total_teams})")

    # Tous les GP dont la date est passée doivent être comptabilisés : c'est le
    # symptôme direct d'un GP perdu par un builder.
    calendar = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))
    last_gp_date = data.get("lastGp", {}).get("date", "")
    expected = [r for r in calendar["rounds"] if r["date"] <= last_gp_date]
    if len(expected) != race_count:
        missing = [
            r["name"]
            for r in expected
            if r["name"] not in {p["gp"] for p in drivers[0]["progress"]}
        ]
        errors.append(
            f"{len(expected)} GP courus au calendrier jusqu'au {last_gp_date} "
            f"mais raceCount={race_count}"
            + (f" — manquant(s) : {', '.join(missing)}" if missing else "")
        )


def main() -> int:
    errors: list[str] = []
    check_race_chart_vs_heatmap(errors)
    check_dashboard(errors)

    if errors:
        print("[ECHEC] Donnees incoherentes, publication interrompue :", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("[OK] Donnees coherentes (race chart, heatmap, dashboard).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
