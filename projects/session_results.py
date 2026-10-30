"""Chargement commun des classements, indépendant de la télémétrie live."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd


def load_results(season: int, round_no: int, session: str, attempts: int = 3):
    """Retourne une session complète ou échoue ; un sprint absent n'est pas zéro.

    Les tours/télémétries ne servent pas aux points. Les demander ajoute des
    requêtes et des pannes possibles, notamment lorsque le live timing manque.
    """
    cache = os.environ.get("FASTF1_CACHE")
    if cache:
        Path(cache).mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(cache)

    for attempt in range(1, attempts + 1):
        try:
            loaded = fastf1.get_session(season, round_no, session)
            loaded.load(laps=False, telemetry=False, weather=False, messages=False)
            results = loaded.results
            if results is None or results.empty:
                raise ValueError("résultats vides")
            for column in ("FullName", "Abbreviation", "TeamName"):
                if results[column].isna().any() or results[column].eq("").any():
                    raise ValueError(f"{column} incomplet")
            points = pd.to_numeric(results["Points"], errors="coerce")
            if not np.isfinite(points).all() or (points < 0).any():
                raise ValueError("points absents ou invalides")
            if points.sum() <= 0 or results["Abbreviation"].duplicated().any():
                raise ValueError("classement incomplet ou pilotes dupliqués")
            if not (pd.to_numeric(results["Position"], errors="coerce") == 1).any():
                raise ValueError("classement sans vainqueur")
            return loaded
        except Exception as exc:
            print(
                f"[RETRY] {season} round {round_no} {session} " f"({attempt}/{attempts}) : {exc}",
                file=sys.stderr,
            )
            if attempt == attempts:
                raise RuntimeError(
                    f"Résultats indisponibles : {season} round {round_no} {session}"
                ) from exc
            time.sleep(5 * attempt)
