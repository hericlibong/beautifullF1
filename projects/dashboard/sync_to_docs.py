"""Synchronise projects/dashboard/web/ vers docs/ (racine GitHub Pages).

Usage :
    python projects/dashboard/sync_to_docs.py

Source canonique : projects/dashboard/web/
Cible publique  : docs/   (à la racine, car la dashboard est la home page)

Copie additive : ne supprime rien dans docs/ — préserve les autres viz
(race_chart_builder/, season_summary_heatmap/, ...).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "web"
DST = HERE.parents[1] / "docs"


def main() -> int:
    if not SRC.is_dir():
        print(f"[ERREUR] Source introuvable : {SRC}", file=sys.stderr)
        return 1

    DST.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in SRC.rglob("*"):
        rel = path.relative_to(SRC)
        target = DST / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copied += 1

    print(f"[OK] {copied} fichier(s) synchronisé(s)")
    print(f"     {SRC} -> {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
