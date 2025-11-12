# hamilton_mildseason_tracker/ham_quali_duels_builder.py
# Sortie : hamilton_mildseason_tracker/hamilton_quali_duels_2007_2025_until_R20.csv

import os
import time
from typing import Optional, Tuple

import fastf1
import pandas as pd
from fastf1.ergast import Ergast
from fastf1.ergast.interface import ErgastInvalidRequestError

CURRENT_GPS_COMPLETED = 21  # dernier GP compté = Mexico (R20)
CSV_NAME = "hamilton_quali_duels_2007_2025_until_R21.csv"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "outputs", CSV_NAME)

# Relances anti-429
MAX_RETRIES = 3
RETRY_SLEEP_S = 0.6

# --- Nouveau : mapping image par teammate_driverId ---
TM_IMG_BY_ID = {
    "kovalainen": "https://s.hs-data.com/gfx/person/cropped/400x400/37599.png?",
    "bottas": "https://image-service.zaonce.net/eyJidWNrZXQiOiJmcm9udGllci1jbXMiLCJrZXkiOiJmMW1hbmFnZXIvMjAyNC9kcml2ZXJzL2hlYWRzaG90cy9mMS9ib3QucG5nIiwiZWRpdHMiOnsicmVzaXplIjp7IndpZHRoIjo3MH19fQ==",
    "alonso": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/F/FERALO01_Fernando_Alonso/feralo01.png.transform/1col/image.png",
    "leclerc": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/C/CHALEC01_Charles_Leclerc/chalec01.png.transform/1col/image.png",
    "russell": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/G/GEORUS01_George_Russell/georus01.png.transform/1col/image.png",
    "button": "https://media.formula1.com/image/upload/c_fill,w_192,h_192,g_center/q_auto/v1740000000/fom-website/2025/Miscellaneous/GENERAL%20CROP%20-%202025-10-30T102533.857.webp",
    "rosberg": "https://www.formulaonehistory.com/wp-content/uploads/2024/02/Nico-Rosberg-F1-2016.webp",
}

TEAMMATE_BY_YEAR = {
    2007: ("McLaren", "Fernando Alonso", "alonso"),
    2008: ("McLaren", "Heikki Kovalainen", "kovalainen"),
    2009: ("McLaren", "Heikki Kovalainen", "kovalainen"),
    2010: ("McLaren", "Jenson Button", "button"),
    2011: ("McLaren", "Jenson Button", "button"),
    2012: ("McLaren", "Jenson Button", "button"),
    2013: ("Mercedes", "Nico Rosberg", "rosberg"),
    2014: ("Mercedes", "Nico Rosberg", "rosberg"),
    2015: ("Mercedes", "Nico Rosberg", "rosberg"),
    2016: ("Mercedes", "Nico Rosberg", "rosberg"),
    2017: ("Mercedes", "Valtteri Bottas", "bottas"),
    2018: ("Mercedes", "Valtteri Bottas", "bottas"),
    2019: ("Mercedes", "Valtteri Bottas", "bottas"),
    2020: ("Mercedes", "Valtteri Bottas", "bottas"),
    2021: ("Mercedes", "Valtteri Bottas", "bottas"),
    2022: ("Mercedes", "George Russell", "russell"),
    2023: ("Mercedes", "George Russell", "russell"),
    2024: ("Mercedes", "George Russell", "russell"),
    2025: ("Ferrari", "Charles Leclerc", "leclerc"),
}
HAM_ID = "hamilton"

# fastf1.Cache.enable_cache("~/.cache/fastf1")
erg = Ergast(result_type="pandas", auto_cast=True, limit=1000)


def _cutoff_round_and_event(year: int, target_round: int) -> Tuple[int, str]:
    """(r_eff, event_name) avec r_eff=min(target_round, nb rounds de la saison)."""
    sched = fastf1.get_event_schedule(year)
    if "RoundNumber" in sched.columns:
        total = int(sched["RoundNumber"].max())
        r_eff = min(target_round, total)
        row = sched.loc[sched["RoundNumber"] == r_eff].iloc[0]
        event_name = str(row.get("EventName", f"Round {r_eff}"))
    else:
        total = len(sched)
        r_eff = min(target_round, total)
        row = sched.iloc[r_eff - 1]
        event_name = str(row.get("EventName", f"Round {r_eff}"))
    return r_eff, event_name


