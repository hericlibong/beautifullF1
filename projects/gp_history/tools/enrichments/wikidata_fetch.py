# gp_history/tools/enrichments/wikidata_fetch.py
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pandas as pd

try:
    from SPARQLWrapper import JSON, SPARQLWrapper
except ImportError as e:
    raise SystemExit("SPARQLWrapper n'est pas installé. Fais: pip install sparqlwrapper") from e

BASE_DIR = Path(__file__).resolve().parents[2]  # -> gp_history/
DATA_DIR = BASE_DIR / "data"
GP_CSV = DATA_DIR / "gp_history" / "mexican_grand_prix.csv"
OUT_CSV = DATA_DIR / "reference" / "wikidata_query_results.csv"
ENDPOINT = "https://query.wikidata.org/sparql"

# Tu peux forcer/ajouter des noms ici si tu veux (ils seront ajoutés même s'ils ont déjà une image)
ADDITIONAL_NAMES = [
    # "Jim Clark",  # exemple si tu veux forcer un nom
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return s.replace(".", "").strip().lower()


EXCLUDE = {"max verstappen", "lewis hamilton", "carlos sainz jr", "carlos sainz"}


def load_missing_winners() -> list[str]:
    if not GP_CSV.exists():
        raise FileNotFoundError(f"Introuvable: {GP_CSV}")
    df = pd.read_csv(GP_CSV)
    if "Winner" not in df.columns:
        raise ValueError("La colonne 'Winner' est absente du CSV GP")
    # ne retenir que ceux qui n'ont pas d'URL (ou colonne absente)
    has_col = "WinnerImageURL" in df.columns
    if has_col:
        df = df[df["WinnerImageURL"].isna() | (df["WinnerImageURL"] == "")]
    winners = df["Winner"].dropna().astype(str).drop_duplicates().sort_values().tolist()
    winners = [w for w in winners if _norm(w) not in EXCLUDE]
    # + ajouts forcés éventuels
    for n in ADDITIONAL_NAMES:
        if n not in winners:
            winners.append(n)
    return winners


def build_values_block(names: list[str]) -> str:
    # échappe les guillemets
    def esc(s):
        return s.replace('"', '\\"')

    return " ".join(f'"{esc(n)}"' for n in names)


def build_query(names: list[str]) -> str:
    values = build_values_block(names)
    return f"""SELECT ?inputName ?item ?itemLabel ?image ?enwiki
WHERE {{
  VALUES ?inputName {{ {values} }}

  SERVICE wikibase:mwapi {{
    bd:serviceParam wikibase:endpoint "www.wikidata.org";
                    wikibase:api "EntitySearch";
                    mwapi:search ?inputName;
                    mwapi:language "en".
    ?item wikibase:apiOutputItem mwapi:item.
    ?rank wikibase:apiOrdinal true.
  }}

  ?item wdt:P31 wd:Q5.
  ?item wdt:P106 ?occ.
  FILTER(?occ IN (wd:Q10841764))

  OPTIONAL {{ ?item wdt:P18 ?image. }}
  OPTIONAL {{
    ?enwiki schema:about ?item ;
            schema:isPartOf <https://en.wikipedia.org/> .
  }}

  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr". }}
}}
ORDER BY ?inputName ?rank
"""


def run_sparql(query: str) -> pd.DataFrame:
    ua = "BeautifullF1-GPHistory/1.0 (https://github.com/hericlibong/beautifullF1)"
    sparql = SPARQLWrapper(ENDPOINT, agent=ua)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    rows = []
    for b in results["results"]["bindings"]:

        def g(k):
            return b[k]["value"] if k in b else None

        rows.append(
            {
                "inputName": g("inputName"),
                "item": g("item"),
                "itemLabel": g("itemLabel"),
                "image": g("image"),
                "enwiki": g("enwiki"),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    names = load_missing_winners()
    if not names:
        print("Aucun nom à interroger (tout est déjà rempli ?)")
        sys.exit(0)
    q = build_query(names)
    df = run_sparql(q)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"✅ SPARQL OK — {len(df)} lignes écrites dans {OUT_CSV}")
