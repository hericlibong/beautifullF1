import os

import fastf1 as ff1
import pandas as pd

SPRINT_EVENT_FORMATS = {"sprint", "sprint_shootout", "sprint_qualifying"}


class F1FlourishExporterLead:
    """
    Duplication minimale de F1FlourishExporter avec :
      - ajout d'un indicateur Sprint : EventName "*" si Sprint
      - ajout d'un champ FinishIcon (🥇🥈🥉) basé sur FinishPosition
      - conservation de tous les pilotes au classement total
      - colonnes d'analyse pour popups (régularité/forme) SANS impacter la heatmap
    """

    def __init__(self, season, output_csv=None):
        self.season = season
        self.output_csv = output_csv or f"f1_{season}_leaders_heatmap.csv"
        self.output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_path = self._resolve_output_path(self.output_csv)
        self.schedule = self._get_schedule()
        self.standings = []
        self.df = None
        self.df_heatmap = None

    def _resolve_output_path(self, output_csv):
        output_csv = os.fspath(output_csv)
        if os.path.isabs(output_csv):
            return output_csv
        return os.path.join(self.output_dir, output_csv)

    def _get_schedule(self):
        schedule = ff1.get_event_schedule(self.season, include_testing=False)
        schedule = schedule.copy()
        schedule["ShortEventName"] = schedule["EventName"].str.replace("Grand Prix", "").str.strip()
        return schedule

    def _has_sprint(self, event):
        return event.get("EventFormat") in SPRINT_EVENT_FORMATS

    def _finish_icon(self, pos):
        if pd.isna(pos):
            return ""
        try:
            p = int(pos)
        except Exception:
            return ""
        if p == 1:
            return "🥇"
        if p == 2:
            return "🥈"
        if p == 3:
            return "🥉"
        return ""

    def fetch_results(self):
        for _, event in self.schedule.iterrows():
            event_name = event["EventName"]
            has_sprint = self._has_sprint(event)
            round_label = event["ShortEventName"] + ("*" if has_sprint else "")
            round_number = event["RoundNumber"]

            try:
                race = ff1.get_session(self.season, event_name, "R")
                race.load(laps=False, telemetry=False, weather=False, messages=False)

                sprint_points_map = {}
                if has_sprint:
                    sprint = ff1.get_session(self.season, event_name, "S")
                    sprint.load(laps=False, telemetry=False, weather=False, messages=False)
                    for _, srow in sprint.results.iterrows():
                        sprint_points_map[srow["Abbreviation"]] = srow["Points"]

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
                    sprint_pts = sprint_points_map.get(abbreviation, 0)

                    total_points = points + sprint_pts

                    self.standings.append(
                        {
                            "Driver": abbreviation,
                            "DriverName": driver_name,
                            "Team": team,
                            "EventName": round_label,  # label court (+ "*" si Sprint)
                            "EventNameFull": event_name,
                            "RoundNumber": round_number,
                            "Points": total_points,  # Course + Sprint éventuel
                            "SprintPoints": sprint_pts,  # <-- nouveau (pour tooltip)
                            "GridPosition": grid_position,
                            "FinishPosition": finish_position,
                            "FinishIcon": self._finish_icon(finish_position),
                            "HeadshotUrl": headshot_url,
                        }
                    )
            except Exception:
                continue  # GP non couru ou data absente

    def build_dataframe(self):
        self.df = pd.DataFrame(self.standings)

        # Totaux par pilote
        pilot_totals = (
            self.df.groupby("Driver")["Points"]
            .sum()
            .reset_index()
            .rename(columns={"Points": "TotalPoints"})
        )
        self.df = self.df.merge(pilot_totals, on="Driver")

        # Rang global
        pilot_totals["Rank"] = (
            pilot_totals["TotalPoints"].rank(method="min", ascending=False).astype(int)
        )
        self.df = self.df.merge(pilot_totals[["Driver", "Rank"]], on="Driver")

        # Label de rang
        self.df["RankLabel"] = self._rank_to_label_series(self.df["Rank"])

    def _rank_to_label_series(self, s):
        def f(rank):
            if pd.isna(rank):
                return ""
            r = int(rank)
            if r == 1:
                return "1er"
            if r == 2:
                return "2e"
            if r == 3:
                return "3e"
            if r <= 21:
                return f"{r}e"
            return f"{r}e"

        return s.apply(f)

    def patch_headshots(self):
        patch_urls = {
            "COL": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/F/FRACOL01_Franco_Colapinto/fracol01.png.transform/1col/image.png"
        }
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
        df = self.df.copy()

        # --- Tous les pilotes (pas de filtre) ---
        # FastF1 fournit la grille via race.results, sans hypothèse sur le nombre de pilotes.

        # Ordre des pilotes
        pilot_order = (
            df.groupby("Driver")["TotalPoints"].mean().sort_values(ascending=False).index.tolist()
        )
        df["Driver"] = pd.Categorical(df["Driver"], categories=pilot_order, ordered=True)

        # Ordre des GP (avec "*" si Sprint)
        gp_order = []
        for _, ev in self.schedule.sort_values("RoundNumber").iterrows():
            label = ev["ShortEventName"] + ("*" if self._has_sprint(ev) else "")
            gp_order.append(label)
        df["EventName"] = pd.Categorical(df["EventName"], categories=gp_order, ordered=True)

        # Cast numériques de base
        for col in [
            "TotalPoints",
            "GridPosition",
            "FinishPosition",
            "Rank",
            "Points",
            "SprintPoints",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # --- Colonnes d'analyse pour popups (cumulées / glissantes), par pilote en ordre de round ---
        df = df.sort_values(["Driver", "EventName"])  # EventName est catégoriel ordonné

        # GridGain (ligne à ligne)
        df["GridGain"] = (df["GridPosition"] - df["FinishPosition"]).where(
            df["GridPosition"].notna() & df["FinishPosition"].notna()
        )

        # Par pilote : cumul, moyenne cumulée, rolling 5
        g = df.groupby("Driver", group_keys=False)

        df["CumulativePoints"] = g["Points"].cumsum()
        # nombre de GP disputés à date = cumcount + 1
        df["_gp_count"] = g.cumcount() + 1
        df["AvgPointsToDate"] = df["CumulativePoints"] / df["_gp_count"]

        # moyenne glissante 5 derniers GP (min_periods=1)
        df["Last5Avg"] = (
            g["Points"].rolling(window=5, min_periods=1).mean().reset_index(level=0, drop=True)
        )

        # métriques de position (expanding)
        df["AvgFinish"] = g["FinishPosition"].expanding().mean().reset_index(level=0, drop=True)
        df["MedianFinish"] = (
            g["FinishPosition"].expanding().median().reset_index(level=0, drop=True)
        )

        # taux cumulés
        df["_is_podium"] = (
            (df["FinishPosition"] <= 3).astype("float").where(df["FinishPosition"].notna())
        )
        df["_is_points"] = (df["Points"] > 0).astype("float")

        df["PodiumRate"] = g["_is_podium"].cumsum() / df["_gp_count"]
        df["PointsRate"] = g["_is_points"].cumsum() / df["_gp_count"]

        # moyenne cumulée du gain grille
        df["AvgGridGain"] = g["GridGain"].expanding().mean().reset_index(level=0, drop=True)

        # Nettoyage des colonnes techniques
        df = df.drop(columns=["_gp_count", "_is_podium", "_is_points"])

        # --- Nettoyage d'affichage pour Flourish : entiers "propres"
        int_cols = [
            "TotalPoints",
            "GridPosition",
            "FinishPosition",
            "Rank",
            "Points",
            "SprintPoints",
            "CumulativePoints",
        ]

        for col in int_cols:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: "" if pd.isna(x) else int(round(x)))

        # Cast "soft" (laisse float si nécessaire pour éviter les erreurs)
        # Colonnes finales pour Flourish (ajouts en fin)
        self.df_heatmap = df[
            [
                "Driver",
                "DriverName",
                "Team",
                "EventName",
                "EventNameFull",
                "Points",
                "SprintPoints",
                "TotalPoints",
                "Rank",
                "RankLabel",
                "HeadshotUrl",
                "GridPosition",
                "FinishPosition",
                "FinishIcon",
                "GridGain",
                "CumulativePoints",
                "AvgPointsToDate",
                "Last5Avg",
                "AvgFinish",
                "MedianFinish",
                "PodiumRate",
                "PointsRate",
                "AvgGridGain",
            ]
        ].sort_values(["Driver", "EventName"])

    def export(self):
        self.df_heatmap.to_csv(self.output_path, index=False)
        print(f"Exported to {self.output_path}")
