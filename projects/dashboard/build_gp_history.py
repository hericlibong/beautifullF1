"""Builder historique par circuit pour le drill-down du dashboard.

Construit (ou met à jour) la clé `circuitId` dans `docs/data/gp_history.json`
+ copie `web/data/`, à partir de :
  - Jolpica/Ergast  : vainqueur, podium, grille, temps, nationalité, champion
  - f1db            : motoriste par (annee, constructorId)
  - Wikipedia REST  : photo du pilote (par pilote unique)

Lent (APIs multiples, rate-limit) -> lancé MANUELLEMENT par circuit, hors workflow auto.

Exemple :
    python projects/dashboard/build_gp_history.py \
        --circuit catalunya --year-from 1991 --year-to 2025 --label Espagne
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import requests

# Console Windows : éviter UnicodeEncodeError sur les emoji dans les print()
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

UA = {"User-Agent": "BeautifullF1-GPHistory/1.0 (github.com/hericlibong)"}
ERGAST = "https://api.jolpi.ca/ergast/f1"
F1DB_ZIP = "https://github.com/f1db/f1db/releases/latest/download/f1db-json-splitted.zip"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"

HERE = Path(__file__).resolve().parent
DOCS_JSON = HERE.parents[1] / "docs" / "data" / "gp_history.json"
WEB_JSON = HERE / "web" / "data" / "gp_history.json"
CACHE_DIR = HERE / ".cache"

# Nationalité (Ergast, anglais) -> emoji drapeau
NAT_FLAG = {
    "British": "🇬🇧",
    "German": "🇩🇪",
    "French": "🇫🇷",
    "Italian": "🇮🇹",
    "Spanish": "🇪🇸",
    "Finnish": "🇫🇮",
    "Brazilian": "🇧🇷",
    "Dutch": "🇳🇱",
    "Austrian": "🇦🇹",
    "Australian": "🇦🇺",
    "Canadian": "🇨🇦",
    "Mexican": "🇲🇽",
    "American": "🇺🇸",
    "Belgian": "🇧🇪",
    "Swedish": "🇸🇪",
    "Swiss": "🇨🇭",
    "Argentine": "🇦🇷",
    "Colombian": "🇨🇴",
    "Japanese": "🇯🇵",
    "Monegasque": "🇲🇨",
    "Polish": "🇵🇱",
    "Danish": "🇩🇰",
    "Russian": "🇷🇺",
    "Thai": "🇹🇭",
    "New Zealander": "🇳🇿",
    "Portuguese": "🇵🇹",
    "Irish": "🇮🇪",
}


def _get(url: str, tries: int = 5) -> dict:
    """GET Ergast poli : retry exponentiel sur 429/5xx."""
    delay = 2.0
    for attempt in range(tries):
        r = requests.get(url, timeout=30, headers=UA)
        if r.status_code == 200:
            return r.json()["MRData"]
        if r.status_code in (429, 500, 502, 503):
            time.sleep(delay)
            delay *= 2
            continue
        r.raise_for_status()
    raise RuntimeError(f"Echec après {tries} essais : {url}")


def load_engine_map() -> dict:
    """(annee, constructorId f1db) -> motoriste (label). Téléchargé + caché 7 jours."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / "f1db_engines.json"
    if cache.exists() and (time.time() - cache.stat().st_mtime) < 7 * 86400:
        rows = json.loads(cache.read_text(encoding="utf-8"))
    else:
        print("⏬ Téléchargement f1db (moteurs)…")
        blob = requests.get(F1DB_ZIP, timeout=120, headers=UA).content
        z = zipfile.ZipFile(io.BytesIO(blob))
        rows = json.loads(z.read("f1db-seasons-entrants-engines.json"))
        # labels lisibles des motoristes
        mans = json.loads(z.read("f1db-engine-manufacturers.json"))
        labels = {m["id"]: m["name"] for m in mans}
        for row in rows:
            row["_label"] = labels.get(row["engineManufacturerId"], row["engineManufacturerId"])
        cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return {(r["year"], r["constructorId"]): r.get("_label") for r in rows}


def engine_for(emap: dict, year: int, ergast_cid: str) -> str | None:
    return emap.get((year, ergast_cid.replace("_", "-")))


def driver_photo(wiki_url: str, cache: dict) -> str | None:
    """Photo via résumé Wikipedia (thumbnail). 1 appel par pilote, caché en session."""
    title = wiki_url.rsplit("/", 1)[-1]
    if title in cache:
        return cache[title]
    photo = None
    try:
        r = requests.get(WIKI_SUMMARY + title, timeout=20, headers=UA)
        if r.status_code == 200:
            photo = (r.json().get("thumbnail") or {}).get("source")
    except requests.RequestException:
        pass
    cache[title] = photo
    return photo


