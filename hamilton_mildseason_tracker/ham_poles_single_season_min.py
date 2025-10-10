# hamilton_mildseason_tracker/ham_poles_single_season_strict.py
# -*- coding: utf-8 -*-
"""
Poles d'Hamilton pour UNE saison, en s'appuyant uniquement sur les endpoints dédiés :
- fastf1.get_event_schedule (pour connaître les rounds)
- Ergast.get_qualifying_results(season=Y, round=R) (classement des qualifs du round)
On compte 'position == 1' pour driverId == 'hamilton'.
"""

import argparse
import pandas as pd
import fastf1
from fastf1.ergast import Ergast

LH_ID = "hamilton"
DEFAULT_CACHE = ".fastf1cache"

def enable_cache(path: str) -> None:
    try:
        fastf1.Cache.enable_cache(path)
    except Exception:
        pass

def count_poles_strict(year: int, driver_id: str = LH_ID) -> tuple[int, list[int]]:
    erg = Ergast(result_type="pandas", auto_cast=True)

    # Rounds de la saison (évite d'appeler des rounds inexistants)
    sched = fastf1.get_event_schedule(year)
    rounds = sched.loc[sched["RoundNumber"] > 0, "RoundNumber"].astype(int).tolist()

    poles = 0
    rounds_with_pole: list[int] = []

    for rnd in rounds:
        qr = erg.get_qualifying_results(season=year, round=rnd, limit=1000)
        qdf = qr.content[0] if hasattr(qr, "content") else qr
        if qdf is None or qdf.empty:
            continue
        row = qdf[qdf["driverId"] == driver_id]
        if row.empty:
            continue
        pos = pd.to_numeric(row.iloc[0].get("position"), errors="coerce")
        if pd.notna(pos) and int(pos) == 1:
            poles += 1
            rounds_with_pole.append(rnd)

    return poles, rounds_with_pole

def main():
    parser = argparse.ArgumentParser(description="Compter les poles d'Hamilton pour UNE saison (fiable, par round).")
    parser.add_argument("--season", type=int, required=True, help="Saison (ex: 2007 ou 2008)")
    parser.add_argument("--driver", type=str, default=LH_ID, help="driverId Ergast (défaut: hamilton)")
    parser.add_argument("--cache", type=str, default=DEFAULT_CACHE, help="Dossier cache FastF1 (défaut .fastf1cache)")
    args = parser.parse_args()

    enable_cache(args.cache)
    poles, rounds_with_pole = count_poles_strict(args.season, args.driver)

    print(f"Saison {args.season} — {args.driver} — Poles: {poles}")
    if rounds_with_pole:
        print("Rounds avec pole:", ", ".join(map(str, rounds_with_pole)))

if __name__ == "__main__":
    main()
