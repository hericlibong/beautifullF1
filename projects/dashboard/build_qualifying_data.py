"""Construit qualifying_2026.json : duels en qualif entre coéquipiers.

Pour chaque GP joué de la saison, charge la session Qualifying via FastF1 et
calcule, pour chaque paire de coéquipiers :
    - le pilote qui a placé le meilleur temps,
    - le gap (en secondes) entre les deux,
    - le compteur Q3 sur la saison.

Le "temps de référence" d'un pilote = son meilleur temps (Q3 si disponible,
sinon Q2, sinon Q1), c'est-à-dire le temps qui a déterminé sa position.

Sorties :
    projects/dashboard/web/data/qualifying_2026.json
    docs/data/qualifying_2026.json

Lance :
    python projects/dashboard/build_qualifying_data.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import fastf1
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# Nommage des écuries partagé avec les autres builders.
if str(ROOT / "projects") not in sys.path:
    sys.path.insert(0, str(ROOT / "projects"))

from team_naming import canonical_team  # noqa: E402

CALENDAR_PATH = HERE / "calendar_2026.json"
RACE_CHART_CSV = (
    ROOT / "projects" / "race_chart_builder" / "web" / "data" / "f1_race_chart_fastf1_2026.csv"
)
DRIVER_IMAGES_PATH = HERE / "driver_images.json"
OUT_WEB = HERE / "web" / "data" / "qualifying_2026.json"
OUT_DOCS = ROOT / "docs" / "data" / "qualifying_2026.json"

SEASON = 2026


def to_seconds(td) -> float | None:
    """Convertit un Timedelta pandas (ou NaT) en secondes float."""
    if td is None or pd.isna(td):
        return None
    return float(td.total_seconds())


def format_lap(seconds: float | None) -> str | None:
    """1:15.234 ou 65.234 pour les très courts."""
    if seconds is None:
        return None
    minutes = int(seconds // 60)
    secs = seconds - minutes * 60
    if minutes:
        return f"{minutes}:{secs:06.3f}"
    return f"{secs:.3f}"


def best_time_for_driver(row: pd.Series) -> tuple[float | None, bool]:
    """Retourne (meilleur temps en secondes, a_atteint_Q3)."""
    q3 = to_seconds(row.get("Q3"))
    q2 = to_seconds(row.get("Q2"))
    q1 = to_seconds(row.get("Q1"))
    best = next((t for t in (q3, q2, q1) if t is not None), None)
    return best, q3 is not None


def load_display_names() -> dict[str, str]:
    """Table { abréviation FIA : nom affiché par le dashboard }.

    FastF1 ne renvoie pas un nom de pilote stable d'une session à l'autre : les
    Q donnent "Andrea Kimi Antonelli" là où les SQ donnent "Kimi Antonelli",
    "Nico Hülkenberg" alterne avec "Nico Hulkenberg". Sans normalisation, le
    même pilote compte pour deux dans les duels coéquipiers et l'écurie se
    retrouve avec trois pilotes. L'abréviation FIA, elle, est stable.

    Le nom retenu est celui du CSV race chart (ce que le classement affiche),
    relié à l'abréviation via l'URL de photo de driver_images.json ; à défaut,
    le nom de driver_images.json.
    """
    try:
        images = json.loads(DRIVER_IMAGES_PATH.read_text(encoding="utf-8")).get("drivers", {})
    except (OSError, json.JSONDecodeError):
        return {}

    names_by_image: dict[str, str] = {}
    try:
        df = pd.read_csv(RACE_CHART_CSV, encoding="utf-8-sig")
        for _, row in df.iterrows():
            image = str(row.get("image", "") or "")
            if image:
                names_by_image[image] = str(row["Pilote"])
    except (OSError, pd.errors.ParserError, KeyError):
        pass

    out: dict[str, str] = {}
    for abbr, info in images.items():
        image = info.get("image", "")
        out[abbr] = names_by_image.get(image) or info.get("name", "")
    return {k: v for k, v in out.items() if v}


def load_round_session(
    year: int,
    round_no: int,
    session_code: str,
    label: str = "",
    display_names: dict[str, str] | None = None,
) -> list[dict] | None:
    """Charge une session ('Q' ou 'SQ') et retourne la liste pilotes avec leur temps de référence.

    Le GP est désigné par son NUMÉRO DE ROUND, jamais par son nom : FastF1 fait
    un fuzzy match sur les noms, et "Spain" y désigne le Spanish Grand Prix,
    c'est-à-dire Madrid (round 14) — pas Barcelone (round 7). Passer le nom
    ramenait donc les qualifs du mauvais GP espagnol.

    Pour SQ, Ergast n'a pas les données : on utilise le meilleur tour de chaque pilote
    via session.laps (donc on charge les laps dans ce cas-là).
    """
    label = label or f"round {round_no}"
    needs_laps = session_code == "SQ"
    try:
        session = fastf1.get_session(year, round_no, session_code)
        session.load(laps=needs_laps, telemetry=False, weather=False, messages=False)
    except Exception as e:
        print(f"  [SKIP {label} {session_code}] impossible de charger : {e}", file=sys.stderr)
        return None

    results = session.results
    if results is None or results.empty:
        return None

    # Pour SQ, on calcule le meilleur temps par pilote depuis les laps
    best_lap_by_driver = {}
    if needs_laps and session.laps is not None and not session.laps.empty:
        for drv, grp in session.laps.groupby("Driver"):
            fastest = grp.pick_fastest()
            if fastest is not None and not pd.isna(fastest.get("LapTime")):
                best_lap_by_driver[str(drv)] = to_seconds(fastest["LapTime"])

    display_names = display_names or {}
    out = []
    for _, row in results.iterrows():
        abbr = str(row.get("Abbreviation", ""))
        if session_code == "Q":
            best, did_q3 = best_time_for_driver(row)
        else:
            # SQ : meilleur tour via les laps, indexé par Abbreviation (DriverCode)
            best = best_lap_by_driver.get(abbr)
            did_q3 = False  # Q3 ne s'applique qu'aux Q régulières
        raw_name = f"{row.get('FirstName','').strip()} {row.get('LastName','').strip()}".strip()
        out.append(
            {
                "fullName": display_names.get(abbr, raw_name),
                "abbr": abbr,
                "team": canonical_team(row.get("TeamName", "")),
                "position": int(row["Position"]) if not pd.isna(row.get("Position")) else None,
                "bestTimeSec": best,
                "bestTimeStr": format_lap(best),
                "q3": did_q3,
            }
        )
    return out


def load_calendar() -> dict:
    return json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))


def load_previous_sessions() -> dict[tuple[int, str], dict]:
    """Retourne les sessions du fichier existant, indexées par (round, type).

    Sert de fallback : si un chargement FastF1 échoue au run courant mais
    qu'on avait déjà la session, on la préserve au lieu d'écraser avec du vide.
    """
    if not OUT_WEB.exists():
        return {}
    try:
        prev = json.loads(OUT_WEB.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[tuple[int, str], dict] = {}
    for s in prev.get("sessions", []):
        try:
            out[(int(s["round"]), s["type"])] = s
        except (KeyError, TypeError, ValueError):
            continue
    return out


def load_played_gp_names() -> list[str]:
    """Liste des GP déjà courus, lue depuis le CSV race_chart (col names hors meta)."""
    META = {"Pilote", "image", "team", "start"}
    df = pd.read_csv(RACE_CHART_CSV, encoding="utf-8-sig")
    return [c for c in df.columns if c not in META]


def normalize_session(session: dict, display_names: dict[str, str]) -> dict:
    """Réapplique le nommage canonique pilote/écurie à une session déjà stockée."""
    drivers = []
    for d in session.get("drivers", []):
        drivers.append(
            {
                **d,
                "fullName": display_names.get(d.get("abbr", ""), d.get("fullName", "")),
                "team": canonical_team(d.get("team", "")),
            }
        )
    return {**session, "drivers": drivers}


def current_pair(items: list[tuple[dict, list[dict]]]) -> list[str]:
    """Duo courant d'une écurie : les 2 pilotes du dernier GP où elle en alignait 2.

    Retourne les deux noms triés par ordre alphabétique (le front s'appuie sur
    cet ordre pour fixer les côtés A/B de la timeline), ou [] si l'écurie n'a
    jamais aligné exactement deux pilotes.
    """
    for meta, drvs in sorted(items, key=lambda it: (it[0]["round"], it[0]["type"]), reverse=True):
        if len(drvs) == 2:
            return sorted(d["fullName"] for d in drvs)
    return []


def build_teammate_pairs(sessions_data: list[dict]) -> list[dict]:
    """Pour chaque écurie, agrège les duels coéquipier sur Q + SQ.

    Entrée : liste de dicts { round, gp, shortName, type ('Q'|'SQ'), drivers: [...] }
    """
    # team -> list[(session_meta, drivers_in_session)]
    by_team = defaultdict(list)
    for s in sessions_data:
        team_map = defaultdict(list)
        for d in s["drivers"]:
            if d["team"]:
                team_map[d["team"]].append(d)
        for team, drvs in team_map.items():
            by_team[team].append((s, drvs))

    teams_out = []
    for team, items in by_team.items():
        # Paire de référence = le dernier duo aligné par l'écurie, pas l'union de
        # tous les pilotes vus. Un transfert en cours de saison (Lawson chez Red
        # Bull à Zandvoort, Tsunoda chez Racing Bulls) faisait sinon apparaître
        # trois pilotes, et le front n'en affichait que les deux premiers par
        # ordre alphabétique — donc un duel qui n'a jamais eu lieu.
        names = current_pair(items)
        if not names:
            continue

        h2h = {"Q": defaultdict(int), "SQ": defaultdict(int)}
        q3_count = defaultdict(int)
        sessions_out = []

        for meta, drvs in items:
            stype = meta["type"]
            # Compteur Q3 (sessions Q uniquement — Q3 n'existe pas en SQ)
            if stype == "Q":
                for d in drvs:
                    if d["q3"] and d["fullName"] in names:
                        q3_count[d["fullName"]] += 1

            # Duel : exactement 2 pilotes du team, deux temps présents
            if (
                len(drvs) == 2
                and drvs[0]["bestTimeSec"] is not None
                and drvs[1]["bestTimeSec"] is not None
            ):
                d0, d1 = drvs[0], drvs[1]
                # On normalise par ordre alpha pour stabiliser timeA / timeB
                if d0["fullName"] not in names or d1["fullName"] not in names:
                    continue
                if names.index(d0["fullName"]) > names.index(d1["fullName"]):
                    d0, d1 = d1, d0
                # Sécurité : ne traite que les 2 pilotes "titulaires"
                if d0["fullName"] != names[0] or d1["fullName"] != names[1]:
                    continue
                tA = d0["bestTimeSec"]
                tB = d1["bestTimeSec"]
                fastest = d0["fullName"] if tA < tB else d1["fullName"]
                gap = abs(tA - tB)
                h2h[stype][fastest] += 1
                sessions_out.append(
                    {
                        "round": meta["round"],
                        "gp": meta["gp"],
                        "shortName": meta["shortName"],
                        "type": stype,
                        "fastest": fastest,
                        "gapSec": round(gap, 3),
                        "timeA": d0["bestTimeStr"],
                        "timeB": d1["bestTimeStr"],
                        "posA": d0["position"],
                        "posB": d1["position"],
                    }
                )

        teams_out.append(
            {
                "team": team,
                "drivers": names,
                "h2h": {k: dict(v) for k, v in h2h.items()},
                "q3Count": dict(q3_count),
                "sessions": sessions_out,
            }
        )
    return teams_out


def main() -> int:
    cal = load_calendar()
    played = set(load_played_gp_names())
    rounds_in_scope = [r for r in cal["rounds"] if r["name"] in played]
    print(f"[INFO] {len(rounds_in_scope)} GP joués détectés")

    previous_sessions = load_previous_sessions()
    display_names = load_display_names()

    def append_or_fallback(sessions_data: list, meta: dict, drivers: list | None) -> None:
        """Ajoute la session ou, si le chargement a échoué, réutilise la précédente."""
        stype = meta["type"]
        rnd = meta["round"]
        if drivers is not None:
            sessions_data.append({**meta, "drivers": drivers})
            return
        fallback = previous_sessions.get((rnd, stype))
        if fallback is not None:
            print(
                f"  [FALLBACK {meta['shortName']} {stype}] chargement échoué — "
                f"préservation de la session précédente",
                file=sys.stderr,
            )
            # La session préservée a pu être écrite avant la normalisation :
            # on la repasse au même moule que les sessions fraîches.
            sessions_data.append(normalize_session(fallback, display_names))
        else:
            print(
                f"  [MISS {meta['shortName']} {stype}] chargement échoué et aucune donnée antérieure",
                file=sys.stderr,
            )

    sessions_data: list[dict] = []
    for r in rounds_in_scope:
        is_sprint = bool(r.get("isSprint", False))
        meta_q = {
            "round": r["round"],
            "gp": r["name"],
            "shortName": r["shortName"],
            "type": "Q",
        }
        # Session principale : Qualifying
        print(f"  - {r['shortName']} (Q)")
        append_or_fallback(
            sessions_data,
            meta_q,
            load_round_session(SEASON, r["round"], "Q", r["shortName"], display_names),
        )
        # Sprint Qualifying (uniquement week-ends sprint)
        if is_sprint:
            meta_sq = {**meta_q, "type": "SQ"}
            print(f"  - {r['shortName']} (SQ)")
            append_or_fallback(
                sessions_data,
                meta_sq,
                load_round_session(SEASON, r["round"], "SQ", r["shortName"], display_names),
            )

    teammates = build_teammate_pairs(sessions_data)

    payload = {
        "season": SEASON,
        "generatedAt": date.today().isoformat(),
        "sessions": sessions_data,
        "teammates": teammates,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    for target in (OUT_WEB, OUT_DOCS):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print(f"[OK] {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
