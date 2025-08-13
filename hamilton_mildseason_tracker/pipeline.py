from __future__ import annotations

import logging
from typing import List, Optional

from .compute import (
    ResultsAggregate,
    StandingsAtRound,
    TeammateStats,
    aggregate_from_results,
    count_poles,
    parse_standings_payload,
    teammate_points_at_round,
    # on n'a plus besoin de build_sprint_points_map ici
)
from .config import DRIVER_ID, SEASON_END, SEASON_START
from .ergast_jolpica import ErgastClient
from .export import YearRecord, write_csv, write_json
from .schedule import CutoffInfo, find_round_cutoff


def _extract_driver_points_from_standings_payload(payload: dict, driver_id: str) -> float:
    """Retourne les points cumulés du driver dans le payload driverStandings donné."""
    mr = payload.get("MRData", {})
    st_table = mr.get("StandingsTable", {})
    lists = st_table.get("StandingsLists", [])
    if not lists:
        return 0.0
    entries = lists[0].get("DriverStandings", []) or []
    for e in entries:
        d = e.get("Driver", {}) or {}
        if d.get("driverId") == driver_id:
            try:
                return float(e.get("points", 0.0))
            except Exception:
                return 0.0
    return 0.0


def _compute_weekend_zero_via_standings(
    client: ErgastClient, year: int, cutoff_round: int, driver_id: str
) -> tuple[int, float]:
    """
    Calcule:
      - nb de week-ends à 0 point (GP + Sprint) jusqu'à cutoff,
      - % de week-ends scorés = (rounds avec delta_points > 0) / (rounds effectivement disputés)

    Méthode: on prend les 'driverStandings' à chaque round r (1..cutoff),
    et on regarde le delta de points entre r-1 et r pour le driver.
    Si delta == 0 => week-end à 0 point.

    Remarque: on normalise par le nb de rounds 'disputés' = nb de rounds pour lesquels
    le pilote apparaît dans les 'Results' (déjà calculé dans res_aggr.races_started),
    pour rester cohérent avec nos autres métriques.
    """
    prev_points = 0.0
    zero_weekends = 0
    scored_weekends = 0

    for r in range(1, cutoff_round + 1):
        payload_r = client.get_driver_standings_at(year, r)
        cur_points = _extract_driver_points_from_standings_payload(payload_r, driver_id)
        delta = cur_points - prev_points
        # tolérance flottante
        if delta > 1e-9:
            scored_weekends += 1
        else:
            zero_weekends += 1
        prev_points = cur_points

    return zero_weekends, scored_weekends  # on renvoie les comptes bruts


def build_year_record(
    year: int,
    cutoff: CutoffInfo,
    standings: StandingsAtRound,
    res: ResultsAggregate,
    poles: int,
    team_stats: Optional[TeammateStats],
    zero_point_weekends_to_date: int,
    weekend_scored_pct: float,
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
        # compat ascendant : on conserve l'ancien champ (points en course principale)
        races_scored_pct=res.race_scored_pct_main,
        # nouveaux champs (version robuste via standings)
        race_scored_pct_main=res.race_scored_pct_main,
        weekend_scored_pct=weekend_scored_pct,
        zero_point_weekends_to_date=zero_point_weekends_to_date,
        constructor_id=res.constructor_id,
        teammate_points_to_date=(team_stats.teammate_points_to_date if team_stats else None),
        teammate_gap=(team_stats.teammate_gap if team_stats else None),
    )


def run_pipeline(year_start: int = SEASON_START, year_end: int = SEASON_END) -> List[YearRecord]:
    client = ErgastClient()
    out: List[YearRecord] = []

    for year in range(year_start, year_end + 1):
        try:
            cutoff = find_round_cutoff(year, client=client)
        except Exception as exc:
            logging.error("[%s] Erreur calcul cutoff: %s", year, exc)
            continue

        try:
            standings_payload = client.get_driver_standings_at(year, cutoff.round)
            standings = parse_standings_payload(standings_payload)
        except Exception as exc:
            logging.error("[%s] Erreur standings@R: %s", year, exc)
            continue

        try:
            results_payload = client.get_season_results(year, limit=1000, offset=0)
            # On calcule les agrégats 'course principale' (podiums, DNF, % scorés en course)
            res_aggr = aggregate_from_results(results_payload, cutoff.round, sprint_points_by_round=None, driver_id=DRIVER_ID)
        except Exception as exc:
            logging.error("[%s] Erreur results: %s", year, exc)
            continue

        try:
            # Pôles (qualifying)
            qual_payload = client.get_qualifying(year, limit=1000, offset=0)
            poles = count_poles(qual_payload, cutoff.round, driver_id=DRIVER_ID)
        except Exception as exc:
            logging.warning("[%s] Qualifying indisponible: %s", year, exc)
            poles = 0

        # === NOUVEAU: Comptage robuste des week-ends à 0 point via deltas standings ===
        try:
            zero_weekends, scored_weekends = _compute_weekend_zero_via_standings(client, year, cutoff.round, DRIVER_ID)
            # Denom pour le % = nb de courses réellement disputées (cohérent avec race_scored_pct_main)
            denom = res_aggr.races_started if res_aggr.races_started > 0 else (zero_weekends + scored_weekends)
            weekend_scored_pct = (scored_weekends / denom) if denom else 0.0
            zero_point_weekends_to_date = zero_weekends
        except Exception as exc:
            logging.warning("[%s] Calcul week-ends 0 via standings indisponible: %s", year, exc)
            # fallback: garde ce qu'on avait (au pire 0)
            weekend_scored_pct = getattr(res_aggr, "weekend_scored_pct", res_aggr.race_scored_pct_main)
            zero_point_weekends_to_date = getattr(res_aggr, "zero_point_weekends_to_date", 0)

        team_stats: Optional[TeammateStats] = None
        try:
            team_stats = teammate_points_at_round(standings, res_aggr.constructor_id)
        except Exception as exc:
            logging.warning("[%s] Coéquipier non calculé: %s", year, exc)

        out.append(
            build_year_record(
                year,
                cutoff,
                standings,
                res_aggr,
                poles,
                team_stats,
                zero_point_weekends_to_date=zero_point_weekends_to_date,
                weekend_scored_pct=weekend_scored_pct,
            )
        )

    # Export
    write_csv(out)
    write_json(out)
    return out
