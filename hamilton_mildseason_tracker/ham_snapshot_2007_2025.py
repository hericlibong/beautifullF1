# -*- coding: utf-8 -*-
"""
Snapshot multi-saisons Hamilton (2007–2025) — fiable & simple.
Principe : Hybride = dump saison rapide + patch round-by-round uniquement pour les rounds manquants.
Corrige les pôles ET les podiums, sans double écriture ni surcodage.
"""

from __future__ import annotations
import argparse
import os
import time
import pandas as pd
import fastf1
from fastf1.ergast import Ergast
from fastf1.req import RateLimitExceededError
from fastf1.ergast.interface import ErgastInvalidRequestError

LH_ID = "hamilton"
START_SEASON = 2007
END_SEASON = 2025
DEFAULT_CACHE = ".fastf1cache"

COLS = [
    "year","round_cutoff","gp_name_cutoff","gp_date_cutoff",
    "hamilton_rank","hamilton_points","leader_points","points_behind","pct_of_leader",
    "pct_to_leader_label","status_label","wins_to_date","podiums_to_date","poles_to_date","dnf_to_date",
    "races_started","races_scored_pct","race_scored_pct_main","weekend_scored_pct",
    "zero_point_weekends_to_date","team","teammate_points_to_date","teammate_gap"
]

TEAM_LABELS = {"mclaren": "McLaren", "mercedes": "Mercedes", "ferrari": "Ferrari"}


# -------------------------------------------------------------
def enable_cache(path: str = DEFAULT_CACHE) -> None:
    try:
        fastf1.Cache.enable_cache(path)
    except Exception:
        pass


def api_get(fn, **kwargs):
    """Appels Ergast avec retry light (évite 429)."""
    for attempt in range(3):
        try:
            return fn(**kwargs)
        except (RateLimitExceededError, ErgastInvalidRequestError) as e:
            msg = str(e)
            if "Too Many Requests" in msg or isinstance(e, RateLimitExceededError):
                print("⏸️  API limit atteinte, pause 60s…")
                time.sleep(60)
                continue
            print(f"Erreur Ergast: {e} — {kwargs}")
            return pd.DataFrame()
        except Exception as e:
            print(f"⚠️ tentative {attempt+1}/3 échouée ({e}); pause 2s")
            time.sleep(2)
    return pd.DataFrame()


# -------------------------------------------------------------
def season_total_rounds(year: int) -> int:
    sched = fastf1.get_event_schedule(year)
    r = sched.loc[sched["RoundNumber"] > 0, "RoundNumber"]
    return int(r.max()) if not r.empty else 0


def get_event_name_date(year: int, rnd: int) -> tuple[str, str]:
    """Robuste à EventDateUtc manquant (versions FastF1 différentes)."""
    sched = fastf1.get_event_schedule(year)
    ev = sched.get_event_by_round(rnd)
    name = getattr(ev, "EventName", f"Round {rnd}")

    date = None
    if hasattr(ev, "EventDateUtc") and getattr(ev, "EventDateUtc") is not None:
        date = ev.EventDateUtc
    elif hasattr(ev, "EventDate") and getattr(ev, "EventDate") is not None:
        date = ev.EventDate
    elif hasattr(ev, "Session1Date") and getattr(ev, "Session1Date") is not None:
        date = ev.Session1Date

    date_str = ""
    if date is not None:
        try:
            date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
        except Exception:
            date_str = str(date)

    return name, date_str


def get_cutoff_k_for_2025(erg: Ergast) -> int:
    st = api_get(erg.get_driver_standings, season=END_SEASON, round="last")
    desc = getattr(st, "description", None)
    return int(desc.iloc[-1]["round"]) if desc is not None and not desc.empty else 1


# -------------------------------------------------------------
def assemble_df(mr) -> pd.DataFrame:
    """Convertit une réponse Ergast (multi/single) en DataFrame unique avec colonne 'round'."""
    # MultiResponse
    if hasattr(mr, "content") and isinstance(mr.content, list):
        desc = getattr(mr, "description", None)
        if desc is None or getattr(desc, "empty", True):
            rounds = list(range(1, len(mr.content) + 1))
        else:
            try:
                rs = desc.get("round")
                if rs is None or getattr(rs, "empty", True):
                    rounds = list(range(1, len(mr.content) + 1))
                else:
                    rounds = pd.to_numeric(rs, errors="coerce").tolist()
            except Exception:
                rounds = list(range(1, len(mr.content) + 1))
        parts = []
        for rnum, df_part in zip(rounds, mr.content):
            if df_part is None or getattr(df_part, "empty", True):
                continue
            dfp = df_part.copy()
            dfp["round"] = rnum
            parts.append(dfp)
        df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    # DataFrame simple
    elif isinstance(mr, pd.DataFrame):
        df = mr.copy()
        if not df.empty and "round" not in df.columns:
            df["round"] = pd.NA
    else:
        df = pd.DataFrame()

    # Normalisation minimale
    if df.empty:
        return pd.DataFrame(columns=["round","position","points","status","driverId","constructorId"])

    for col in ["round","position","points","status","driverId","constructorId"]:
        if col not in df.columns:
            df[col] = pd.NA

    df["round"] = pd.to_numeric(df["round"], errors="coerce")
    df["position"] = pd.to_numeric(df["position"], errors="coerce")
    df["points"] = pd.to_numeric(df["points"], errors="coerce")
    df["status"] = df["status"].astype(str)
    df["driverId"] = df["driverId"].astype(str)
    df["constructorId"] = df["constructorId"].astype(str)
    return df


