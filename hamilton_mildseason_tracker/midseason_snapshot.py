# hamilton_mildseason_tracker/midseason_snapshot.py
# -*- coding: utf-8 -*-
"""
Snapshot 'mi-saison' de Lewis Hamilton :
Compare la saison en cours, au même nombre de GP (K), avec chaque saison depuis 2007.

Sortie : CSV identique à hamilton_midseason_snapshot.csv (mêmes colonnes).
Dépendances : fastf1>=3.5, pandas
"""

from __future__ import annotations
import argparse
import datetime as dt
from typing import Dict, List, Tuple
import time

import pandas as pd
import fastf1
from fastf1.ergast import Ergast

# --- Paramètres de base
LH_DRIVER_ID = "hamilton"  # Ergast driverId
START_SEASON = 2007  # début de carrière F1 de LH
DEFAULT_CACHE = ".fastf1cache"  # dossier cache pour FastF1


# ---------- Utilitaires cache / détection K ----------
def enable_cache(path: str) -> None:
    try:
        fastf1.Cache.enable_cache(path)
    except Exception:
        pass


def get_current_season_and_round(
    erg: Ergast, season_arg: int | None, round_arg: int | None
) -> Tuple[int, int]:
    if season_arg and round_arg:
        return season_arg, round_arg
    year = season_arg or dt.date.today().year
    standings = erg.get_driver_standings(season=year, round="last")
    desc = getattr(standings, "description", None)
    if desc is None or desc.empty:
        return year, (round_arg or 1)
    last_round = int(desc.iloc[-1]["round"])
    return year, (round_arg or last_round)


# ---------- Calendrier ----------
def season_total_rounds(year: int) -> int:
    schedule = fastf1.get_event_schedule(year)
    rounds = schedule.loc[schedule["RoundNumber"] > 0, "RoundNumber"]
    return int(rounds.max()) if not rounds.empty else 0


def get_event_name_and_date(year: int, rnd: int) -> Tuple[str, str]:
    try:
        schedule = fastf1.get_event_schedule(year)
        event = schedule.get_event_by_round(rnd)
        name = str(getattr(event, "EventName", f"Round {rnd}"))
        date = getattr(event, "EventDateUtc", None)
        if pd.isna(date):
            date = getattr(event, "EventDate", None)
        date_str = pd.to_datetime(date).strftime("%Y-%m-%d") if date is not None else ""
        return name, date_str
    except Exception:
        return f"Round {rnd}", ""


