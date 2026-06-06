"""Construit circuits_2026.json : fiche par circuit pour le drill-down calendrier.

Pour chaque GP du calendrier 2026 :
    - tracé du circuit (télémétrie du meilleur tour d'une saison réelle récente),
    - longueur, nombre de virages, nombre de tours,
    - meilleur tour de la saison source (pilote + temps),
    - vainqueurs des 3 dernières saisons (2023-2025).

⚠️ Builder LENT (chargement télémétrie de ~22 circuits). À lancer
MANUELLEMENT, pas dans le workflow auto :
    python projects/dashboard/build_circuits_data.py

Les tracés et l'historique ne changent quasi jamais : un run en début de
saison suffit. Le vainqueur 2026 d'un GP est pris côté front depuis le
dashboard JSON (calendar[].winner), pas ici.

Sorties :
    projects/dashboard/web/data/circuits_2026.json
    docs/data/circuits_2026.json
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CALENDAR_PATH = HERE / "calendar_2026.json"
OUT_WEB = HERE / "web" / "data" / "circuits_2026.json"
OUT_DOCS = ROOT / "docs" / "data" / "circuits_2026.json"

SEASON = 2026
# Saisons réelles d'où l'on tire le tracé et l'historique (la plus récente d'abord)
HISTORY_YEARS = [2025, 2024, 2023]
TRACK_POINTS = 120  # sous-échantillonnage du tracé


def load_calendar() -> dict:
    return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))


def format_lap(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    return f"{minutes}:{secs:06.3f}" if minutes else f"{secs:.3f}"


def resample(points: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    """Sous-échantillonne une polyligne à n points (indices régulièrement espacés)."""
    if len(points) <= n:
        return points
    idx = np.linspace(0, len(points) - 1, n).round().astype(int)
    return [points[i] for i in idx]


def rotate(x: float, y: float, deg: float) -> tuple[float, float]:
    rad = np.deg2rad(deg)
    return (
        x * np.cos(rad) - y * np.sin(rad),
        x * np.sin(rad) + y * np.cos(rad),
    )


def build_track(year: int, gp_name: str) -> dict | None:
    """Charge la télémétrie du meilleur tour et retourne tracé + métriques.

    Retourne None si la session ou la télémétrie n'est pas disponible.
    """
    try:
        session = fastf1.get_session(year, gp_name, "R")
        session.load(laps=True, telemetry=True, weather=False, messages=False)
    except Exception as e:
        print(f"    [track {year}] échec chargement : {e}", file=sys.stderr)
        return None

    try:
        fastest = session.laps.pick_fastest()
        tel = fastest.get_telemetry()
    except Exception as e:
        print(f"    [track {year}] pas de télémétrie : {e}", file=sys.stderr)
        return None

    if tel is None or tel.empty or "X" not in tel.columns:
        return None

    ci = session.get_circuit_info()
    rotation = float(getattr(ci, "rotation", 0.0) or 0.0)
    n_corners = int(len(ci.corners)) if ci.corners is not None else None

    xs = tel["X"].astype(float).values
    ys = tel["Y"].astype(float).values

    # Rotation pour orienter correctement le tracé
    rot = [rotate(x, y, rotation) for x, y in zip(xs, ys)]
    rx = np.array([p[0] for p in rot])
    ry = np.array([p[1] for p in rot])

    # Normalisation dans un carré 0..1000 en préservant le ratio
    min_x, max_x = rx.min(), rx.max()
    min_y, max_y = ry.min(), ry.max()
    span = max(max_x - min_x, max_y - min_y) or 1.0
    norm = [
        (
            round(float((x - min_x) / span * 1000), 1),
            round(float((y - min_y) / span * 1000), 1),
        )
        for x, y in zip(rx, ry)
    ]
    norm = resample(norm, TRACK_POINTS)

    length_m = None
    if "Distance" in tel.columns:
        try:
            length_m = int(float(tel["Distance"].max()))
        except (ValueError, TypeError):
            length_m = None

    record = None
    if fastest is not None and not pd.isna(fastest.get("LapTime")):
        record = {
            "driver": str(fastest.get("Driver", "")),
            "time": format_lap(float(fastest["LapTime"].total_seconds())),
            "year": year,
        }

    return {
        "trackPath": norm,
        "trackFromYear": year,
        "lengthKm": round(length_m / 1000, 3) if length_m else None,
        "corners": n_corners,
        "laps": int(session.total_laps) if session.total_laps else None,
        "lapRecord": record,
    }


def winner_for(year: int, gp_name: str) -> dict | None:
    """Charge les résultats (léger) et retourne le vainqueur."""
    try:
        session = fastf1.get_session(year, gp_name, "R")
        session.load(laps=False, telemetry=False, weather=False, messages=False)
    except Exception:
        return None
    res = session.results
    if res is None or res.empty:
        return None
    row = res.iloc[0]
    return {
        "year": year,
        "driver": str(row.get("FullName", "")),
        "abbr": str(row.get("Abbreviation", "")),
        "team": str(row.get("TeamName", "")),
    }


def build_circuit(gp: dict) -> dict:
    name = gp["name"]
    print(f"  - {gp['shortName']} ({name})")

    # Nom à résoudre via FastF1 (peut différer du name d'affichage).
    # Pour un circuit sans données historiques (ex. Madrid, nouveau en 2026),
    # mettre "fastf1Name": null dans le calendrier => pas de tracé ni d'historique.
    fastf1_name = gp.get("fastf1Name", name)

    track = None
    winners = []
    if fastf1_name:
        # Tracé : première saison réelle qui répond
        for yr in HISTORY_YEARS:
            track = build_track(yr, fastf1_name)
            if track:
                break
        # Vainqueurs historiques (3 saisons)
        for yr in HISTORY_YEARS:
            w = winner_for(yr, fastf1_name)
            if w:
                winners.append(w)

    circuit = {
        "gpName": name,
        "shortName": gp.get("shortName", name),
        "round": gp.get("round"),
        "isSprint": bool(gp.get("isSprint", False)),
        "pastWinners": winners,
    }
    if track:
        circuit.update(track)
    else:
        circuit["trackPath"] = None
        circuit["trackFromYear"] = None
    return circuit


def main() -> int:
    calendar = load_calendar()
    rounds = calendar["rounds"]

    print(f"[INFO] Construction des fiches circuit pour {len(rounds)} GP…")
    circuits = {}
    for gp in rounds:
        circuits[gp["name"]] = build_circuit(gp)

    payload = {
        "season": SEASON,
        "generatedAt": date.today().isoformat(),
        "circuits": circuits,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    for target in (OUT_WEB, OUT_DOCS):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"[OK] {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
