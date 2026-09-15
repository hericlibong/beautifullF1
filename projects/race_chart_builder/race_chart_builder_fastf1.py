from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

import fastf1
import pandas as pd

# fastf1.Cache.enable_cache("cache")  # cache local

_HERE = os.path.dirname(os.path.abspath(__file__))

# Le nommage des GP est partagé avec le dashboard (projects/gp_naming.py). Ce
# script étant lancé en sous-processus par build_all.py, projects/ n'est pas sur
# sys.path : on l'ajoute avant l'import.
_PROJECTS_DIR = os.path.dirname(_HERE)
if _PROJECTS_DIR not in sys.path:
    sys.path.insert(0, _PROJECTS_DIR)

from gp_naming import check_unique, col_name  # noqa: E402
from team_naming import canonical_team  # noqa: E402

# Mapping fallback des photos pilotes (utilisé quand FastF1 ne fournit pas
# HeadshotUrl, ce qui arrive notamment sur runners Linux / cache vide).
DRIVER_IMAGES_PATH = os.path.join(_HERE, "..", "dashboard", "driver_images.json")

# Colonnes non-GP du CSV : tout le reste est une colonne de Grand Prix.
META_COLUMNS = {"Pilote", "image", "team", "start"}


def load_driver_images_fallback() -> dict[str, str]:
    """Retourne un dict { abbreviation 3 lettres : URL photo }."""
    try:
        with open(DRIVER_IMAGES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {abbr: info.get("image", "") for abbr, info in data.get("drivers", {}).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class RaceChartBuilderFastF1:
    def __init__(
        self,
        season: int,
        output_file: str | None = None,
        top_n: int | None = None,
    ):
        self.season = season
        self.top_n = top_n
        outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        if output_file is None:
            output_file = f"f1_race_chart_fastf1_{season}.csv"
        self.output_file = os.path.join(outputs_dir, output_file)
        self.drivers_data = {}
        self.race_keys = []
        self.failed_rounds: list[tuple[int, str]] = []
        self.driver_images_fallback = load_driver_images_fallback()

    @staticmethod
    def _col_name(country: str, locality: str) -> str:
        # Délègue à projects/gp_naming.py : les colonnes de ce CSV servent de
        # clés au calendrier du dashboard, les deux doivent suivre la même règle.
        return col_name(country, locality)

    def _load_race_with_retry(self, round_no: int, col_name: str, attempts: int = 3):
        """Charge la session Race d'un round, avec retry exponentiel.

        Retourne la session chargée, ou None si tous les essais ont échoué.
        Les échecs sont journalisés : un GP qui disparaît silencieusement fausse
        tout le cumul en aval (dashboard, duels qualif), le bruit est voulu.
        """
        for attempt in range(1, attempts + 1):
            try:
                race = fastf1.get_session(self.season, round_no, "Race")
                race.load()
                if race.results is None or len(race.results) == 0:
                    raise ValueError("résultats vides")
                return race
            except Exception as exc:  # noqa: BLE001 - on veut tout retenter
                print(
                    f"[!] round {round_no} ({col_name}) : echec {attempt}/{attempts} - {exc}",
                    file=sys.stderr,
                )
                if attempt < attempts:
                    time.sleep(2**attempt)
        return None

    def _existing_race_columns(self) -> list[str]:
        """Colonnes de GP présentes dans le CSV déjà écrit (vide s'il n'existe pas)."""
        if not os.path.exists(self.output_file):
            return []
        try:
            with open(self.output_file, encoding="utf-8-sig", newline="") as f:
                header = next(csv.reader(f))
        except (OSError, StopIteration):
            return []
        return [c for c in header if c not in META_COLUMNS]

    def _assert_no_regression(self) -> None:
        """Interdit d'écrire un CSV qui perdrait un GP déjà publié.

        Le CSV est reconstruit intégralement à chaque run : une session
        momentanément indisponible côté FastF1 (ce qui est arrivé à Spa lors du
        refresh post-Madrid) supprimait la colonne du GP et retirait ses points
        du cumul de tous les pilotes. Mieux vaut échouer et garder le fichier
        précédent que publier un classement faux.
        """
        missing = [c for c in self._existing_race_columns() if c not in self.race_keys]
        if not missing:
            return
        details = ", ".join(f"round {r} ({n})" for r, n in self.failed_rounds) or "aucun"
        raise SystemExit(
            "[ECHEC] Le CSV regenere perdrait des GP deja publies : "
            f"{', '.join(missing)}.\n"
            f"        Sessions non chargees ce run : {details}.\n"
            "        Fichier existant conserve, rien n'a ete ecrit."
        )

    def build_results_table(self):
        schedule = fastf1.get_event_schedule(self.season)

        # 1) On collecte d'abord toutes les courses PASSÉES avec leurs données + date réelle de la session Race
        past_events_payload = (
            []
        )  # liste de tuples (race_date, round, col_name, race_results_df, sprint_points_dict)

        from datetime import timezone

        for _, event in schedule.iterrows():
            # 1️⃣ Identifier la date réelle de la course (session Race)
            race_date = event.get("Session5DateUtc", None)
            if pd.isna(race_date):
                continue
            race_date = pd.to_datetime(race_date).to_pydatetime().replace(tzinfo=timezone.utc)

            # 2️⃣ Si la course n’a pas encore eu lieu → on saute
            if race_date > datetime.now(timezone.utc):
                continue

            round_no = int(event["RoundNumber"])
            col_name = self._col_name(event["Country"], event["Location"])

            # Un GP passé qui n'a pas pu être chargé n'est PAS "pas encore
            # couru" : on retente, puis on le mémorise pour que export_csv()
            # refuse d'écrire un CSV amputé (cf. _assert_no_regression).
            race = self._load_race_with_retry(round_no, col_name)
            if race is None:
                self.failed_rounds.append((round_no, col_name))
                continue

            # On garde la même logique ensuite
            sprint_points = {}
            try:
                sprint = fastf1.get_session(self.season, round_no, "Sprint")
                sprint.load()
                if sprint.results is not None and len(sprint.results) > 0:
                    for _, row in sprint.results.iterrows():
                        sprint_points[row.FullName] = float(row.Points or 0.0)
            except Exception:
                pass

            past_events_payload.append(
                (race_date, round_no, col_name, race.results.copy(), sprint_points)
            )

        # 2) TRIER par date réelle de la course (ordre effectif des GP)
        past_events_payload.sort(key=lambda x: x[0])

        # Garde-fou : un GP = une colonne. Sans ça, deux GP d'un même pays
        # (Barcelone et Madrid en 2026) écraseraient mutuellement leur cumul et
        # l'un des deux ne serait jamais marqué comme disputé côté dashboard.
        check_unique([p[2] for p in past_events_payload], context="le CSV race chart")

        # 3) Construire le cumul dans cet ordre
        for idx, (race_date, round_no, col_name, race_results, sprint_points) in enumerate(
            past_events_payload
        ):
            self.race_keys.append(col_name)

            # cumuler les points (Race + Sprint éventuel)
            for _, row in race_results.iterrows():
                full_name = row.FullName
                team = canonical_team(row.TeamName)
                # 1) HeadshotUrl FastF1 si fourni (cas idéal)
                # 2) sinon fallback via driver_images.json (par abréviation FIA)
                # 3) sinon chaîne vide (comportement historique)
                image = getattr(row, "HeadshotUrl", "") or ""
                if not image:
                    abbr = getattr(row, "Abbreviation", "") or ""
                    image = self.driver_images_fallback.get(abbr, "")
                race_pts = float(row.Points or 0.0)
                total_pts = race_pts + float(sprint_points.get(full_name, 0.0))

                if full_name not in self.drivers_data:
                    self.drivers_data[full_name] = {
                        "Pilote": full_name,
                        "image": image,
                        "team": team,
                        "start": 0,
                    }
                    # initialiser toutes les colonnes passées à 0
                    for past in self.race_keys:
                        self.drivers_data[full_name][past] = 0
                else:
                    # Les GP sont parcourus dans l'ordre : l'écurie du dernier GP
                    # couru fait foi. Sans ça, un pilote transféré en cours de
                    # saison (Lawson → Red Bull à Zandvoort) resterait affiché
                    # sous son écurie de début d'année.
                    self.drivers_data[full_name]["team"] = team
                    if image:
                        self.drivers_data[full_name]["image"] = image

                # cumul
                if idx == 0:
                    self.drivers_data[full_name][col_name] = total_pts
                else:
                    prev = self.race_keys[-2]
                    prev_points = float(self.drivers_data[full_name].get(prev, 0.0))
                    self.drivers_data[full_name][col_name] = prev_points + total_pts

            # compléter pour les pilotes absents à cette course
            for d in self.drivers_data.values():
                if col_name not in d:
                    prev = d.get(self.race_keys[-2], 0.0) if len(self.race_keys) > 1 else 0.0
                    d[col_name] = prev

    def export_csv(self):
        df = pd.DataFrame.from_dict(self.drivers_data, orient="index")

        if not self.race_keys:
            print("[!] Aucun GP couru detecte - rien a exporter.")
            return

        self._assert_no_regression()

        last_gp = self.race_keys[-1]
        df = df.sort_values(by=last_gp, ascending=False)
        if self.top_n is not None:
            df = df.head(self.top_n)

        df.to_csv(self.output_file, index=False, encoding="utf-8-sig")
        print(f"\n[OK] Fichier exporte : {self.output_file}")
        print(df)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="F1 race chart dataset builder (FastF1).")
    parser.add_argument("--season", type=int, default=2025, help="Saison F1 (ex: 2025, 2026)")
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Garder uniquement les N premiers du classement (par défaut: tous les pilotes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Nom du fichier CSV (défaut: f1_race_chart_fastf1_<season>.csv)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    builder = RaceChartBuilderFastF1(season=args.season, output_file=args.output, top_n=args.top)
    builder.build_results_table()
    builder.export_csv()
