#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hamilton Mid-Season Tracker (2007–2025)
---------------------------------------

Objectif
========
Comparer la performance de Lewis Hamilton à la **pause estivale** (dernier GP avant la coupure d’août)
pour chaque saison, via un indicateur principal robuste : **% des points du leader** à la date de coupure.

Sorties
=======
- CSV : hamilton_midseason_snapshot.csv
- JSON : hamilton_midseason_snapshot.json

Dépendances
===========
- requests
- pandas
- fastf1 (pour le calendrier)

Structure
=========
Ce fichier regroupe les composants en sections (clients API, calculs, export, CLI) pour facilité de copie.
Au besoin, vous pouvez le scinder en modules comme décrit dans le brief.

Notes
=====
- Sources API : miroir Ergast via Jolpica (https://api.jolpi.ca/ergast/f1/)
- Les endpoints/schémas sont compatibles Ergast.
- Nous lisons le driverStandings **au round de coupure** comme source de vérité des points.

"""

from __future__ import annotations

import csv
import json
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

try:
    import fastf1  # type: ignore
except Exception as exc:  # pragma: no cover
    fastf1 = None
    logging.warning("FastF1 non disponible (%s) – la détection de la coupure utilisera un fallback.", exc)

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

BASE_URL = "https://api.jolpi.ca/ergast/f1"
DRIVER_ID = "hamilton"
SEASON_START = 2007
SEASON_END = 2025

HTTP_TIMEOUT = 30
RETRY_COUNT = 3
RETRY_BACKOFF = 1.5  # secondes, facteur d'augmentation

OUTPUT_CSV = "hamilton_midseason_snapshot.csv"
OUTPUT_JSON = "hamilton_midseason_snapshot.json"

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)

# -----------------------------------------------------------------------------
# Utils
# -----------------------------------------------------------------------------

_STATUS_FINISH_OK = re.compile(r"^(?:Finished|Winner|\+\d+ Laps?)$", re.IGNORECASE)


def _is_finish_status(status: str) -> bool:
    return bool(_STATUS_FINISH_OK.match(status.strip()))


# -----------------------------------------------------------------------------
# Client Ergast/Jolpica
# -----------------------------------------------------------------------------

class ErgastClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = HTTP_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _fetch(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:  # pragma: no cover (réseau)
                last_exc = exc
                sleep_s = RETRY_BACKOFF ** attempt
                logging.warning("HTTP retry %s/%s for %s (%s)", attempt, RETRY_COUNT, url, exc)
                time.sleep(sleep_s)
        raise RuntimeError(f"HTTP error for {url}: {last_exc}")

    def get_driver_standings_at(self, year: int, round_: int) -> Dict[str, Any]:
        """Retourne le payload JSON brut driverStandings au round donné."""
        path = f"/{year}/{round_}/driverStandings.json"
        return self._fetch(path)

    def get_season_results(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """Retourne les résultats de la saison (tous rounds)."""
        params = {"limit": limit, "offset": offset}
        path = f"/{year}/results.json"
        return self._fetch(path, params=params)

    def get_qualifying(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        path = f"/{year}/qualifying.json"
        return self._fetch(path, params=params)


# -----------------------------------------------------------------------------
# Schedule (FastF1) – détection du round de coupure
# -----------------------------------------------------------------------------

@dataclass
class CutoffInfo:
    round: int
    gp_name: str
    gp_date_iso: str


def find_round_cutoff(year: int) -> CutoffInfo:
    """Trouve la coupure estivale via le plus grand gap en août.

    Algorithme (par défaut):
      1. Charger le calendrier via FastF1
      2. Ordonner par date (EventDate)
      3. Calculer les gaps entre GP successifs
      4. Restreindre aux gaps dont la date de départ ∈ [15 juin ; 15 septembre]
      5. Prendre le gap maximal → le GP juste AVANT ce gap est le round_cutoff

    Fallback si FastF1 indisponible: heuristique simple → dernier GP dont la date <= 10 août.
    """
    if fastf1 is None:
        logging.warning("FastF1 absent – utilisation du fallback calendrier heuristique.")
        return _fallback_cutoff_heuristic(year)

    try:
        schedule = fastf1.get_event_schedule(year)  # DataFrame
    except Exception as exc:  # pragma: no cover
        logging.warning("FastF1 get_event_schedule a échoué (%s) – fallback heuristique.", exc)
        return _fallback_cutoff_heuristic(year)

    df = (
        schedule[["RoundNumber", "EventName", "EventDate"]]
        .dropna()
        .sort_values("EventDate")
        .reset_index(drop=True)
    )
    if df.empty:
        logging.warning("Calendrier vide – fallback heuristique.")
        return _fallback_cutoff_heuristic(year)

    # Fenêtre d’intérêt
    start = pd.Timestamp(year=year, month=6, day=15)
    end = pd.Timestamp(year=year, month=9, day=15)

    # Gaps
    gaps: List[Tuple[int, pd.Timestamp, pd.Timedelta]] = []
    for i in range(len(df) - 1):
        date_i = pd.to_datetime(df.loc[i, "EventDate"])  # type: ignore[arg-type]
        date_j = pd.to_datetime(df.loc[i + 1, "EventDate"])  # type: ignore[arg-type]
        if not (start <= date_i <= end):
            continue
        gap = date_j - date_i
        gaps.append((i, date_i, gap))

    if not gaps:
        # Aucun gap dans la fenêtre → fallback: dernier GP <= 10 août
        return _fallback_cutoff_from_schedule(df)

    # Gap maximal
    gaps.sort(key=lambda t: t[2], reverse=True)
    idx, date_i, gap = gaps[0]
    round_cutoff = int(df.loc[idx, "RoundNumber"])  # le GP juste avant le gap
    gp_name = str(df.loc[idx, "EventName"])  # type: ignore[index]
    gp_date_iso = pd.to_datetime(df.loc[idx, "EventDate"]).date().isoformat()

    logging.info(
        "Cutoff %s: round=%s, GP=%s, date=%s, gap=%s jours",
        year,
        round_cutoff,
        gp_name,
        gp_date_iso,
        int(gap / pd.Timedelta(days=1)),
    )

    return CutoffInfo(round=round_cutoff, gp_name=gp_name, gp_date_iso=gp_date_iso)


def _fallback_cutoff_heuristic(year: int) -> CutoffInfo:
    """Fallback sans FastF1: suppose que la coupure intervient début/mi-août.
    Choisit le dernier round dont la date (estimée) serait ≤ 10 août.
    Comme nous n’avons pas les dates, on prend un cutoff fixe (ex: 12e GP ou 13e selon charge calendrier).
    Cette heuristique est volontairement conservatrice – à remplacer par FastF1 dès dispo.
    """
    # Heuristique minimaliste: cutoff à 12 (saisons 19–24 GP)
    round_cutoff = 12
    return CutoffInfo(round=round_cutoff, gp_name="(unknown)", gp_date_iso=f"{year}-08-01")


def _fallback_cutoff_from_schedule(df: pd.DataFrame) -> CutoffInfo:
    # Dernier GP <= 10 août
    dates = pd.to_datetime(df["EventDate"])  # type: ignore[arg-type]
    mask = dates <= pd.Timestamp(year=dates.dt.year.iloc[0], month=8, day=10)
    if mask.any():
        idx = mask[mask].index.max()
    else:
        idx = len(df) // 2  # à défaut, milieu de saison
    round_cutoff = int(df.loc[idx, "RoundNumber"])  # type: ignore[index]
    gp_name = str(df.loc[idx, "EventName"])  # type: ignore[index]
    gp_date_iso = pd.to_datetime(df.loc[idx, "EventDate"]).date().isoformat()
    return CutoffInfo(round=round_cutoff, gp_name=gp_name, gp_date_iso=gp_date_iso)


# -----------------------------------------------------------------------------
# Transformations / Calculs
# -----------------------------------------------------------------------------

@dataclass
class StandingsAtRound:
    hamilton_points: float
    hamilton_rank: int
    wins_to_date: int
    leader_points: float
    standings_entries: List[Dict[str, Any]]  # brut pour calcul coéquipier


def parse_standings_payload(payload: Dict[str, Any]) -> StandingsAtRound:
    """Extrait les infos utiles depuis le JSON driverStandings."""
    mr = payload.get("MRData", {})
    st_table = mr.get("StandingsTable", {})
    lists = st_table.get("StandingsLists", [])
    if not lists:
        raise ValueError("StandingsLists vide")
    lst = lists[0]
    entries = lst.get("DriverStandings", [])
    if not entries:
        raise ValueError("DriverStandings vide")

    # Leader points
    leader_points = 0.0
    for e in entries:
        try:
            leader_points = max(leader_points, float(e.get("points", 0)))
        except Exception:
            pass

    # Hamilton
    hamilton_points = 0.0
    hamilton_rank = math.inf
    wins_to_date = 0
    for e in entries:
        d = e.get("Driver", {})
        if d.get("driverId") == DRIVER_ID:
            hamilton_points = float(e.get("points", 0))
            hamilton_rank = int(e.get("position", 999))
            wins_to_date = int(e.get("wins", 0))
            break

    if leader_points == 0:
        leader_points = 1e-9  # éviter division par zéro plus tard

    return StandingsAtRound(
        hamilton_points=hamilton_points,
        hamilton_rank=int(hamilton_rank if hamilton_rank != math.inf else 999),
        wins_to_date=wins_to_date,
        leader_points=leader_points,
        standings_entries=entries,
    )


@dataclass
class ResultsAggregate:
    podiums_to_date: int
    dnf_to_date: int
    races_started: int
    races_scored_pct: float
    constructor_id: str


def aggregate_from_results(results_payload: Dict[str, Any], round_cutoff: int) -> ResultsAggregate:
    """Calcule les agrégats de résultats pour Hamilton jusqu'au round_cutoff inclus."""
    mr = results_payload.get("MRData", {})
    race_table = mr.get("RaceTable", {})
    races = race_table.get("Races", [])

    podiums = 0
    dnf = 0
    started = 0
    scored = 0
    constructor_id = ""

    # Conserver le constructor du dernier GP <= cutoff
    last_round_seen = -1

    for race in races:
        try:
            rnd = int(race.get("round"))
        except Exception:
            continue
        if rnd > round_cutoff:
            continue
        res_list = race.get("Results", [])
        for res in res_list:
            drv = res.get("Driver", {})
            if drv.get("driverId") != DRIVER_ID:
                continue
            started += 1
            pos = str(res.get("position", ""))
            status = str(res.get("status", ""))
            pts = float(res.get("points", 0))
            if pos in {"1", "2", "3"}:
                podiums += 1
            if not _is_finish_status(status):
                dnf += 1
            if pts > 0:
                scored += 1
            # Constructor
            try:
                if rnd >= last_round_seen:
                    cons = res.get("Constructor", {})
                    constructor_id = cons.get("constructorId", constructor_id)
                    last_round_seen = rnd
            except Exception:
                pass

    races_scored_pct = (scored / started) if started else 0.0

    return ResultsAggregate(
        podiums_to_date=podiums,
        dnf_to_date=dnf,
        races_started=started,
        races_scored_pct=races_scored_pct,
        constructor_id=constructor_id or "unknown",
    )


def count_poles(qual_payload: Dict[str, Any], round_cutoff: int) -> int:
    mr = qual_payload.get("MRData", {})
    race_table = mr.get("RaceTable", {})
    races = race_table.get("Races", [])

    poles = 0
    for race in races:
        try:
            rnd = int(race.get("round"))
        except Exception:
            continue
        if rnd > round_cutoff:
            continue
        q_list = race.get("QualifyingResults", [])
        for q in q_list:
            drv = q.get("Driver", {})
            if drv.get("driverId") == DRIVER_ID and str(q.get("position")) == "1":
                poles += 1
    return poles


@dataclass
class TeammateStats:
    teammate_points_to_date: float
    teammate_gap: float


def teammate_points_at_round(std: StandingsAtRound, constructor_id: str) -> Optional[TeammateStats]:
    """Trouve le meilleur coéquipier (même constructor_id) et calcule l'écart.
    Utilise la table driverStandings au round de coupure.
    """
    if not constructor_id or constructor_id == "unknown":
        return None

    best_team_points = None
    for e in std.standings_entries:
        drv = e.get("Driver", {})
        if drv.get("driverId") == DRIVER_ID:
            continue
        constructors = e.get("Constructors", [])
        cons_id = None
        if constructors:
            cons_id = constructors[0].get("constructorId")
        if cons_id == constructor_id:
            pts = float(e.get("points", 0))
            if best_team_points is None or pts > best_team_points:
                best_team_points = pts

    if best_team_points is None:
        return None

    gap = std.hamilton_points - float(best_team_points)
    return TeammateStats(teammate_points_to_date=float(best_team_points), teammate_gap=gap)


# -----------------------------------------------------------------------------
# Assemblage & Export
# -----------------------------------------------------------------------------

@dataclass
class YearRecord:
    year: int
    round_cutoff: int
    gp_name_cutoff: str
    gp_date_cutoff: str
    hamilton_rank: int
    hamilton_points: float
    leader_points: float
    points_behind: float
    pct_of_leader: float
    wins_to_date: int
    podiums_to_date: int
    poles_to_date: int
    dnf_to_date: int
    races_started: int
    races_scored_pct: float
    constructor_id: str
    teammate_points_to_date: Optional[float]
    teammate_gap: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "round_cutoff": self.round_cutoff,
            "gp_name_cutoff": self.gp_name_cutoff,
            "gp_date_cutoff": self.gp_date_cutoff,
            "hamilton_rank": self.hamilton_rank,
            "hamilton_points": self.hamilton_points,
            "leader_points": self.leader_points,
            "points_behind": self.points_behind,
            "pct_of_leader": self.pct_of_leader,
            "wins_to_date": self.wins_to_date,
            "podiums_to_date": self.podiums_to_date,
            "poles_to_date": self.poles_to_date,
            "dnf_to_date": self.dnf_to_date,
            "races_started": self.races_started,
            "races_scored_pct": self.races_scored_pct,
            "constructor_id": self.constructor_id,
            "teammate_points_to_date": self.teammate_points_to_date,
            "teammate_gap": self.teammate_gap,
        }