# -------------------------------------------------------------
def rounds_list(year: int, k_eff: int) -> list[int]:
    sched = fastf1.get_event_schedule(year)
    rounds = (
        sched.loc[sched["RoundNumber"] > 0, "RoundNumber"]
        .dropna().astype(int).tolist()
    )
    return [r for r in rounds if r <= int(k_eff)]


def race_df_hybrid(erg: Ergast, year: int, k_eff: int) -> pd.DataFrame:
    """
    Course hybride = dump saison + patch rounds manquants (fiable, peu d'appels).
    Renvoie un DF complet et propre pour 1..K.
    """
    base = assemble_df(api_get(erg.get_race_results, season=year, limit=2000))
    base = base[base["round"] <= k_eff].copy()
    have = set(base["round"].dropna().astype(int).tolist())
    need = [r for r in rounds_list(year, k_eff) if r not in have]

    parts = [base]
    for rnd in need:
        rr = api_get(erg.get_race_results, season=year, round=int(rnd), limit=2000)
        rdf = rr.content[0] if hasattr(rr, "content") and rr.content else (rr if isinstance(rr, pd.DataFrame) else pd.DataFrame())
        if rdf is None or rdf.empty:
            continue
        rdf = assemble_df(rdf)
        rdf = rdf[rdf["round"] == rnd]
        parts.append(rdf)
        time.sleep(0.05)  # anti-429 soft

    if parts:
        out = pd.concat(parts, ignore_index=True)
        # Nettoyage et bornage 1..K
        out["round"] = pd.to_numeric(out["round"], errors="coerce")
        out["position"] = pd.to_numeric(out["position"], errors="coerce")
        out["points"] = pd.to_numeric(out["points"], errors="coerce")
        out = out[(out["round"] >= 1) & (out["round"] <= k_eff)]
        return out
    return pd.DataFrame(columns=base.columns)


def count_poles_up_to_k_final(erg: Ergast, year: int, k_eff: int) -> int:
    """
    Pôles hybride final = dump saison + patch rounds manquants (fiable).
    """
    # base rapide
    qr = api_get(erg.get_qualifying_results, season=year, limit=2000)
    qdf = assemble_df(qr)
    qdf = qdf[qdf["round"] <= k_eff].copy()
    poles = 0
    ok_rounds = set()
    if not qdf.empty:
        mask = (qdf["driverId"] == LH_ID) & (qdf["position"] == 1)
        poles += int(mask.sum())
        ok_rounds = set(qdf["round"].dropna().astype(int).unique().tolist())

    # patch rounds manquants
    need = [r for r in rounds_list(year, k_eff) if r not in ok_rounds]
    for rnd in need:
        q = api_get(erg.get_qualifying_results, season=year, round=int(rnd), limit=2000)
        qdf_r = q.content[0] if hasattr(q, "content") and q.content else (q if isinstance(q, pd.DataFrame) else pd.DataFrame())
        if qdf_r is None or qdf_r.empty:
            continue
        qdf_r = assemble_df(qdf_r)
        row = qdf_r[(qdf_r["driverId"] == LH_ID) & (qdf_r["position"] == 1)]
        if not row.empty:
            poles += 1
        time.sleep(0.05)
    return int(poles)


def count_podiums_up_to_k_strict(erg: Ergast, year: int, k_eff: int) -> int:
    """
    Compte FIABLE des podiums : interroge chaque round 1..K.
    Un podium est compté si la position finale officielle ∈ {1,2,3}.
    """
    podiums = 0
    for rnd in range(1, int(k_eff) + 1):
        resp = api_get(erg.get_race_results, season=year, round=rnd, limit=2000)
        rr_df = resp.content[0] if hasattr(resp, "content") and resp.content else (resp if isinstance(resp, pd.DataFrame) else pd.DataFrame())
        if rr_df is None or rr_df.empty or "driverId" not in rr_df.columns:
            continue

        row = rr_df[rr_df["driverId"] == LH_ID]
        if row.empty:
            continue

        pos = pd.to_numeric(row.iloc[0].get("position"), errors="coerce")
        if pd.notna(pos) and int(pos) in (1, 2, 3):
            podiums += 1

        # petite pause anti-429 ; les réponses sont cachées en local, donc c'est souple après la 1re passe
        time.sleep(0.05)

    return int(podiums)




