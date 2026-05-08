"""Construit dashboard_2026.json à partir du CSV race_chart + du calendrier 2026.

Lance :
    python projects/dashboard/build_dashboard_data.py

Sorties :
    projects/dashboard/web/data/dashboard_2026.json   (source canonique)
    docs/data/dashboard_2026.json                     (mirror servi par GitHub Pages)

La donnée brute (cumul de points par GP × pilote) est lue depuis le builder
race_chart_builder. Le calendrier 2026 est statique (calendar_2026.json).
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CSV_SRC = ROOT / "projects" / "race_chart_builder" / "web" / "data" / "f1_race_chart_fastf1_2026.csv"
CALENDAR_PATH = HERE / "calendar_2026.json"
OUT_WEB = HERE / "web" / "data" / "dashboard_2026.json"
OUT_DOCS = ROOT / "docs" / "data" / "dashboard_2026.json"

META_COLS = {"Pilote", "image", "team", "start"}


def load_calendar() -> dict:
    return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))


def load_drivers(csv_path: Path) -> tuple[list[dict], list[str]]:
    """Retourne (rows, gp_columns)."""
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        if not rows:
            raise ValueError(f"CSV vide : {csv_path}")
        gp_columns = [c for c in reader.fieldnames or [] if c not in META_COLS]
    return rows, gp_columns


def to_float(v: str | None) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except ValueError:
        return 0.0


def compute_kpis(rows: list[dict], gp_columns: list[str]) -> tuple[dict, str]:
    """Renvoie (kpis, last_gp_name)."""
    if not gp_columns:
        raise ValueError("Aucune colonne de GP dans le CSV")

    last_gp = gp_columns[-1]
    prev_gp = gp_columns[-2] if len(gp_columns) >= 2 else None

    standings = sorted(
        ({"name": r["Pilote"], "team": r.get("team", ""), "points": to_float(r[last_gp])} for r in rows),
        key=lambda d: d["points"],
        reverse=True,
    )
    leader = standings[0]
    second = standings[1] if len(standings) > 1 else {"name": "—", "team": "", "points": 0.0}
    leader_gap = int(leader["points"] - second["points"])

    if prev_gp is not None:
        gains = [
            {
                "name": r["Pilote"],
                "team": r.get("team", ""),
                "gain": to_float(r[last_gp]) - to_float(r[prev_gp]),
            }
            for r in rows
        ]
        winner = max(gains, key=lambda d: d["gain"])
    else:
        winner = {"name": leader["name"], "team": leader["team"], "gain": leader["points"]}

    return (
        {
            "leader":     {"name": leader["name"], "team": leader["team"], "points": int(leader["points"])},
            "second":     {"name": second["name"], "team": second["team"], "points": int(second["points"])},
            "leaderGap":  leader_gap,
            "lastWinner": {"name": winner["name"], "team": winner["team"], "gp": last_gp},
            "raceCount":  len(gp_columns),
        },
        last_gp,
    )


def find_round(rounds: Iterable[dict], gp_name: str) -> dict | None:
    for r in rounds:
        if r["name"] == gp_name:
            return r
    return None


def build(today: date | None = None) -> dict:
    rows, gp_columns = load_drivers(CSV_SRC)
    calendar = load_calendar()
    rounds = calendar["rounds"]
    total_races = calendar.get("totalRaces", len(rounds))

    kpis, last_gp_name = compute_kpis(rows, gp_columns)
    last_round = find_round(rounds, last_gp_name) or {}
    last_round_idx = next((i for i, r in enumerate(rounds) if r["name"] == last_gp_name), -1)
    next_round = rounds[last_round_idx + 1] if 0 <= last_round_idx < len(rounds) - 1 else None

    kpis["totalRaces"] = total_races

    return {
        "season": calendar["season"],
        "generatedAt": (today or date.today()).isoformat(),
        "lastGp": {
            "name":       last_gp_name,
            "shortName":  last_round.get("shortName", last_gp_name),
            "date":       last_round.get("date"),
            "isSprint":   bool(last_round.get("isSprint", False)),
            "winner":     {"name": kpis["lastWinner"]["name"], "team": kpis["lastWinner"]["team"]},
        },
        "nextGp": (
            {
                "name":      next_round["name"],
                "shortName": next_round["shortName"],
                "date":      next_round["date"],
                "isSprint":  bool(next_round.get("isSprint", False)),
            }
            if next_round else None
        ),
        "kpis": kpis,
    }


def write_outputs(payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    for target in (OUT_WEB, OUT_DOCS):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"[OK] {target.relative_to(ROOT)}")


def main() -> int:
    try:
        payload = build()
    except FileNotFoundError as e:
        print(f"[ERREUR] {e}", file=sys.stderr)
        return 1
    write_outputs(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
