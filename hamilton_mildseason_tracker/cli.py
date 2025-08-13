# =========================
# file: hamilton_midseason_tracker/cli.py
# =========================
from __future__ import annotations

import argparse
import logging
from typing import Tuple

from .pipeline import run_pipeline


def _parse_years(value: str) -> Tuple[int, int]:
    if "," in value:
        parts = [int(v.strip()) for v in value.split(",") if v.strip()]
        if len(parts) == 1:
            return parts[0], parts[0]
        return min(parts), max(parts)
    if "-" in value:
        a, b = value.split("-", 1)
        return int(a), int(b)
    y = int(value)
    return y, y


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hamilton mid-season snapshot")
    parser.add_argument("--years", default="2008,2016,2022", help="Ex: 2008,2016,2022 ou 2007-2025")
    parser.add_argument("--log", default="INFO", help="Logging level (DEBUG/INFO/WARN/ERROR)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log.upper(), logging.INFO), format="[%(levelname)s] %(message)s")
    y0, y1 = _parse_years(args.years)
    rows = run_pipeline(y0, y1)

    # Narratif minimal
    if rows:
        worst = sorted(rows, key=lambda r: r.pct_of_leader)[0]
        logging.info(
            "Pire mi-saison (%% leader) dans l'intervalle [%s-%s]: %s (%.3f)", y0, y1, worst.year, worst.pct_of_leader
        )
    return 0