def build_circuit(circuit: str, year_from: int, year_to: int, label: str) -> dict:
    emap = load_engine_map()
    photo_cache: dict[str, str | None] = {}

    # 1 appel : tous les podiums (P1-P3) du circuit, toutes éditions confondues
    races = _get(f"{ERGAST}/circuits/{circuit}/results/1.json?limit=100")["RaceTable"]["Races"]
    print(f"  {len(races)} éditions trouvées pour '{circuit}'")

    editions = []
    champ_cache: dict[int, str] = {}

    for race in races:
        year = int(race["season"])
        if year < year_from or year > year_to:
            continue

        # podium complet (P1-P3) pour cette édition
        time.sleep(0.6)
        full = _get(f"{ERGAST}/{year}/circuits/{circuit}/results.json?limit=10")
        results = full["RaceTable"]["Races"][0]["Results"]
        win = results[0]
        podium = [f"{r['Driver']['givenName']} {r['Driver']['familyName']}" for r in results[:3]]

        # poleman : qualifs si dispo (1994+), sinon grille==1
        poleman, pole_time = None, None
        time.sleep(0.6)
        ql = _get(f"{ERGAST}/{year}/circuits/{circuit}/qualifying.json?limit=1")["RaceTable"][
            "Races"
        ]
        if ql and ql[0].get("QualifyingResults"):
            q = ql[0]["QualifyingResults"][0]
            poleman = f"{q['Driver']['givenName']} {q['Driver']['familyName']}"
            pole_time = q.get("Q3") or q.get("Q2") or q.get("Q1")
        else:
            p1 = next((r for r in results if r["grid"] == "1"), None)
            if p1:
                poleman = f"{p1['Driver']['givenName']} {p1['Driver']['familyName']}"

        # champion de la saison (caché par année)
        if year not in champ_cache:
            time.sleep(0.6)
            st = _get(f"{ERGAST}/{year}/driverStandings/1.json")["StandingsTable"]["StandingsLists"]
            if st:
                c = st[0]["DriverStandings"][0]["Driver"]
                champ_cache[year] = f"{c['givenName']} {c['familyName']}"
        champion = champ_cache.get(year)

        nat = win["Driver"]["nationality"]
        editions.append(
            {
                "year": year,
                "winner": f"{win['Driver']['givenName']} {win['Driver']['familyName']}",
                "flag": NAT_FLAG.get(nat, ""),
                "nationality": nat,
                "team": win["Constructor"]["name"],
                "teamId": win["Constructor"]["constructorId"],
                "engine": engine_for(emap, year, win["Constructor"]["constructorId"]),
                "grid": int(win["grid"]) if win["grid"].isdigit() else None,
                "raceTime": (win.get("Time") or {}).get("time"),
                "poleman": poleman,
                "poleTime": pole_time,
                "podium": podium,
                "champion": champion,
                "photo": driver_photo(win["Driver"]["url"], photo_cache),
            }
        )
        print(
            f"    {year}  {editions[-1]['winner']:<22} {editions[-1]['team']:<14} {editions[-1]['engine']}"
        )

    editions.sort(key=lambda e: e["year"])

    # Calcul des totaux (Y du scatter) : victoires pilote + victoires écurie sur le circuit
    driver_wins: dict[str, int] = {}
    team_wins: dict[str, int] = {}
    for e in editions:
        driver_wins[e["winner"]] = driver_wins.get(e["winner"], 0) + 1
        team_wins[e["team"]] = team_wins.get(e["team"], 0) + 1
    for e in editions:
        e["driverWins"] = driver_wins[e["winner"]]
        e["teamWins"] = team_wins[e["team"]]

    return {
        "circuitId": circuit,
        "circuitName": races[0]["Circuit"]["circuitName"] if races else circuit,
        "gpLabel": label,
        "yearFrom": year_from,
        "yearTo": year_to,
        "editions": editions,
    }


def merge_write(circuit: str, payload: dict) -> None:
    """Read-merge-write de la clé circuit dans gp_history.json (docs/ + web/)."""
    for target in (DOCS_JSON, WEB_JSON):
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if target.exists():
            data = json.loads(target.read_text(encoding="utf-8"))
        data[circuit] = payload
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ {target.relative_to(HERE.parents[1])} ({len(payload['editions'])} éditions)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Builder historique par circuit (scatter chronologie)")
    ap.add_argument("--circuit", required=True, help="circuitId Ergast (ex: catalunya)")
    ap.add_argument("--year-from", type=int, required=True)
    ap.add_argument("--year-to", type=int, required=True)
    ap.add_argument("--label", required=True, help="libellé affiché du GP (ex: Espagne)")
    args = ap.parse_args()

    payload = build_circuit(args.circuit, args.year_from, args.year_to, args.label)
    merge_write(args.circuit, payload)


if __name__ == "__main__":
    main()