def _two_positions_for_round(
    year: int, rnd: int, a_id: str, b_id: str
) -> Tuple[Optional[int], Optional[int]]:
    """Retourne (pos_a, pos_b) (1=pole) avec 1 seul appel réseau + relances anti-429."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = erg.get_qualifying_results(season=year, round=rnd)
            df = resp.content[0] if isinstance(resp.content, list) else resp.content
            if not isinstance(df, pd.DataFrame) or df.empty:
                return None, None

            if "driverId" not in df.columns and "Driver" in df.columns:
                df = df.copy()
                df["driverId"] = df["Driver"].apply(
                    lambda d: (d or {}).get("driverId", "") if isinstance(d, dict) else ""
                )
            if "driverId" not in df.columns:
                return None, None

            pos_col = (
                "position"
                if "position" in df.columns
                else ("Position" if "Position" in df.columns else None)
            )
            if pos_col is None and "positionText" in df.columns:
                df = df.copy()
                df["position"] = pd.to_numeric(df["positionText"], errors="coerce")
                pos_col = "position"
            if pos_col is None:
                return None, None

            df = df[["driverId", pos_col]].copy()
            df.columns = ["driverId", "qpos"]
            df["driverId"] = df["driverId"].str.lower()
            df["qpos"] = pd.to_numeric(df["qpos"], errors="coerce").astype("Int64")

            a = df.loc[df["driverId"] == a_id.lower(), "qpos"]
            b = df.loc[df["driverId"] == b_id.lower(), "qpos"]
            pos_a = int(a.iloc[0]) if not a.empty and pd.notna(a.iloc[0]) else None
            pos_b = int(b.iloc[0]) if not b.empty and pd.notna(b.iloc[0]) else None
            return pos_a, pos_b

        except ErgastInvalidRequestError:
            if attempt == MAX_RETRIES:
                return None, None
            time.sleep(RETRY_SLEEP_S * attempt)
        except Exception:
            if attempt == MAX_RETRIES:
                return None, None
            time.sleep(RETRY_SLEEP_S * attempt)


def build_quali_duels():
    rows = []

    for year in range(2007, 2026):
        meta = TEAMMATE_BY_YEAR.get(year)
        if not meta:
            continue
        team, teammate_name, tm_id = meta

        r_eff, cutoff_event = _cutoff_round_and_event(year, CURRENT_GPS_COMPLETED)

        ham_wins = tm_wins = ties = 0

        for rnd in range(1, r_eff + 1):
            ph, pt = _two_positions_for_round(year, rnd, HAM_ID, tm_id)

            if ph is None and pt is None:
                ties += 1
            elif ph is None:
                tm_wins += 1
            elif pt is None:
                ham_wins += 1
            elif ph == pt:
                ties += 1
            elif ph < pt:
                ham_wins += 1
            else:
                tm_wins += 1

        rounds_compared = r_eff
        ham_diff = ham_wins - tm_wins  # + = Hamilton devant, - = coéquipier devant
        tm_img = TM_IMG_BY_ID.get(tm_id, "")  # --- Nouveau : URL image du coéquipier

        rows.append(
            {
                "year": year,
                "cutoff_round": r_eff,
                "cutoff_event": cutoff_event,
                "rounds_compared": rounds_compared,
                "ham_quali_wins": ham_wins,
                "teammate_quali_wins": tm_wins,
                "ties": ties,
                "ham_quali_diff": ham_diff,  # (après ties)
                "teammate_driverId": tm_id,
                "team": team,
                "teammate_name": teammate_name,
                "teammate_img": tm_img,  # --- Nouvelle colonne
            }
        )

    df = pd.DataFrame(rows)
    # Ordre des colonnes (ham_quali_diff reste juste après ties)
    df = df[
        [
            "year",
            "cutoff_round",
            "cutoff_event",
            "rounds_compared",
            "ham_quali_wins",
            "teammate_quali_wins",
            "ties",
            "ham_quali_diff",
            "teammate_driverId",
            "team",
            "teammate_name",
            "teammate_img",
        ]
    ]
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Résumé exporté: {OUTPUT_CSV} ({len(df)} saisons)")
    print(df.head(8))


if __name__ == "__main__":
    build_quali_duels()
