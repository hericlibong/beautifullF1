import fastf1  # noqa: I001
import pandas as pd
from datetime import datetime

# fastf1.Cache.enable_cache("cache")  # cache local


class RaceChartBuilderFastF1:
    def __init__(self, season: int, output_file: str = "f1_race_chart_fastf1.csv"):
        self.season = season
        self.output_file = output_file
        self.drivers_data = {}
        self.race_keys = []

    @staticmethod
    def _col_name(country: str, locality: str) -> str:
        # même logique que ta version API (USA/Italy dédoublés)
        return f"{country} - {locality}" if country in ["USA", "Italy"] else country

    def build_results_table(self):
        schedule = fastf1.get_event_schedule(self.season)

        # 1) On collecte d'abord toutes les courses PASSÉES avec leurs données + date réelle de la session Race
        past_events_payload = []  # liste de tuples (race_date, round, col_name, race_results_df, sprint_points_dict)

        for _, event in schedule.iterrows():
            # ignorer les évènements futurs (basé sur la date d'évènement prévue)
            if event["EventDate"].to_pydatetime() > datetime.now():
                continue

            round_no = int(event["RoundNumber"])
            col_name = self._col_name(event["Country"], event["Location"])

            # Charger la session de course; si pas de résultats, on saute
            try:
                race = fastf1.get_session(self.season, round_no, "Race")
                race.load()
                if race.results is None or len(race.results) == 0:
                    continue
            except Exception:
                continue

            race_date = pd.to_datetime(race.date)  # date réelle de la session Race (horodatée) 

            # Sprint optionnel
            sprint_points = {}
            try:
                sprint = fastf1.get_session(self.season, round_no, "Sprint")
                sprint.load()
                if sprint.results is not None and len(sprint.results) > 0:
                    for _, row in sprint.results.iterrows():
                        # HeadshotUrl, FullName, TeamName/Colour dispo via results/driver_info 
                        sprint_points[row.FullName] = float(row.Points or 0.0)
            except Exception:
                pass

            past_events_payload.append(
                (race_date, round_no, col_name, race.results.copy(), sprint_points)
            )

        # 2) TRIER par date réelle de la course (ordre effectif des GP)
        past_events_payload.sort(key=lambda x: x[0])

        # 3) Construire le cumul dans cet ordre
        for idx, (race_date, round_no, col_name, race_results, sprint_points) in enumerate(past_events_payload):
            self.race_keys.append(col_name)

            # cumuler les points (Race + Sprint éventuel)
            for _, row in race_results.iterrows():
                full_name = row.FullName
                team = row.TeamName
                image = getattr(row, "HeadshotUrl", "") or ""  # présent via driver_info/Session.results 
                race_pts = float(row.Points or 0.0)
                total_pts = race_pts + float(sprint_points.get(full_name, 0.0))

                if full_name not in self.drivers_data:
                    self.drivers_data[full_name] = {
                        "Pilote": full_name,
                        "image": image,
                        "team": team,
                        "start": 0
                    }
                    # initialiser toutes les colonnes passées à 0
                    for past in self.race_keys:
                        self.drivers_data[full_name][past] = 0

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

        # Top 4 au dernier GP couru
        last_gp = self.race_keys[-1]
        df = df.sort_values(by=last_gp, ascending=False).head(4)

        df.to_csv(self.output_file, index=False, encoding="utf-8-sig")
        print(f"\n✅ Fichier exporté : {self.output_file}")
        print(df)


if __name__ == "__main__":
    builder = RaceChartBuilderFastF1(season=2025)
    builder.build_results_table()
    builder.export_csv()