# -------------------------------------------------------------
def compute_row_for_season(erg: Ergast, year: int, k_global: int) -> dict:
    total_rounds = season_total_rounds(year)
    k_eff = min(k_global, total_rounds if total_rounds else k_global)

    # Standings (points / rang / wins / leader)
    st = api_get(erg.get_driver_standings, season=year, round=k_eff, limit=2000)
    st_df = st.content[0] if hasattr(st, "content") and st.content else (st if isinstance(st, pd.DataFrame) else pd.DataFrame())
    if st_df.empty or "driverId" not in st_df.columns:
        print(f"⚠️ Standings manquants {year} R{k_eff}")
        return {}

    lh_row = st_df[st_df["driverId"] == LH_ID]
    if lh_row.empty:
        return {}

    hamilton_rank = int(pd.to_numeric(lh_row.iloc[0]["position"], errors="coerce"))
    hamilton_points = float(pd.to_numeric(lh_row.iloc[0]["points"], errors="coerce"))
    leader_points = float(pd.to_numeric(st_df.iloc[0]["points"], errors="coerce"))
    wins = int(pd.to_numeric(lh_row.iloc[0].get("wins", 0), errors="coerce"))
    points_behind = round(leader_points - hamilton_points, 2)
    pct_of_leader = round((hamilton_points / leader_points) * 100 if leader_points > 0 else 0.0, 1)
    pct_label = f"{pct_of_leader:.1f}% (1er)" if points_behind == 0 else f"{pct_of_leader:.1f}%"
    status_label = "Leader" if points_behind == 0 else f"Gap: {int(points_behind)} pts"

    # Course HYBRIDE fiable 1..K
    rr = race_df_hybrid(erg, year, k_eff)

    # Podiums (classement final ∈ {1,2,3})
    # podiums = 0
    # if not rr.empty:
    #     lh = rr[(rr["driverId"] == LH_ID)]
    #     podiums = int(lh["position"].isin([1, 2, 3]).sum())
    podiums = count_podiums_up_to_k_strict(erg, year, k_eff)

    # DNF / starts / points
    race_k = rr.copy()
    lh_race = race_k[race_k["driverId"] == LH_ID].copy()
    started = len(lh_race)
    dnf = 0
    if not lh_race.empty:
        finished = lh_race["status"].astype(str).str.contains("Finished|Lap", na=False)
        dnf = int((~finished).sum())
    pts = pd.to_numeric(lh_race["points"], errors="coerce").fillna(0)
    zero_points = int((pts == 0).sum())
    races_scored_pct = round((started - zero_points) / started, 2) if started else 0.0
    avg_pos = pd.to_numeric(lh_race["position"], errors="coerce").mean()
    weekend_scored_pct = round(avg_pos, 2) if not pd.isna(avg_pos) else 0.0

    # Team & teammate (depuis rr consolidé)
    team = None
    teammate_pts = 0.0
    if not lh_race.empty:
        last_cid = str(lh_race.dropna(subset=["constructorId"]).iloc[-1]["constructorId"]).lower()
        team = TEAM_LABELS.get(last_cid, last_cid.title() if last_cid else None)
        for _, row in lh_race.iterrows():
            mates = race_k[(race_k["round"] == row["round"]) &
                           (race_k["constructorId"] == row["constructorId"]) &
                           (race_k["driverId"] != LH_ID)]
            teammate_pts += pd.to_numeric(mates["points"], errors="coerce").fillna(0).sum()
    teammate_pts = float(teammate_pts)
    teammate_gap = round(hamilton_points - teammate_pts, 1)

    # Pôles HYBRIDE fiable
    poles = count_poles_up_to_k_final(erg, year, k_eff)

    gp_name, gp_date = get_event_name_date(year, k_eff)

    return dict(
        year=year, round_cutoff=k_eff, gp_name_cutoff=gp_name, gp_date_cutoff=gp_date,
        hamilton_rank=hamilton_rank, hamilton_points=hamilton_points, leader_points=leader_points,
        points_behind=points_behind, pct_of_leader=pct_of_leader,
        pct_to_leader_label=pct_label, status_label=status_label, wins_to_date=wins,
        podiums_to_date=podiums, poles_to_date=poles, dnf_to_date=dnf, races_started=started,
        races_scored_pct=races_scored_pct, race_scored_pct_main=races_scored_pct,
        weekend_scored_pct=weekend_scored_pct, zero_point_weekends_to_date=zero_points,
        team=team, teammate_points_to_date=round(teammate_pts, 1), teammate_gap=teammate_gap
    )


# -------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", "-o", default="hamilton_2007_2025_snapshot.csv")
    args = parser.parse_args()

    enable_cache(DEFAULT_CACHE)
    erg = Ergast(result_type="pandas", auto_cast=True)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    args.out = os.path.join(script_dir, os.path.basename(args.out))

    k_global = get_cutoff_k_for_2025(erg)

    rows = []
    for year in range(START_SEASON, END_SEASON + 1):
        print(f"⏳ Saison {year}")
        row = compute_row_for_season(erg, year, k_global)
        if row:
            rows.append(row)
        # petite pause pour rester en dessous des limites (mais on fait très peu d’appels)
        time.sleep(0.15)

    df = pd.DataFrame(rows)
    df = df[COLS]
    df.to_csv(args.out, index=False)
    print("\n✅ Snapshot terminé.")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
