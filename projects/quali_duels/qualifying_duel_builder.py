import pandas as pd
import requests


class QualifyingDuelBuilder:
    def __init__(self, season: int, total_rounds: int = 24):
        self.season = season
        self.total_rounds = total_rounds
        self.duels = []

    def time_to_seconds(t):
        try:
            m, s = t.split(":")
            return int(m) * 60 + float(s)
        except ValueError:
            return None

    def fetch_duels_for_all_rounds(self):
        for round_num in range(1, self.total_rounds + 1):
            url = f"https://api.jolpi.ca/ergast/f1/{self.season}/{round_num}/qualifying.json"
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()
            except requests.exceptions.RequestException:
                continue

            data = response.json()
            races = data["MRData"]["RaceTable"].get("Races", [])
            if not races:
                continue

            race = races[0]
            gp_name = race["raceName"]
            gp_date = race["date"]
            results = race.get("QualifyingResults", [])

            records = []
            for result in results:
                driver = result["Driver"]
                constructor = result["Constructor"]
                full_name = f"{driver['givenName'][0]}. {driver['familyName']}"
                team = constructor["name"]
                position = int(result["position"])
                q1 = result.get("Q1")
                q2 = result.get("Q2")
                q3 = result.get("Q3")
                best_time = q3 or q2 or q1

                records.append(
                    {
                        "Grand Prix": gp_name,
                        "Date": gp_date,
                        "Round": round_num,
                        "Team": team,
                        "Driver": full_name,
                        "Position": position,
                        "Q1": q1,
                        "Q2": q2,
                        "Q3": q3,
                        "Best Time": best_time,
                    }
                )

            df = pd.DataFrame(records)

            for team, group in df.groupby("Team"):
                if len(group) == 2:
                    p1, p2 = group.iloc[0], group.iloc[1]
                    t1 = self.time_to_seconds(p1["Best Time"])
                    t2 = self.time_to_seconds(p2["Best Time"])

                    if t1 is not None and t2 is not None:
                        gap = round(abs(t1 - t2), 3)
                        winner = p1["Driver"] if t1 < t2 else p2["Driver"]
                    else:
                        gap = None
                        winner = "N/A"

                    self.duels.append(
                        {
                            "Grand Prix": gp_name,
                            "Date": gp_date,
                            "Round": round_num,
                            "Team": team,
                            "Driver A": p1["Driver"],
                            "Position A": p1["Position"],
                            "Q3 A": p1["Q3"],
                            "Driver B": p2["Driver"],
                            "Position B": p2["Position"],
                            "Q3 B": p2["Q3"],
                            "Winner": winner,
                            "Gap (s)": gap,
                        }
                    )

    def to_dataframe(self):
        return pd.DataFrame(self.duels)

    def export_csv(self, filepath="qualifying_duels_2025.csv"):
        df = self.to_dataframe()
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        print(f"✅ Exported to {filepath}")
        print(df)
