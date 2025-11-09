"""
Beautifull F1 — GP History Builder (v1)

Objectif : produire automatiquement l’historique d’un Grand Prix (ici : Mexique)
à partir de FastF1/Ergast, avec les colonnes du gabarit Australie.

⚙️ Décisions v1
- Source unique pour l’historique : Ergast via FastF1 (`fastf1.ergast.Ergast`).
  -> couvre 1950+ et fournit podiums, grilles, constructeurs, etc. (docs Ergast/FF1)
- Images : option `--with-winner-image` (URL uniquement), via `enrichments/images.py`
- Motoriste : encore "NA" en v1 (module séparé à venir).
- Un CSV par GP dans `gp_history/data/gp_history/`.

📦 Dépendances : fastf1>=3.4, pandas>=1.5, requests (si --with-winner-image)

🧪 Usage CLI (exemples)
python -m gp_history.tools.gp_history_builder_mexique_v1 \
  --out gp_history/data/gp_history/mexican_grand_prix.csv \
  --with-winner-image

💡 Adaptation à d’autres GP : changer la logique de détection (schedule -> rounds) ou généraliser.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
import time
from typing import List, Dict

import pandas as pd
import fastf1
from fastf1.ergast import Ergast


# ============================================================
#  Répertoires (tout est contenu dans le dossier `gp_history/`)
# ============================================================
# Ce fichier est dans: gp_history/tools/gp_history_builder_mexique_v1.py
# On remonte à gp_history/ (parents[1])
BASE_DIR = Path(__file__).resolve().parents[1]            # -> gp_history/
DATA_DIR = BASE_DIR / "data"
OUT_DIR = DATA_DIR / "gp_history"
REF_DIR = DATA_DIR / "reference"
CACHE_DIR = BASE_DIR / ".cache" / "fastf1"                # cache local au projet
# Dossier d'assets (pas utilisé ici car on ne télécharge pas d'images)
ASSET_DIR = BASE_DIR / "asset"


# --- Paramètres spécifiques au GP du Mexique ---
#
# Historique rappelé :
# - 1963–1970, 1986–1992, 2015–… (interruption entre 1993 et 2014)
# Deux appellations de course : "Mexican Grand Prix" puis "Mexico City Grand Prix" (depuis 2021).
GP_LABEL = "Mexican Grand Prix"

# Fenêtres d'années où le GP a eu lieu
MEXICO_YEARS = list(range(1963, 1971)) + list(range(1986, 1993)) + list(range(2015, 2100))


# --- Colonnes cibles alignées sur le CSV Australie ---
TARGET_COLUMNS = [
    "Year",
    "GP",
    "Circuit",
    "Winner",
    "WinnerWinsOnThisGP",
    "WinnerGridPos",
    "Constructor",
    "EngineManufacturer",
    "ConstructorWinsOnThisGP",
    "P2",
    "P3",
    "SeasonChampion",
    "Trophies",
]


@dataclass
class GPRaceRow:
    Year: int
    GP: str
    Circuit: str
    Winner: str
    WinnerWinsOnThisGP: int
    WinnerGridPos: int | str
    Constructor: str
    EngineManufacturer: str  # "NA" en v1
    ConstructorWinsOnThisGP: int
    P2: str
    P3: str
    SeasonChampion: str
    Trophies: str


def _get_champion_name(ergast: Ergast, season: int) -> str:
    """Retourne le champion du monde pilotes (saison donnée) via Ergast standings.
    Gère ErgastMultiResponse **ou** DataFrame + petits écarts de colonnes.
    Inclus un retry léger contre le 429.
    """
    import pandas as _pd
    backoffs = [0.6, 1.2, 2.4, 4.8]
    resp = None
    for delay in [0] + backoffs:
        if delay:
            time.sleep(delay)
        try:
            resp = ergast.get_driver_standings(season=season, round="last")
            break
        except Exception:
            continue
    if resp is None:
        return "NA"

    if hasattr(resp, "content"):
        # ErgastMultiResponse: on prend le premier dataframe de standings
        if not resp.content:
            return "NA"
        df = resp.content[0]
    else:
        df = resp if isinstance(resp, _pd.DataFrame) else _pd.DataFrame()

    if df is None or len(df) == 0:
        return "NA"

    # Trouver la ligne du champion (position == 1) ou fallback première ligne
    pos_col = "position" if "position" in df.columns else None
    if pos_col:
        try:
            df_pos = df.copy()
            df_pos[pos_col] = df_pos[pos_col].astype(str)
            top = df_pos[df_pos[pos_col] == "1"]
            leader = top.iloc[0] if len(top) else df_pos.iloc[0]
        except Exception:
            leader = df.iloc[0]
    else:
        leader = df.iloc[0]

    given = leader.get("givenName") or leader.get("Driver.givenName") or leader.get("driver.givenName")
    family = leader.get("familyName") or leader.get("Driver.familyName") or leader.get("driver.familyName")
    if _pd.isna(given) and _pd.isna(family):
        # fallback sur un nom déjà combiné
        full = leader.get("driverName") or leader.get("Driver.code") or leader.get("Driver.surname")
        return str(full) if _pd.notna(full) else "NA"
    return f"{given} {family}".strip() if given or family else "NA"


def _find_mexico_rounds(ergast: Ergast, years: List[int]) -> List[tuple[int, int, str]]:
    """Retourne la liste (year, round, circuitName/raceName) pour les éditions disputées au Mexique.
    On identifie via `country == 'Mexico'` ou `raceName` contenant 'Mexico'.
    Gère poliment le rate limiting.
    """
    rounds: List[tuple[int, int, str]] = []
    for y in years:
        # Retry simple en cas de 429
        backoffs = [0.6, 1.2, 2.4, 4.8]
        sched = None
        for delay in [0] + backoffs:
            if delay:
                time.sleep(delay)
            try:
                sched = ergast.get_race_schedule(season=y)
                break
            except Exception:
                continue
        if sched is None:
            continue

        df_sched = sched if isinstance(sched, pd.DataFrame) else getattr(sched, "content", [pd.DataFrame()])[0]
        if df_sched is None or len(df_sched) == 0:
            continue

        df_sched = df_sched.copy()
        rn = "raceName" if "raceName" in df_sched.columns else None
        country_col = "country" if "country" in df_sched.columns else None

        # filtre Mexico
        if country_col:
            mask = (df_sched[country_col].astype(str).str.lower() == "mexico")
        else:
            mask = False
        if rn:
            mask = mask | df_sched[rn].astype(str).str.contains("Mexico", case=False, na=False)

        df_mex = df_sched[mask]
        for _, r in df_mex.iterrows():
            rnd = int(r.get("round") or r.get("Race.round") or r.get("Round", 0))
            if rnd <= 0:
                continue
            circ = str(r.get("circuitName") or r.get("Circuit.circuitName") or r.get(rn, "Mexico"))
            rounds.append((int(y), rnd, circ))
    return rounds


def _get_race_results_df(ergast: Ergast, season: int, round_: int) -> pd.DataFrame:
    """Récupère le DataFrame de résultats pour (saison, round) avec retry/backoff."""
    backoffs = [0.6, 1.2, 2.4, 4.8]
    res = None
    for delay in [0] + backoffs:
        if delay:
            time.sleep(delay)
        try:
            res = ergast.get_race_results(season=season, round=round_)
            break
        except Exception:
            continue
    if res is None:
        return pd.DataFrame()
    if hasattr(res, "content"):
        if not res.content or res.content[0] is None:
            return pd.DataFrame()
        return res.content[0]
    return res if isinstance(res, pd.DataFrame) else pd.DataFrame()


def _build_rows_for_gp(dfs_by_year: Dict[int, pd.DataFrame], gp_label: str, ergast: Ergast) -> List[GPRaceRow]:
    """À partir d'un dict {year: DF résultats}, produit les lignes finales.
    """
    # concat pour calculer cumuls
    all_df = []
    for y, df in dfs_by_year.items():
        if df is None or df.empty:
            continue
        tmp = df.copy()
        tmp["Year"] = int(y)
        all_df.append(tmp)
    if not all_df:
        return []
    df = pd.concat(all_df, ignore_index=True)

    # Colonnes possibles selon flatten Ergast
    def full_name(row):
        g = row.get("givenName") or row.get("Driver.givenName")
        f = row.get("familyName") or row.get("Driver.familyName")
        if pd.isna(g) and pd.isna(f):
            n = row.get("driverName") or row.get("Driver.code")
            return str(n) if pd.notna(n) else "NA"
        return f"{g} {f}".strip()

    df["DriverFullName"] = df.apply(full_name, axis=1)

    team_col = "constructorName" if "constructorName" in df.columns else (
        "Constructor.name" if "Constructor.name" in df.columns else "constructorId"
    )

    # cumuls par pilote & constructeur
    winners = df[df["position"].astype(str) == "1"].copy()
    pilot_win_counts = winners.groupby("DriverFullName").size().to_dict()
    team_win_counts = winners.groupby(team_col).size().to_dict()

    rows: List[GPRaceRow] = []
    for y in sorted(dfs_by_year.keys()):
        pod = dfs_by_year[y]
        if pod is None or pod.empty:
            continue
        pod = pod.copy()
        pod["position_num"] = pod["position"].astype(int)
        pod = pod[pod["position_num"].isin([1, 2, 3])].sort_values("position_num")
        if len(pod) < 3:
            continue
        p1, p2, p3 = pod.iloc[0], pod.iloc[1], pod.iloc[2]

        winner_name = full_name(p1)
        winner_grid = p1.get("grid", "NA")
        constructor = p1.get(team_col, "NA")
        # Circuit : on essaie champs de résultat sinon placeholder
        circuit_name = (
            str(p1.get("circuitName") or p1.get("Circuit.circuitName") or p1.get("raceName") or "Mexico")
        )

        rows.append(
            GPRaceRow(
                Year=int(y),
                GP=gp_label,
                Circuit=circuit_name,
                Winner=winner_name,
                WinnerWinsOnThisGP=int(pilot_win_counts.get(winner_name, 0)),
                WinnerGridPos=int(winner_grid) if pd.notna(winner_grid) else "NA",
                Constructor=str(constructor),
                EngineManufacturer="NA",
                ConstructorWinsOnThisGP=int(team_win_counts.get(constructor, 0)),
                P2=full_name(p2),
                P3=full_name(p3),
                SeasonChampion=_get_champion_name(ergast, int(y)),
                Trophies="🏆" * int(pilot_win_counts.get(winner_name, 0)),
            )
        )
    return rows


def build_mexico_history() -> pd.DataFrame:
    """Pipeline complet pour le GP du Mexique (v2: via schedule -> rounds)."""
    # Cache local au projet
    os.makedirs(CACHE_DIR, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    ergast = Ergast(result_type="pandas", auto_cast=True, limit=1000)

    rounds = _find_mexico_rounds(ergast, MEXICO_YEARS)
    if not rounds:
        return pd.DataFrame(columns=TARGET_COLUMNS)

    dfs_by_year: Dict[int, pd.DataFrame] = {}
    for y, rnd, _circ in rounds:
        df_res = _get_race_results_df(ergast, y, rnd)
        time.sleep(0.5)  # délai poli entre appels
        if df_res is None or df_res.empty:
            continue
        dfs_by_year[y] = df_res

    rows = _build_rows_for_gp(dfs_by_year, GP_LABEL, ergast)
    out = pd.DataFrame([r.__dict__ for r in rows], columns=TARGET_COLUMNS)
    out = out.sort_values("Year").reset_index(drop=True)
    return out


def main():
    parser = argparse.ArgumentParser(description="Build GP history — Mexico (v1)")
    parser.add_argument(
        "--out",
        type=str,
        default=str(OUT_DIR / "mexican_grand_prix.csv"),
        help="Chemin de sortie CSV (défaut: gp_history/data/gp_history/mexican_grand_prix.csv)",
    )
    parser.add_argument(
        "--with-winner-image",
        action="store_true",
        help="Ajoute la colonne WinnerImageURL via OpenF1/Wikipedia",
    )
    args = parser.parse_args()

    # Build
    df = build_mexico_history()

    # Enrichissement image du vainqueur (URL uniquement)
    if args.with_winner_image:
        try:
            # Import depuis le package local gp_history
            from gp_history.tools.enrichments.images import enrich_winner_image
            df = enrich_winner_image(df)
        except Exception as e:
            print(f"[warn] enrich_winner_image a échoué: {e}")

    # Écriture CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"✅ Écrit: {out_path} — {len(df)} lignes")


if __name__ == "__main__":
    main()