# ---------- Préchargement Ergast (assemble MultiResponse -> DataFrame) ----------
def _assemble_multiresponse(mr) -> pd.DataFrame:
    if hasattr(mr, "content") and isinstance(mr.content, list):
        desc = mr.description if mr.description is not None else pd.DataFrame()
        rounds = list(
            pd.to_numeric(
                desc.get("round", pd.Series(range(1, len(mr.content) + 1))), errors="coerce"
            )
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
    # types utiles
    if not df.empty:
        df["round"] = pd.to_numeric(df["round"], errors="coerce")
        for col in ("points", "position"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        # sécuriser status/constructorId/driverId
        for col in ("status", "constructorId", "driverId"):
            if col in df.columns:
                df[col] = df[col].astype(str)
    return df


def prefetch_season_dfs(erg: Ergast, year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rr = erg.get_race_results(season=year, limit=1000)  # toutes les courses
    race_df = _assemble_multiresponse(rr)
    qr = erg.get_qualifying_results(season=year, limit=1000)  # toutes les qualifs
    quali_df = _assemble_multiresponse(qr)
    return race_df, quali_df


# ---------- Aides d'agrégation ----------
def _apply_disqualifications_and_rank(race_df: pd.DataFrame) -> pd.DataFrame:
    """
    Retourne un DF avec une 'rank_after_dq' par round :
    - on EXCLUT les lignes dont status contient 'Disqualified'
    - on trie par 'position' numérique croissante
    - on assigne 1,2,3,… par round (classement effectif post-DQ)
    """
    if race_df.empty:
        return race_df.assign(rank_after_dq=pd.Series(dtype="float"))

    df = race_df.copy()

    # flag DQ
    dq_mask = df["status"].str.contains("Disqualified", case=False, na=False)
    df = df[~dq_mask].copy()

    # position numérique (sécurisée)
    df["pos_num"] = pd.to_numeric(df.get("position"), errors="coerce")

    # classement effectif : trier par 'pos_num' et numéroter
    df.sort_values(["round", "pos_num"], inplace=True, kind="mergesort")
    df["rank_after_dq"] = df.groupby("round").cumcount() + 1

    return df


def _dnf_mask(df: pd.DataFrame) -> pd.Series:
    status = df["status"].astype(str)
    finished = status.str.contains("Finished", na=False) | status.str.contains("Lap", na=False)
    return ~finished


# ---------- Cumuls sur K premiers GP ----------
def cumulate_to_round_k(
    erg: Ergast, year: int, k: int, race_df: pd.DataFrame, quali_df: pd.DataFrame
) -> Dict[str, any]:
    total_rounds = season_total_rounds(year)
    k_eff = min(k, total_rounds if total_rounds > 0 else k)

    # Sous-ensembles 1..K
    race_k = race_df[race_df["round"] <= k_eff].copy()
    quali_k = quali_df[quali_df["round"] <= k_eff].copy()

    # Classement effectif (post-DQ)
    race_ranked = _apply_disqualifications_and_rank(race_k)

    # Lignes LH (course/qualifs) 1..K
    lh_race = race_ranked[race_ranked["driverId"] == LH_DRIVER_ID].copy()
    lh_quali = quali_k[quali_k["driverId"] == LH_DRIVER_ID].copy()

    # started
    started = int(len(lh_race))

    # victoires / podiums (après DQ)
    wins = int((lh_race["rank_after_dq"] == 1).sum())
    podiums = int(lh_race["rank_after_dq"].isin([1, 2, 3]).sum())

    # poles
    qpos = pd.to_numeric(lh_quali.get("position"), errors="coerce")
    poles = int((qpos == 1).sum())

    # dnf (d’après statut original)
    dnf = int(_dnf_mask(lh_race).sum()) if "status" in lh_race.columns else 0

    # points course cumul (info interne)
    points_course = float(pd.to_numeric(lh_race.get("points"), errors="coerce").fillna(0).sum())

    # moyenne position d’arrivée (après DQ)
    finishing_list = (
        pd.to_numeric(lh_race.get("rank_after_dq"), errors="coerce").dropna().astype(int).tolist()
    )
    weekend_scored_pct = round(
        float(pd.Series(finishing_list).mean()) if finishing_list else 0.0, 2
    )

    # GP marqués (>0 pt)
    scored_rounds = int((pd.to_numeric(lh_race.get("points"), errors="coerce").fillna(0) > 0).sum())
    races_scored_pct = 0.0 if started == 0 else round(scored_rounds / started, 2)
    race_scored_pct_main = races_scored_pct
    zero_point_weekends = started - scored_rounds

    # Teammate points (après DQ aussi, car on part de race_ranked filtré)
    teammate_points = 0.0
    constructor_id_at_k = None
    if not lh_race.empty:
        lh_rounds = lh_race[["round", "constructorId"]].dropna()
        for _, row in lh_rounds.iterrows():
            r = int(row["round"])
            cid = str(row["constructorId"])
            rr_r = race_ranked[race_ranked["round"] == r]
            mates = rr_r[(rr_r["constructorId"] == cid) & (rr_r["driverId"] != LH_DRIVER_ID)]
            if not mates.empty:
                teammate_points += float(
                    pd.to_numeric(mates["points"], errors="coerce").fillna(0).sum()
                )
            if r == k_eff:
                constructor_id_at_k = cid

    # Standings officiels au round K (points & rang & leader)
    standings = erg.get_driver_standings(season=year, round=k_eff, limit=1000)
    s_tbl = standings.content[0] if hasattr(standings, "content") else standings

    h_rank = None
    h_points = points_course
    leader_points = None
    if s_tbl is not None and not s_tbl.empty:
        leader_points = float(pd.to_numeric(s_tbl.iloc[0]["points"], errors="coerce"))
        lh_row = s_tbl[s_tbl["driverId"] == LH_DRIVER_ID]
        if not lh_row.empty:
            try:
                h_rank = int(lh_row.iloc[0]["position"])
            except Exception:
                h_rank = None
            h_points = float(pd.to_numeric(lh_row.iloc[0]["points"], errors="coerce"))

    points_behind = (
        round(leader_points - h_points, 2)
        if (leader_points is not None and h_points is not None)
        else None
    )
    pct_of_leader = (
        round((h_points / leader_points), 3)
        if (leader_points and leader_points > 0 and h_points is not None)
        else None
    )

    gp_name_cutoff, gp_date_cutoff = get_event_name_and_date(year, k_eff)

    return {
        "year": year,
        "round_cutoff": k_eff,
        "gp_name_cutoff": gp_name_cutoff,
        "gp_date_cutoff": gp_date_cutoff,
        "hamilton_rank": h_rank,
        "hamilton_points": h_points,
        "leader_points": leader_points,
        "points_behind": points_behind,
        "pct_of_leader": pct_of_leader,
        "wins_to_date": wins,
        "podiums_to_date": podiums,
        "poles_to_date": poles,
        "dnf_to_date": dnf,
        "races_started": started,
        "races_scored_pct": races_scored_pct,
        "race_scored_pct_main": race_scored_pct_main,
        "weekend_scored_pct": weekend_scored_pct,
        "zero_point_weekends_to_date": zero_point_weekends,
        "constructor_id": constructor_id_at_k,
        "teammate_points_to_date": round(teammate_points, 1),
        "teammate_gap": (round(h_points - teammate_points, 1) if h_points is not None else None),
    }


# ---------- Construction du snapshot ----------
def build_snapshot(
    season_current: int | None, round_cutoff: int | None, out_csv: str
) -> pd.DataFrame:
    erg = Ergast(result_type="pandas", auto_cast=True)
    season, k = get_current_season_and_round(erg, season_current, round_cutoff)

    seasons = list(range(START_SEASON, season + 1))
    rows: List[Dict[str, any]] = []

    for y in seasons:
        race_df, quali_df = prefetch_season_dfs(erg, y)  # 2 appels
        row = cumulate_to_round_k(erg, y, k, race_df, quali_df)  # +1 appel (standings)
        rows.append(row)
        time.sleep(0.15)  # petite pause anti-429

    df = pd.DataFrame(rows)
    cols = [
        "year",
        "round_cutoff",
        "gp_name_cutoff",
        "gp_date_cutoff",
        "hamilton_rank",
        "hamilton_points",
        "leader_points",
        "points_behind",
        "pct_of_leader",
        "wins_to_date",
        "podiums_to_date",
        "poles_to_date",
        "dnf_to_date",
        "races_started",
        "races_scored_pct",
        "race_scored_pct_main",
        "weekend_scored_pct",
        "zero_point_weekends_to_date",
        "constructor_id",
        "teammate_points_to_date",
        "teammate_gap",
    ]
    df = df[cols]
    if out_csv:
        df.to_csv(out_csv, index=False)
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Snapshot mi-saison de Lewis Hamilton (2007→année courante) sur K GP."
    )
    parser.add_argument(
        "--season",
        type=int,
        default=None,
        help="Saison courante à évaluer (défaut = année système).",
    )
    parser.add_argument(
        "--round", type=int, default=None, help="Cutoff K (nb de GP) ; défaut = dernier round clos."
    )
    parser.add_argument(
        "--out",
        "-o",
        nargs="?",
        const="hamilton_midseason_snapshot.csv",
        default="hamilton_midseason_snapshot.csv",
        help="CSV de sortie (défaut: hamilton_midseason_snapshot.csv).",
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=DEFAULT_CACHE,
        help="Dossier cache FastF1 (défaut: .fastf1cache).",
    )

    args = parser.parse_args()
    enable_cache(args.cache)

    df = build_snapshot(args.season, args.round, args.out)
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
