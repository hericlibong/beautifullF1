# hamilton_mildseason_tracker/ham_quali_duels_builder.py
# Génère :
#  - hamilton_quali_duels_2007_2025_summary.csv
#  - hamilton_quali_duels_2007_2025_rounds.csv
#
# Méthode :
#  - Calendrier via fastf1.get_event_schedule(year) pour déterminer le cutoff effectif
#  - Résultats de qualifications round-par-round via Ergast (fastf1.ergast)
#  - "Best quali time" = min(Q1, Q2, Q3) lorsqu'elles existent
#  - Duel Hamilton vs coéquipier principal (mapping ci-dessous)
#
# Dépendances :
#  pip install fastf1 pandas numpy

import fastf1
from fastf1.ergast import Ergast
import pandas as pd
import numpy as np
from typing import Optional, Tuple

# --------------------------
# Paramètres généraux
# --------------------------
CUTOFF_ROUND = 18  # on aligne la comparaison sur R18 (ou dernier GP si saison < 18)
SUMMARY_CSV = "hamilton_quali_duels_2007_2025_summary.csv"
DETAIL_CSV  = "hamilton_quali_duels_2007_2025_rounds.csv"

# Coéquipier "principal" par saison (id Ergast)
TEAMMATE_BY_YEAR = {
    2007: "alonso",
    2008: "kovalainen",
    2009: "kovalainen",
    2010: "button",
    2011: "button",
    2012: "button",
    2013: "rosberg",
    2014: "rosberg",
    2015: "rosberg",
    2016: "rosberg",
    2017: "bottas",
    2018: "bottas",
    2019: "bottas",
    2020: "bottas",
    2021: "bottas",
    2022: "russell",
    2023: "russell",
    2024: "russell",
    2025: "leclerc",
}
HAM_ID = "hamilton"

# fastf1.Cache.enable_cache("~/.cache/fastf1")  # décommente si tu veux un cache explicite
erg = Ergast(result_type="pandas", auto_cast=True, limit=1000)


# --------------------------
# Utils
# --------------------------
def _to_seconds(t: Optional[str]) -> Optional[float]:
    """Convertit 'm:ss.xxx' (ou 'ss.xxx') en secondes (float). Retourne None si vide/NaN."""
    if t is None or (isinstance(t, float) and np.isnan(t)):
        return None
    s = str(t).strip()
    if not s or s.lower() in {"none", "nan"}:
        return None
    # Certains endpoints peuvent renvoyer "\N" ou chaînes non chronométrées
    if s in {"\\N", "DNF", "DNS"}:
        return None
    try:
        if ":" in s:
            m, rest = s.split(":")
            return float(m) * 60.0 + float(rest)
        return float(s)
    except Exception:
        return None


def best_quali_time_for_driver(year: int, rnd: int, driver_id: str) -> Optional[float]:
    """Meilleur chrono de qualif (min(Q1,Q2,Q3)) pour 'driver_id' sur un round donné.
       Utilise Ergast: get_qualifying_results(season, round)."""
    resp = erg.get_qualifying_results(season=year, round=rnd)
    # ErgastMultiResponse -> prenons le premier DF
    df = resp.content[0] if isinstance(resp.content, list) else resp.content
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None

    # Normalisation driverId
    if "driverId" not in df.columns:
        if "Driver" in df.columns:
            df = df.copy()
            df["driverId"] = df["Driver"].apply(
                lambda d: (d or {}).get("driverId", "") if isinstance(d, dict) else ""
            )
        else:
            return None

    row = df.loc[df["driverId"].str.lower() == driver_id.lower()]
    if row.empty:
        return None

    # Colonnes Q1/Q2/Q3 -> secondes ; meilleur temps = min des segments disponibles
    q1 = _to_seconds(row.iloc[0].get("Q1"))
    q2 = _to_seconds(row.iloc[0].get("Q2"))
    q3 = _to_seconds(row.iloc[0].get("Q3"))

    # filtre None
    times = [t for t in (q1, q2, q3) if t is not None]
    if not times:
        return None
    return min(times)


def get_cutoff_for_year(year: int) -> Tuple[int, str, pd.Timestamp]:
    """Retourne (round_eff, EventName, EventDate) via le calendrier FastF1."""
    sched = fastf1.get_event_schedule(year)
    if "RoundNumber" in sched.columns:
        total = int(sched["RoundNumber"].max())
        r_eff = min(CUTOFF_ROUND, total)
        row = sched.loc[sched["RoundNumber"] == r_eff].iloc[0]
        return r_eff, str(row["EventName"]), pd.to_datetime(row["EventDate"])
    # fallback si colonnes différentes
    total = len(sched)
    r_eff = min(CUTOFF_ROUND, total)
    row = sched.iloc[r_eff - 1]
    return r_eff, str(row.get("EventName", "")), pd.to_datetime(row.get("EventDate", pd.NaT))


# --------------------------
# Calcul principal
# --------------------------
def build_quali_duels():
    detail_rows = []
    summary_rows = []

    for year in range(2007, 2026):
        if year not in TEAMMATE_BY_YEAR:
            continue
        teammate_id = TEAMMATE_BY_YEAR[year]
        r_eff, _, _ = get_cutoff_for_year(year)

        ham_better = 0
        tm_better = 0
        ties = 0
        deltas = []  # delta_s = teammate_time - ham_time (négatif => Hamilton plus rapide)

        for rnd in range(1, r_eff + 1):
            try:
                ham_t = best_quali_time_for_driver(year, rnd, HAM_ID)
                tm_t  = best_quali_time_for_driver(year, rnd, teammate_id)
            except Exception:
                ham_t, tm_t = None, None

            # on ne compte que si on a les deux temps
            if ham_t is None or tm_t is None:
                continue

            delta = tm_t - ham_t
            deltas.append(delta)

            if abs(delta) < 1e-6:
                winner = "TIE"
                ties += 1
            elif delta > 0:
                winner = "HAM"  # Hamilton plus rapide (temps plus petit)
                ham_better += 1
            else:
                winner = "TM"   # Teammate plus rapide
                tm_better += 1

            detail_rows.append({
                "year": year,
                "round": rnd,
                "ham_best_quali_s": ham_t,
                "tm_best_quali_s": tm_t,
                "delta_s": delta,          # tm - ham ; négatif => Hamilton devant
                "winner": winner,
                "ham_driverId": HAM_ID,
                "teammate_driverId": teammate_id
            })

        rounds_compared = ham_better + tm_better + ties
        avg_delta = float(np.mean(deltas)) if deltas else None
        med_delta = float(np.median(deltas)) if deltas else None

        summary_rows.append({
            "year": year,
            "rounds_compared": rounds_compared,
            "ham_quali_wins": ham_better,
            "teammate_quali_wins": tm_better,
            "ties": ties,
            # interprétation: delta < 0 => Hamilton devant (en moyenne négatif = Hamilton globalement plus rapide)
            "avg_delta_s": avg_delta,
            "median_delta_s": med_delta,
            "teammate_driverId": teammate_id
        })

    # Export
    detail_df = pd.DataFrame(detail_rows)
    summary_df = pd.DataFrame(summary_rows)

    detail_df.to_csv(DETAIL_CSV, index=False)
    summary_df.to_csv(SUMMARY_CSV, index=False)

    print(f"✅ Détail exporté: {DETAIL_CSV} ({len(detail_df)} lignes)")
    print(f"✅ Résumé exporté: {SUMMARY_CSV} ({len(summary_df)} saisons)")
    print(summary_df.head(8))


if __name__ == "__main__":
    build_quali_duels()
