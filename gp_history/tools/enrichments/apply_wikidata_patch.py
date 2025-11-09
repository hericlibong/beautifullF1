# gp_history/tools/enrichments/apply_wikidata_patch.py
from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]  # -> gp_history/
DATA_DIR = BASE_DIR / "data"
GP_CSV_IN = DATA_DIR / "gp_history" / "mexican_grand_prix.csv"
PATCH_CSV = DATA_DIR / "reference" / "wikidata_query_results.csv"
GP_CSV_OUT = DATA_DIR / "gp_history" / "mexican_grand_prix.csv"  # écrase le fichier


def _prepare_patch_df(patch_path: Path) -> pd.DataFrame:
    dfp = pd.read_csv(patch_path)
    cols = {c.lower(): c for c in dfp.columns}
    in_col = cols.get("inputname") or cols.get("winner") or "inputName"
    img_col = cols.get("image") or cols.get("winnerimageurl") or "image"
    if in_col not in dfp.columns or img_col not in dfp.columns:
        raise ValueError(f"Colonnes manquantes dans {patch_path} (attendu: inputName + image)")

    dfp = dfp[[in_col, img_col]].rename(columns={in_col: "Winner", img_col: "WinnerImageURL"})
    dfp["Winner"] = dfp["Winner"].astype(str).str.strip()
    dfp["WinnerImageURL"] = dfp["WinnerImageURL"].astype(str).str.strip()
    dfp = dfp[dfp["WinnerImageURL"].notna() & (dfp["WinnerImageURL"] != "")]
    return dfp.drop_duplicates(subset=["Winner"], keep="first")


def apply_patch(gp_csv_in: Path, patch_csv: Path, gp_csv_out: Path) -> int:
    df = pd.read_csv(gp_csv_in)
    if "Winner" not in df.columns:
        raise ValueError("La colonne 'Winner' est absente du CSV GP")
    if "WinnerImageURL" not in df.columns:
        df["WinnerImageURL"] = None

    patch = _prepare_patch_df(patch_csv)
    before_missing = df["WinnerImageURL"].isna() | (df["WinnerImageURL"] == "")

    merged = df.merge(patch, on="Winner", how="left", suffixes=("", "_patch"))
    fill_mask = (
        before_missing
        & merged["WinnerImageURL_patch"].notna()
        & (merged["WinnerImageURL_patch"] != "")
    )
    merged.loc[fill_mask, "WinnerImageURL"] = merged.loc[fill_mask, "WinnerImageURL_patch"]

    merged = merged.drop(
        columns=[c for c in merged.columns if c.endswith("_patch")], errors="ignore"
    )
    gp_csv_out.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(gp_csv_out, index=False)
    return int(fill_mask.sum())


if __name__ == "__main__":
    if not GP_CSV_IN.exists():
        raise FileNotFoundError(f"Introuvable: {GP_CSV_IN}")
    if not PATCH_CSV.exists():
        raise FileNotFoundError(
            f"Introuvable: {PATCH_CSV} (exécute wikidata_fetch.py ou copie ton query.csv)"
        )
    n = apply_patch(GP_CSV_IN, PATCH_CSV, GP_CSV_OUT)
    print(f"✅ Patch appliqué: {n} lignes complétées → {GP_CSV_OUT}")
