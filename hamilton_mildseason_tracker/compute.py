from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .config import DRIVER_ID

_STATUS_FINISH_OK = re.compile(r"^(?:Finished|Winner|\+\d+ Laps?)$", re.IGNORECASE)

# DNF strict : vrais abandons (retirements)
RETIREMENT_KEYWORDS = {
    "retired", "accident", "collision", "engine", "gearbox", "hydraulics",
    "electrical", "power unit", "brakes", "suspension", "mechanical", "overheating"
}
# Statuts non-DNF (ne pas confondre avec abandons)
NON_DNF_STATUSES = {
    "disqualified", "excluded", "did not start", "did not qualify", "withdrawn", "not classified"
}


def _is_finish_status(status: str) -> bool:
    return bool(_STATUS_FINISH_OK.match((status or "").strip()))


def _is_retirement(position_text: str, status: str) -> bool:
    """
    DNF strict = véritable abandon en course.
    - True si positionText == 'R'
    - OU si le status contient un mot-clé d'abandon
    - EXCLUSION explicite : DSQ/DNS/DNQ/Withdrawn/Not Classified -> pas DNF
    """
    s = (status or "").strip().lower()
    if s in NON_DNF_STATUSES:
        return False
    if (position_text or "").strip().upper() == "R":
        return True
    if any(k in s for k in RETIREMENT_KEYWORDS):
        return True
    return False


@dataclass
class StandingsAtRound:
    hamilton_points: float
    hamilton_rank: int
    wins_to_date: int
    leader_points: float
    standings_entries: List[Dict[str, Any]]


def parse_standings_payload(payload: Dict[str, Any]) -> StandingsAtRound:
    mr = payload.get("MRData", {})
    st_table = mr.get("StandingsTable", {})
    lists = st_table.get("StandingsLists", [])
    if not lists:
        raise ValueError("StandingsLists vide")
    entries = lists[0].get("DriverStandings", [])
    if not entries:
        raise ValueError("DriverStandings vide")

    leader_points = 0.0
    for e in entries:
        try:
            leader_points = max(leader_points, float(e.get("points", 0)))
        except Exception:
            pass

    h_points = 0.0
    h_rank = math.inf
    h_wins = 0
    for e in entries:
        d = e.get("Driver", {})
        if d.get("driverId") == DRIVER_ID:
            h_points = float(e.get("points", 0))
            h_rank = int(e.get("position", 999))
            h_wins = int(e.get("wins", 0))
            break

    return StandingsAtRound(
        hamilton_points=h_points,
        hamilton_rank=int(h_rank if h_rank != math.inf else 999),
        wins_to_date=h_wins,
        leader_points=(leader_points or 1e-9),
        standings_entries=entries,
    )


@dataclass
class ResultsAggregate:
    podiums_to_date: int
    dnf_to_date: int
    races_started: int
    race_scored_pct_main: float         # % courses principales avec points
    weekend_scored_pct: float           # % week-ends (GP+Sprint) avec points
    zero_point_weekends_to_date: int    # nb de week-ends à 0 point
    constructor_id: str


def build_sprint_points_map(sprint_payload: Dict[str, Any], driver_id: str = DRIVER_ID) -> dict[int, float]:
    """Construit {round: points_sprint_du_pilote} pour l'année."""
    mr = sprint_payload.get("MRData", {})
    races = mr.get("RaceTable", {}).get("Races", [])
    mp: dict[int, float] = {}
    for race in races:
        try:
            rnd = int(race.get("round"))
        except Exception:
            continue
        for res in race.get("SprintResults", []):
            drv = res.get("Driver", {})
            if drv.get("driverId") == driver_id:
                mp[rnd] = float(res.get("points", 0))
                break
    return mp


def count_poles(qual_payload: dict, round_cutoff: int, driver_id: str = DRIVER_ID) -> int:
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
        for q in race.get("QualifyingResults", []):
            drv = q.get("Driver", {})
            if drv.get("driverId") == driver_id and str(q.get("position")) == "1":
                poles += 1
    return poles


def aggregate_from_results(
    results_payload: Dict[str, Any],
    round_cutoff: int,
    sprint_points_by_round: dict[int, float] | None = None,
    driver_id: str = DRIVER_ID
) -> ResultsAggregate:
    mr = results_payload.get("MRData", {})
    race_table = mr.get("RaceTable", {})
    races = race_table.get("Races", [])

    podiums = 0
    dnf = 0
    started = 0
    scored_main = 0
    constructor_id = ""
    last_round_seen = -1
    race_points_by_round: dict[int, float] = {}

    for race in races:
        try:
            rnd = int(race.get("round"))
        except Exception:
            continue
        if rnd > round_cutoff:
            continue

        for res in race.get("Results", []):
            drv = res.get("Driver", {})
            if drv.get("driverId") != driver_id:
                continue
            started += 1
            pos = str(res.get("position", ""))
            pos_text = str(res.get("positionText", ""))
            status = str(res.get("status", ""))
            pts = float(res.get("points", 0))
            if pos in {"1", "2", "3"}:
                podiums += 1
            if _is_retirement(pos_text, status):
                dnf += 1
            if pts > 0:
                scored_main += 1
            race_points_by_round[rnd] = pts

            if rnd >= last_round_seen:
                cons = res.get("Constructor", {})
                constructor_id = cons.get("constructorId", constructor_id)
                last_round_seen = rnd

    # --- agrégats "week-end" (GP + Sprint) ---
    weekend_scored = 0
    zero_point_weekends = 0
    sprint_points_by_round = sprint_points_by_round or {}
    for rnd, gp_pts in race_points_by_round.items():
        total = gp_pts + float(sprint_points_by_round.get(rnd, 0.0))
        if total > 0:
            weekend_scored += 1
        else:
            zero_point_weekends += 1

    race_scored_pct_main = (scored_main / started) if started else 0.0
    weekend_scored_pct = (weekend_scored / started) if started else 0.0

    return ResultsAggregate(
        podiums_to_date=podiums,
        dnf_to_date=dnf,
        races_started=started,
        race_scored_pct_main=race_scored_pct_main,
        weekend_scored_pct=weekend_scored_pct,
        zero_point_weekends_to_date=zero_point_weekends,
        constructor_id=constructor_id or "unknown",
    )


@dataclass
class TeammateStats:
    teammate_points_to_date: float
    teammate_gap: float


def teammate_points_at_round(std: StandingsAtRound, constructor_id: str) -> Optional[TeammateStats]:
    if not constructor_id or constructor_id == "unknown":
        return None
    best_team_points = None
    for e in std.standings_entries:
        d = e.get("Driver", {})
        if d.get("driverId") == DRIVER_ID:
            continue
        constructors = e.get("Constructors", [])
        cons_id = constructors[0].get("constructorId") if constructors else None
        if cons_id == constructor_id:
            pts = float(e.get("points", 0))
            if best_team_points is None or pts > best_team_points:
                best_team_points = pts
    if best_team_points is None:
        return None
    gap = std.hamilton_points - float(best_team_points)
    return TeammateStats(teammate_points_to_date=float(best_team_points), teammate_gap=gap)
