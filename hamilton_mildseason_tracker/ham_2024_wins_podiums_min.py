# hamilton_mildseason_tracker/ham_2024_wins_podiums_min.py
# -*- coding: utf-8 -*-
import fastf1
from fastf1.ergast import Ergast
import pandas as pd

LH_ID = "hamilton"
YEAR = 2024

def season_total_rounds(year: int) -> int:
    sched = fastf1.get_event_schedule(year)
    rounds = sched.loc[sched["RoundNumber"] > 0, "RoundNumber"]
    return int(rounds.max()) if not rounds.empty else 0

def main():
    erg = Ergast(result_type="pandas", auto_cast=True)

    # 1) VICTOIRES (direct depuis les standings cumulés 'last')
    st = erg.get_driver_standings(season=YEAR, round="last")
    st_df = st.content[0] if hasattr(st, "content") else st
    wins = int(st_df[st_df["driverId"] == LH_ID]["wins"].iloc[0])

    # 2) PODIUMS (compte des courses où position finale ∈ {1,2,3})
    k = season_total_rounds(YEAR)
    podiums = 0
    for rnd in range(1, k + 1):
        rr = erg.get_race_results(season=YEAR, round=rnd, limit=1000)
        rr_df = rr.content[0] if hasattr(rr, "content") else rr
        if rr_df is None or rr_df.empty:
            continue
        row = rr_df[rr_df["driverId"] == LH_ID]
        if row.empty:
            continue
        # position finale numérique (Ergast renvoie le classement final mis à jour)
        pos = pd.to_numeric(row.iloc[0].get("position"), errors="coerce")
        if pd.notna(pos) and int(pos) in (1, 2, 3):
            podiums += 1

    print(f"Saison {YEAR} — Lewis Hamilton")
    print(f"Victoires: {wins}")
    print(f"Podiums : {podiums}")

if __name__ == "__main__":
    main()
