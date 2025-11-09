"""
Who can still win the WDC? — Saison 2025, Round 14
- Règlement 2025 : pas de point pour le meilleur tour en course.
- Barème retenu :
  * GP "conventional"   = 25 pts (course gagnée)
  * GP "sprint" weekend = 8 pts (sprint win) + 25 pts (course) = 33 pts

Corrections :
- pct_needed_of_remaining_to_lead = 0.0% pour le leader (ou tout pilote à égalité de points avec le leader)
- risk_zone plus strict basé sur le % de points restants nécessaires
- ajout de points_needed_to_lead (valeur absolue)
"""

from __future__ import annotations

from typing import Tuple

import fastf1
import pandas as pd
from fastf1.ergast import Ergast

# --- CONFIG ---
SEASON = 2025
ROUND = 14  # dernier round couru

# Barème 2025 (sans fastest lap)
POINTS_FOR_CONVENTIONAL = 25
POINTS_FOR_SPRINT_WEEKEND = 8 + 25  # sprint win + race win


def get_remaining_events(season: int, after_round: int) -> pd.DataFrame:
    """Events restants (> after_round) + booléen 'is_sprint' robuste."""
    schedule = fastf1.get_event_schedule(season)  # backend par défaut (F1 TV)
    remain = schedule.loc[schedule["RoundNumber"] > after_round].copy()

    # 1) via EventFormat
    fmt = remain.get("EventFormat")
    contains_sprint = (
        fmt.notna() & fmt.str.contains("sprint", case=False, na=False)
        if fmt is not None
        else pd.Series(False, index=remain.index)
    )

    # 2) fallback via noms de sessions (Session1..Session5)
    session_cols = [
        c
        for c in remain.columns
        if c.startswith("Session") and not c.endswith("Date") and not c.endswith("DateUtc")
    ]
    any_session_is_sprint = pd.Series(False, index=remain.index)
    for c in session_cols:
        any_session_is_sprint |= remain[c].fillna("").str.contains("Sprint", case=False, na=False)

    remain["is_sprint"] = contains_sprint | any_session_is_sprint

    keep = [
        "RoundNumber",
        "Country",
        "Location",
        "EventName",
        "EventFormat",
        "is_sprint",
    ] + session_cols
    cols = [c for c in keep if c in remain.columns]
    return remain.loc[:, cols]


def compute_points_pool(remain: pd.DataFrame) -> Tuple[int, int, int]:
    """Total de points qu'un pilote peut encore marquer (= points pool restant)."""
    sprint_events = int(remain["is_sprint"].sum())
    conventional_events = int((~remain["is_sprint"]).sum())
    total_points = (
        sprint_events * POINTS_FOR_SPRINT_WEEKEND + conventional_events * POINTS_FOR_CONVENTIONAL
    )
    return total_points, sprint_events, conventional_events


def get_driver_standings_df(season: int, round_num: int) -> pd.DataFrame:
    """Standings pilotes via Ergast, typés et triés par position."""
    ergast = Ergast()
    res = ergast.get_driver_standings(season=season, round=round_num)
    df = res.content[0].copy()  # DataFrame
    df["points"] = pd.to_numeric(df["points"])
    df["position"] = pd.to_numeric(df["position"])
    df.sort_values("position", inplace=True, ignore_index=True)
    return df


def assign_risk_zone(can_still: bool, pct_needed: float | None) -> str:
    """
    Zones plus strictes basées sur le % des points restants qu'il faut prendre pour
    au moins passer devant le leader (en supposant leader = 0).
    """
    if not can_still:
        return "Eliminated"
    if pct_needed is None:
        return "Unknown"
    if pct_needed <= 25:
        return "Safe"
    if pct_needed <= 50:
        return "Warning"
    if pct_needed <= 70:
        return "Danger"
    if pct_needed <= 90:
        return "Critical"
    # > 90% mais encore mathématiquement possible
    return "LastChance"


def main() -> None:
    # 1) Events restants
    remain = get_remaining_events(SEASON, ROUND)
    fmt_uniques = (
        remain["EventFormat"].dropna().unique().tolist() if "EventFormat" in remain else []
    )
    print(f"[debug] Remaining events: {len(remain)} | EventFormat uniques: {fmt_uniques}")
    print(remain[["RoundNumber", "EventName", "EventFormat", "is_sprint"]].to_string(index=False))

    max_points_remaining, sprint_count, conv_count = compute_points_pool(remain)
    print(
        f"[debug] remaining={len(remain)} (sprint={sprint_count}, conventional={conv_count}) "
        f"→ max_points_remaining={max_points_remaining}"
    )

    # 2) Standings
    standings = get_driver_standings_df(SEASON, ROUND)
    leader_points = float(standings.iloc[0]["points"])

    # 3) Table enrichie
    rows = []
    for _, d in standings.iterrows():
        current = float(d["points"])
        # points à aller chercher pour (au moins) passer devant le leader
        points_needed = max(0.0, leader_points - current + 1)

        maxp = current + max_points_remaining
        can = maxp >= leader_points

        # % nécessaires et % de marge si finish parfait
        if max_points_remaining > 0:
            # Forcer 0.0% si à égalité avec le leader (ou leader lui-même)
            pct_needed = (
                0.0
                if current >= leader_points
                else round(points_needed / max_points_remaining * 100, 1)
            )
            headroom_pct = max(0.0, round((maxp - leader_points) / max_points_remaining * 100, 1))
        else:
            pct_needed = 0.0
            headroom_pct = 0.0

        rows.append(
            {
                "rank": int(d["position"]),
                "driver": f"{d['givenName']} {d['familyName']}",
                "abbreviation": d.get("code") or "",
                "points": current,
                "max_points": int(maxp),
                "delta_with_leader": round(leader_points - current, 1),
                "points_needed_to_lead": round(points_needed, 1),
                "can_still_win": can,
                "pct_needed_of_remaining_to_lead": pct_needed,
                "headroom_pct_if_perfect_finish": headroom_pct,
                "risk_zone": assign_risk_zone(can, pct_needed),
            }
        )

    out_df = pd.DataFrame(rows)

    # 4) Export
    out_path = f"f1_{SEASON}_wdc_projection_round{ROUND}.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\n✅ Export CSV: {out_path}")
    print(out_df.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
