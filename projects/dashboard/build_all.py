"""Pipeline unifié : régénère toutes les données + propage dans docs/.

Usage :
    python projects/dashboard/build_all.py
    python projects/dashboard/build_all.py --skip-fetch   # n'appelle pas FastF1
    python projects/dashboard/build_all.py --season 2026  # par défaut

Étapes exécutées dans l'ordre :
    1. race_chart_builder_fastf1.py        → outputs/f1_race_chart_fastf1_<season>.csv
    2. copie vers web/data/                (consommé par la viz)
    3. lead_main.py (heatmap leaders)      → outputs/f1_<season>_leaders_heatmap.csv
    4. copie vers d3_dataviz/              (consommé par la viz)
    5. build_dashboard_data.py             → docs/data/dashboard_<season>.json
    6. sync_to_docs.py × 3                 (race_chart, heatmap, dashboard)

Le calendrier (calendar_<season>.json) n'est pas régénéré ici — il évolue
rarement, lance fetch_calendar.py manuellement si besoin.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def run_step(label: str, cmd: list[str], cwd: Path | None = None) -> bool:
    print(f"\n>>> {label}")
    print(f"    $ {' '.join(str(c) for c in cmd)}")
    if cwd:
        print(f"    cwd={cwd}")
    result = subprocess.run(cmd, cwd=cwd)
    ok = result.returncode == 0
    print(f"    {'[OK]' if ok else f'[ECHEC code={result.returncode}]'}")
    return ok


def copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"    [SKIP] {src} introuvable")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"    [COPY] {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Saute les builders qui interrogent FastF1 (étapes 1 et 3)")
    args = parser.parse_args()
    season = args.season

    rc_root = ROOT / "projects" / "race_chart_builder"
    hm_root = ROOT / "projects" / "season_summary_heatmap"
    db_root = ROOT / "projects" / "dashboard"

    # 1) Race chart : fetch + génération CSV brut
    if not args.skip_fetch:
        ok = run_step(
            "1/6 race_chart_builder_fastf1",
            [PYTHON, str(rc_root / "race_chart_builder_fastf1.py"), "--season", str(season)],
            cwd=rc_root,
        )
        if not ok:
            return 1
    else:
        print("\n>>> 1/6 race_chart_builder_fastf1 (sauté via --skip-fetch)")

    # 2) Copie vers web/data/
    print("\n>>> 2/6 copie race_chart CSV vers web/data/")
    copy_file(
        rc_root / "outputs" / f"f1_race_chart_fastf1_{season}.csv",
        rc_root / "web" / "data" / f"f1_race_chart_fastf1_{season}.csv",
    )

    # 3) Heatmap : fetch + génération CSV leaders
    if not args.skip_fetch:
        ok = run_step(
            "3/6 lead_main (heatmap leaders)",
            [PYTHON, str(hm_root / "lead_main.py"), "--season", str(season)],
            cwd=hm_root,
        )
        if not ok:
            return 1
    else:
        print("\n>>> 3/6 lead_main (sauté via --skip-fetch)")

    # 4) Copie vers d3_dataviz/
    print("\n>>> 4/6 copie heatmap CSV vers d3_dataviz/")
    copy_file(
        hm_root / "outputs" / f"f1_{season}_leaders_heatmap.csv",
        hm_root / "d3_dataviz" / f"f1_{season}_leaders_heatmap.csv",
    )

    # 5) Dashboard JSON
    ok = run_step(
        "5/6 build_dashboard_data",
        [PYTHON, str(db_root / "build_dashboard_data.py")],
    )
    if not ok:
        return 1

    # 5b) Qualifying JSON (duels coéquipiers)
    if not args.skip_fetch:
        ok = run_step(
            "5b/6 build_qualifying_data",
            [PYTHON, str(db_root / "build_qualifying_data.py")],
        )
        if not ok:
            return 1
    else:
        print("\n>>> 5b/6 build_qualifying_data (sauté via --skip-fetch)")

    # 6) Sync vers docs/ (les 3 projets)
    for label, script in [
        ("race_chart sync",   rc_root / "sync_to_docs.py"),
        ("heatmap sync",      hm_root / "sync_to_docs.py"),
        ("dashboard sync",    db_root / "sync_to_docs.py"),
    ]:
        ok = run_step(f"6/6 {label}", [PYTHON, str(script)])
        if not ok:
            return 1

    print("\n[OK] Pipeline complète.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