def build_year_record(
    year: int,
    cutoff: CutoffInfo,
    standings: StandingsAtRound,
    res: ResultsAggregate,
    poles: int,
    team_stats: Optional[TeammateStats],
) -> YearRecord:
    leader = max(standings.leader_points, 1e-9)
    pct = float(standings.hamilton_points) / float(leader)
    points_behind = float(leader) - float(standings.hamilton_points)

    return YearRecord(
        year=year,
        round_cutoff=cutoff.round,
        gp_name_cutoff=cutoff.gp_name,
        gp_date_cutoff=cutoff.gp_date_iso,
        hamilton_rank=standings.hamilton_rank,
        hamilton_points=standings.hamilton_points,
        leader_points=leader,
        points_behind=points_behind,
        pct_of_leader=pct,
        wins_to_date=standings.wins_to_date,
        podiums_to_date=res.podiums_to_date,
        poles_to_date=poles,
        dnf_to_date=res.dnf_to_date,
        races_started=res.races_started,
        races_scored_pct=res.races_scored_pct,
        constructor_id=res.constructor_id,
        teammate_points_to_date=(team_stats.teammate_points_to_date if team_stats else None),
        teammate_gap=(team_stats.teammate_gap if team_stats else None),
    )


def write_csv(rows: List[YearRecord], path: str = OUTPUT_CSV) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].to_dict().keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r.to_dict())
    logging.info("CSV écrit: %s (%s lignes)", path, len(rows))


