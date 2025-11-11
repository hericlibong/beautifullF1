import fastf1 as ff1
import pandas as pd
import os


class F1FlourishExporter:
    def __init__(self, season, output_csv="f1_2025_full_heatmap.csv"):
        self.season = season
        # Créer le chemin vers le dossier outputs
        self.output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_csv = os.path.join(self.output_dir, output_csv)
        self.schedule = self._get_schedule()
        self.standings = []
        self.df = None
        self.df_heatmap = None

    def _get_schedule(self):
        schedule = ff1.get_event_schedule(self.season, include_testing=False)
        schedule = schedule.copy()  # pour éviter le warning pandas
        schedule["ShortEventName"] = schedule["EventName"].str.replace("Grand Prix", "").str.strip()
        return schedule

    def fetch_results(self):
        # Boucle sur tous les GPs, extrait résultats et infos pilotes
        for _, event in self.schedule.iterrows():
            event_name = event["EventName"]
            round_label = event["ShortEventName"]
            round_number = event["RoundNumber"]
            try:
                race = ff1.get_session(self.season, event_name, "R")
                race.load(laps=False, telemetry=False, weather=False, messages=False)
                sprint_points = {}
                if event.get("EventFormat") == "sprint_qualifying":
                    sprint = ff1.get_session(self.season, event_name, "S")
                    sprint.load(laps=False, telemetry=False, weather=False, messages=False)
                    for _, srow in sprint.results.iterrows():
                        sprint_points[srow["Abbreviation"]] = srow["Points"]
                for _, driver_row in race.results.iterrows():
                    abbreviation = driver_row["Abbreviation"]
                    team = driver_row["TeamName"]
                    driver_name = driver_row["FullName"]
                    points = driver_row["Points"]
                    grid_position = driver_row.get(
                        "GridPosition", driver_row.get("grid_position", None)
                    )
                    finish_position = driver_row.get("Position", None)
                    headshot_url = driver_row.get("HeadshotUrl", None)
                    total_points = points + sprint_points.get(abbreviation, 0)
                    self.standings.append(
                        {
                            "Driver": abbreviation,
                            "DriverName": driver_name,
                            "Team": team,
                            "EventName": round_label,
                            "EventNameFull": event_name,
                            "RoundNumber": round_number,
                            "Points": total_points,
                            "GridPosition": grid_position,
                            "FinishPosition": finish_position,
                            "HeadshotUrl": headshot_url,
                        }
                    )
            except Exception:
                continue  # GP non couru ou data absente

    def build_dataframe(self):
        # Création du DataFrame principal
        self.df = pd.DataFrame(self.standings)
        # Ajout du total points par pilote
        pilot_totals = (
            self.df.groupby("Driver")["Points"]
            .sum()
            .reset_index()
            .rename(columns={"Points": "TotalPoints"})
        )
        self.df = self.df.merge(pilot_totals, on="Driver")
        # Calcul du classement (rank)
        pilot_totals["Rank"] = (
            pilot_totals["TotalPoints"].rank(method="min", ascending=False).astype(int)
        )
        self.df = self.df.merge(pilot_totals[["Driver", "Rank"]], on="Driver")
        # Label texte du rang
        self.df["RankLabel"] = self.df["Rank"].apply(self._rank_to_label)

    def _rank_to_label(self, rank):
        if pd.isna(rank):
            return ""
        rank = int(rank)
        if rank == 1:
            return "1er"
        elif rank == 2:
            return "2e"
        elif rank == 3:
            return "3e"
        else:
            return f"{rank}e"

    def patch_headshots(self):
        # Patch pour Colapinto (et autres si besoin)
        patch_urls = {
            "COL": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/F/FRACOL01_Franco_Colapinto/fracol01.png.transform/1col/image.png"
            # Tu peux en ajouter d'autres ici
        }
        # Cast en str pour patch robustes
        self.df["HeadshotUrl"] = self.df["HeadshotUrl"].astype(str)
        for drv, url in patch_urls.items():
            mask = (self.df["Driver"] == drv) & (
                self.df["HeadshotUrl"].isnull()
                | (self.df["HeadshotUrl"] == "")
                | (self.df["HeadshotUrl"].str.lower() == "none")
                | (self.df["HeadshotUrl"].str.lower() == "nan")
            )
            self.df.loc[mask, "HeadshotUrl"] = url

    def finalize_dataframe(self):
        # Prépare le DataFrame final pour Flourish
        df = self.df.copy()
        # Ordre des pilotes (classement) et GPs (calendrier)
        pilot_order = (
            df.groupby("Driver")["TotalPoints"].mean().sort_values(ascending=False).index.tolist()
        )
        df["Driver"] = pd.Categorical(df["Driver"], categories=pilot_order, ordered=True)
        gp_order = self.schedule.sort_values("RoundNumber")["ShortEventName"].tolist()
        df["EventName"] = pd.Categorical(df["EventName"], categories=gp_order, ordered=True)
        # Cast des scores/rangs/positions en int (gestion nan)
        for col in ["TotalPoints", "GridPosition", "FinishPosition", "Rank"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(pd.Int64Dtype())
        # Colonnes finales pour Flourish
        self.df_heatmap = df[
            [
                "Driver",
                "DriverName",
                "Team",
                "EventName",
                "EventNameFull",
                "Points",
                "TotalPoints",
                "Rank",
                "RankLabel",
                "HeadshotUrl",
                "GridPosition",
                "FinishPosition",
            ]
        ].sort_values(["Driver", "EventName"])

    def export(self):
        # Export CSV final
        self.df_heatmap.to_csv(self.output_csv, index=False)
        print(f"Exported to {self.output_csv}")
