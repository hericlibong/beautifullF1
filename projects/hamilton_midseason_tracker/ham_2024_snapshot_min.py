# hamilton_mildseason_tracker/ham_2024_snapshot_min.py
# -*- coding: utf-8 -*-
"""
Snapshot complet 2024 pour Lewis Hamilton (une seule saison, code minimal).
Produit un CSV avec les colonnes demandées.
"""

import pandas as pd
import fastf1
from fastf1.ergast import Ergast

YEAR = 2024
LH_ID = "hamilton"
OUT_CSV = "hamilton_2024_snapshot.csv"
DEFAULT_CACHE = ".fastf1cache"


def enable_cache(path=DEFAULT_CACHE):
    try:
        fastf1.Cache.enable_cache(path)
    except Exception:
        pass


def assemble_season_df(mr) -> pd.DataFrame:
    """Ergast peut renvoyer un MultiResponse (liste de DF). On assemble + ajoute 'round'."""
    if hasattr(mr, "content") and isinstance(mr.content, list):
        desc = mr.description if mr.description is not None else pd.DataFrame()
        rounds = list(
            pd.to_numeric(desc.get("round", range(1, len(mr.content) + 1)), errors="coerce")
        )
        parts = []
        for rnum, df_part in zip(rounds, mr.content):
            dfp = df_part.copy()
            dfp["round"] = rnum
            parts.append(dfp)
        df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    else:
        df = mr if isinstance(mr, pd.DataFrame) else pd.DataFrame()
        if not df.empty and "round" not in df.columns:
            df["round"] = pd.NA

    if not df.empty:
        df["round"] = pd.to_numeric(df["round"], errors="coerce")
        for col in ("position", "points"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        for col in ("status", "driverId", "constructorId"):
            if col in df.columns:
                df[col] = df[col].astype(str)
    return df


def season_total_rounds(year: int) -> int:
    sched = fastf1.get_event_schedule(year)
    r = sched.loc[sched["RoundNumber"] > 0, "RoundNumber"]
    return int(r.max()) if not r.empty else 0


def get_event_name_date(year: int, rnd: int):
    sched = fastf1.get_event_schedule(year)
    ev = sched.get_event_by_round(rnd)
    name = str(getattr(ev, "EventName", f"Round {rnd}"))
    date = getattr(ev, "EventDateUtc", None)
    if pd.isna(date):
        date = getattr(ev, "EventDate", None)
    date_str = pd.to_datetime(date).strftime("%Y-%m-%d") if date is not None else ""
    return name, date_str


def count_podiums_via_round_calls(erg: Ergast, k: int) -> int:
    """
    Compte les podiums en interrogeant chaque round (comme le script minimal qui marche).
    On se repose sur la position finale déjà recalculée côté Ergast (post-DQ).
    """
    podiums = 0
    for rnd in range(1, k + 1):
        rr = erg.get_race_results(season=YEAR, round=rnd, limit=1000)
        rr_df = rr.content[0] if hasattr(rr, "content") else rr
        if rr_df is None or rr_df.empty:
            continue
        row = rr_df[rr_df["driverId"] == LH_ID]
        if row.empty:
            continue
        pos = pd.to_numeric(row.iloc[0].get("position"), errors="coerce")
        if pd.notna(pos) and int(pos) in (1, 2, 3):
            podiums += 1
    return podiums


def compute_snapshot_2024() -> pd.DataFrame:
    erg = Ergast(result_type="pandas", auto_cast=True)

    # Saison complète – course + qualifs (utilisé pour le reste des champs)
    race_df = assemble_season_df(erg.get_race_results(season=YEAR, limit=1000))
    quali_df = assemble_season_df(erg.get_qualifying_results(season=YEAR, limit=1000))

    # Cutoff = dernier round
    K = season_total_rounds(YEAR)

    # Nom & date du GP cutoff
    gp_name_cutoff, gp_date_cutoff = get_event_name_date(YEAR, K)

    # Standings officiels au round K (points, rang, WINS)
    st = erg.get_driver_standings(season=YEAR, round=K, limit=1000)
    st_df = st.content[0] if hasattr(st, "content") else st
    lh_row = st_df[st_df["driverId"] == LH_ID].iloc[0]
    hamilton_rank = int(lh_row["position"])
    hamilton_points = float(lh_row["points"])
    leader_points = float(st_df.iloc[0]["points"])
    points_behind = round(leader_points - hamilton_points, 2)
    pct_of_leader = round((hamilton_points / leader_points) if leader_points > 0 else 0.0, 3)
    wins_to_date = int(lh_row["wins"])

    # ---- podiums (fiable) : via appels par round ----
    podiums_to_date = count_podiums_via_round_calls(erg, K)

    # Lignes LH (course/qualifs) 1..K (pour le reste des champs)
    race_k = race_df[race_df["round"] <= K].copy()
    quali_k = quali_df[quali_df["round"] <= K].copy()
    lh_race = race_k[race_k["driverId"] == LH_ID].copy()
    started = int(len(lh_race))

    # Poles
    lh_quali = quali_k[quali_k["driverId"] == LH_ID]
    poles_to_date = int((pd.to_numeric(lh_quali["position"], errors="coerce") == 1).sum())

    # DNF (heuristique statut)
    dnf_to_date = 0
    if "status" in lh_race.columns:
        status = lh_race["status"].astype(str)
        finished = status.str.contains("Finished", na=False) | status.str.contains("Lap", na=False)
        dnf_to_date = int((~finished).sum())

    # % GP marqués (>0 pt)
    pts_series = pd.to_numeric(lh_race["points"], errors="coerce").fillna(0)
    scored_rounds = int((pts_series > 0).sum())
    races_scored_pct = 0.0 if started == 0 else round(scored_rounds / started, 2)
    race_scored_pct_main = races_scored_pct
    zero_point_weekends_to_date = started - scored_rounds

    # Moyenne position d’arrivée (classement brut du dump saison – OK pour 2024)
    finishing_list = (
        pd.to_numeric(lh_race.get("position"), errors="coerce").dropna().astype(int).tolist()
    )
    weekend_scored_pct = round(
        float(pd.Series(finishing_list).mean()) if finishing_list else 0.0, 2
    )

    # Constructor au round K + points teammate cumulés
    constructor_id = None
    teammate_points_to_date = 0.0
    if not lh_race.empty:
        last_round_rows = lh_race[lh_race["round"] == K]
        if not last_round_rows.empty:
            constructor_id = str(last_round_rows.iloc[0].get("constructorId", None))
        for r, cid in lh_race[["round", "constructorId"]].dropna().values:
            rr_r = race_k[race_k["round"] == r]
            mates = rr_r[(rr_r["constructorId"] == str(cid)) & (rr_r["driverId"] != LH_ID)]
            if not mates.empty:
                teammate_points_to_date += float(
                    pd.to_numeric(mates["points"], errors="coerce").fillna(0).sum()
                )

    teammate_points_to_date = round(teammate_points_to_date, 1)
    teammate_gap = round(hamilton_points - teammate_points_to_date, 1)

    row = {
        "year": YEAR,
        "round_cutoff": K,
        "gp_name_cutoff": gp_name_cutoff,
        "gp_date_cutoff": gp_date_cutoff,
        "hamilton_rank": hamilton_rank,
        "hamilton_points": hamilton_points,
        "leader_points": leader_points,
        "points_behind": points_behind,
        "pct_of_leader": pct_of_leader,
        "wins_to_date": wins_to_date,
        "podiums_to_date": podiums_to_date,  # <-- maintenant calculé comme le script minimal
        "poles_to_date": poles_to_date,
        "dnf_to_date": dnf_to_date,
        "races_started": started,
        "races_scored_pct": races_scored_pct,
        "race_scored_pct_main": race_scored_pct_main,
        "weekend_scored_pct": weekend_scored_pct,
        "zero_point_weekends_to_date": zero_point_weekends_to_date,
        "constructor_id": constructor_id,
        "teammate_points_to_date": teammate_points_to_date,
        "teammate_gap": teammate_gap,
    }
    return pd.DataFrame([row])


def main():
    enable_cache()
    df = compute_snapshot_2024()
    df.to_csv(OUT_CSV, index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
