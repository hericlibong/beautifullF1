"""
Beautifull F1 — run_mexico_full.py

Lanceur UNIQUE qui:
  1) génère l'historique du GP du Mexique (FastF1/Ergast)
  2) ajoute WinnerImageURL (OpenF1/Wikipedia)
  3) récupère les images manquantes via SPARQL Wikidata
  4) applique le patch et réécrit le CSV final

Prérequis:
  pip install fastf1 pandas requests sparqlwrapper
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# --- Corrige le path pour autoriser "import gp_history...." quand lancé en script ---
THIS_FILE = Path(__file__).resolve()
TOOLS_DIR = THIS_FILE.parent  # gp_history/tools
GP_HISTORY_DIR = TOOLS_DIR.parent  # gp_history
REPO_ROOT = GP_HISTORY_DIR.parent  # racine du repo

# Assure que la racine du repo est sur sys.path (pour importer gp_history.*)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# (Optionnel mais conseillé) Si tu crées gp_history/__init__.py, ce hack n'est plus indispensable.

# --- Répertoires projet ---------------------------------------------------
BASE_DIR = GP_HISTORY_DIR  # -> gp_history/
DATA_DIR = BASE_DIR / "data"
OUT_DIR = DATA_DIR / "gp_history"
REF_DIR = DATA_DIR / "reference"
GP_CSV = OUT_DIR / "mexican_grand_prix.csv"
PATCH_CSV = REF_DIR / "wikidata_query_results.csv"

# --- 1) Build historique (Mexique) ---------------------------------------
try:
    from gp_history.tools.gp_history_builder_mexique_v1 import build_mexico_history
except Exception as e:
    raise SystemExit(f"[fatal] Import builder échoué: {e}")


def step1_build() -> pd.DataFrame:
    df = build_mexico_history()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(GP_CSV, index=False)
    print(f"[1/4] Historique écrit: {GP_CSV} — {len(df)} lignes")
    return df


# --- 2) Enrichir WinnerImageURL (OpenF1/Wikipedia) -----------------------
try:
    from gp_history.tools.enrichments.images import enrich_winner_image
except Exception as e:
    raise SystemExit(f"[fatal] Import images échoué: {e}")


def step2_enrich_images(df: pd.DataFrame) -> pd.DataFrame:
    df2 = enrich_winner_image(df)
    df2.to_csv(GP_CSV, index=False)
    n_filled = int(df2["WinnerImageURL"].notna().sum())
    print(f"[2/4] WinnerImageURL (OpenF1/Wikipedia) appliqué — {n_filled} lignes avec URL")
    return df2


# --- 3) SPARQL Wikidata pour les manquants -------------------------------
try:
    from gp_history.tools.enrichments.wikidata_fetch import (
        build_query,
        load_missing_winners,
        run_sparql,
    )

    SPARQL_READY = True
except Exception:
    SPARQL_READY = False


def step3_fetch_wikidata() -> bool:
    if not SPARQL_READY:
        print("[3/4] SPARQLWrapper non dispo — étape Wikidata sautée (pip install sparqlwrapper)")
        return False
    names = load_missing_winners()
    if not names:
        print("[3/4] Aucun vainqueur manquant (WinnerImageURL déjà rempli).")
        return False
    q = build_query(names)
    dfq = run_sparql(q)
    REF_DIR.mkdir(parents=True, exist_ok=True)
    dfq.to_csv(PATCH_CSV, index=False)
    print(f"[3/4] Patch Wikidata écrit: {PATCH_CSV} — {len(dfq)} lignes")
    return True


# --- 4) Appliquer le patch ----------------------------------------------
try:
    from gp_history.tools.enrichments.apply_wikidata_patch import apply_patch

    PATCH_READY = True
except Exception:
    PATCH_READY = False


def step4_apply_patch() -> int:
    if not PATCH_READY:
        print("[4/4] Module apply_wikidata_patch indisponible — étape sautée")
        return 0
    if not PATCH_CSV.exists():
        print("[4/4] Aucun patch CSV trouvé — étape sautée")
        return 0
    n = apply_patch(GP_CSV, PATCH_CSV, GP_CSV)
    print(f"[4/4] Patch appliqué: {n} lignes mises à jour → {GP_CSV}")
    return n


if __name__ == "__main__":
    # Étape 1
    df = step1_build()
    # Étape 2
    df = step2_enrich_images(df)
    # Étape 3
    _ = step3_fetch_wikidata()
    # Étape 4
    _ = step4_apply_patch()
    print("✅ Terminé — fichier final prêt:", GP_CSV)