def write_json(rows: List[YearRecord], path: str = OUTPUT_JSON, indent: int = 2) -> None:
    data = [r.to_dict() for r in rows]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    logging.info("JSON écrit: %s", path)


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------

def run_pipeline(year_start: int = SEASON_START, year_end: int = SEASON_END) -> List[YearRecord]:
    client = ErgastClient()
    out: List[YearRecord] = []

    for year in range(year_start, year_end + 1):
        try:
            cutoff = find_round_cutoff(year)
        except Exception as exc:
            logging.error("[%s] Erreur calcul cutoff: %s", year, exc)
            continue

        # Standings @ cutoff
        try:
            standings_payload = client.get_driver_standings_at(year, cutoff.round)
            standings = parse_standings_payload(standings_payload)
        except Exception as exc:
            logging.error("[%s] Erreur standings@R: %s", year, exc)
            continue

        # Results ≤ cutoff
        try:
            results_payload = client.get_season_results(year, limit=1000, offset=0)
            res_aggr = aggregate_from_results(results_payload, cutoff.round)
        except Exception as exc:
            logging.error("[%s] Erreur results: %s", year, exc)
            continue

        # Qualifying ≤ cutoff
        try:
            qual_payload = client.get_qualifying(year, limit=1000, offset=0)
            poles = count_poles(qual_payload, cutoff.round)
        except Exception as exc:
            logging.warning("[%s] Qualifying indisponible: %s", year, exc)
            poles = 0

        # Teammate stats (optionnel)
        team_stats: Optional[TeammateStats] = None
        try:
            team_stats = teammate_points_at_round(standings, res_aggr.constructor_id)
        except Exception as exc:
            logging.warning("[%s] Coéquipier non calculé: %s", year, exc)

        record = build_year_record(year, cutoff, standings, res_aggr, poles, team_stats)
        out.append(record)

    return out


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(year_start: int = SEASON_START, year_end: int = SEASON_END) -> int:
    rows = run_pipeline(year_start, year_end)
    # Tri par année croissante (sécurité)
    rows.sort(key=lambda r: r.year)
    write_csv(rows, OUTPUT_CSV)
    write_json(rows, OUTPUT_JSON)

    # Log narratif minimal – identification de la pire mi-saison par % leader
    if rows:
        worst = sorted(rows, key=lambda r: r.pct_of_leader)[0]
        logging.info(
            "Pire mi-saison selon %% points du leader: %s (%.3f) – rank=%s, points=%s, leader=%s",
            worst.year,
            worst.pct_of_leader,
            worst.hamilton_rank,
            worst.hamilton_points,
            worst.leader_points,
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
