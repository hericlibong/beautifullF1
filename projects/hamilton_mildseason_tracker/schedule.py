from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd

try:
    import fastf1  # type: ignore
except Exception as exc:  # pragma: no cover
    fastf1 = None
    logging.warning("FastF1 non disponible (%s) – calendrier via fallback Jolpica.", exc)

from .ergast_jolpica import ErgastClient


@dataclass
class CutoffInfo:
    round: int
    gp_name: str
    gp_date_iso: str


def _compute_cutoff_from_df(df: pd.DataFrame) -> CutoffInfo:
    df = df.sort_values("EventDate").reset_index(drop=True)
    start = pd.Timestamp(year=int(str(df["EventDate"].dt.year.iloc[0])), month=6, day=15)
    end = pd.Timestamp(year=int(str(df["EventDate"].dt.year.iloc[0])), month=9, day=15)

    gaps: List[Tuple[int, pd.Timestamp, pd.Timedelta]] = []
    for i in range(len(df) - 1):
        date_i = pd.to_datetime(df.loc[i, "EventDate"])  # type: ignore[arg-type]
        date_j = pd.to_datetime(df.loc[i + 1, "EventDate"])  # type: ignore[arg-type]
        if not (start <= date_i <= end):
            continue
        gaps.append((i, date_i, date_j - date_i))

    if not gaps:
        # fallback: dernier GP ≤ 10 août
        dates = pd.to_datetime(df["EventDate"])  # type: ignore[arg-type]
        y0 = int(str(dates.dt.year.iloc[0]))
        mask = dates <= pd.Timestamp(year=y0, month=8, day=10)
        idx = mask[mask].index.max() if mask.any() else len(df) // 2
        return CutoffInfo(
            round=int(df.loc[idx, "RoundNumber"]),
            gp_name=str(df.loc[idx, "EventName"]),
            gp_date_iso=pd.to_datetime(df.loc[idx, "EventDate"]).date().isoformat(),
        )

    gaps.sort(key=lambda t: t[2], reverse=True)
    idx, _, gap = gaps[0]
    return CutoffInfo(
        round=int(df.loc[idx, "RoundNumber"]),
        gp_name=str(df.loc[idx, "EventName"]),
        gp_date_iso=pd.to_datetime(df.loc[idx, "EventDate"]).date().isoformat(),
    )


def find_round_cutoff(year: int, client: ErgastClient | None = None) -> CutoffInfo:
    """Primary: FastF1 schedule; Fallback: Jolpica calendar (Ergast /{year}.json)."""
    # --- Primary: FastF1 ---
    if fastf1 is not None:
        try:
            schedule = fastf1.get_event_schedule(year)
            df = (
                schedule[["RoundNumber", "EventName", "EventDate"]]
                .dropna()
                .sort_values("EventDate")
                .reset_index(drop=True)
            )
            if not df.empty:
                cutoff = _compute_cutoff_from_df(df)
                logging.info(
                    "Cutoff %s via FastF1: round=%s, GP=%s, date=%s",
                    year,
                    cutoff.round,
                    cutoff.gp_name,
                    cutoff.gp_date_iso,
                )
                return cutoff
        except Exception as exc:  # pragma: no cover
            logging.warning("FastF1 schedule KO (%s) – fallback Jolpica calendar.", exc)

    # --- Fallback: Jolpica calendar (Ergast style) ---
    client = client or ErgastClient()
    payload = client.get_season_calendar(year, limit=1000)
    mr = payload.get("MRData", {})
    race_table = mr.get("RaceTable", {})
    races = race_table.get("Races", [])
    if not races:
        raise RuntimeError(f"Calendrier vide pour {year}")

    df_rows = []
    for r in races:
        # Ergast fields: round, raceName, date
        round_ = int(r.get("round"))
        name = str(r.get("raceName"))
        date_iso = str(r.get("date"))
        df_rows.append(
            {"RoundNumber": round_, "EventName": name, "EventDate": pd.to_datetime(date_iso)}
        )

    df = pd.DataFrame(df_rows)
    cutoff = _compute_cutoff_from_df(df)
    logging.info(
        "Cutoff %s via Jolpica calendar: round=%s, GP=%s, date=%s",
        year,
        cutoff.round,
        cutoff.gp_name,
        cutoff.gp_date_iso,
    )
    return cutoff
