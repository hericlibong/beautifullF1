import json
import time
import unicodedata

import pandas as pd
import requests


def normalize_name(name):
    # Retire accents, espaces et passe en minuscule
    return (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )


class F1RaceChartBuilder:
    def __init__(
        self,
        season: int,
        rounds: int,
        meeting_key: int,
        output_file: str = "f1_race_chart_results.csv",
    ):
        """
        Initialise les paramètres de la saison de F1 à visualiser

        Args:
            season (int): Année de la saison (ex: 2025)
            rounds (int): Nombre de courses à visualiser
            meeting_key (int): Clé de réunion OpenF1 utilisée pour récupérer les images des pilotes
            output_file (str, optional): Nom du fichier de sortie.

        """
        self.season = season
        self.rounds = rounds
        self.meeting_key = meeting_key
        self.output_file = output_file

        # données à remplir par les méthodes suivantes
        self.photo_map = {}  # Dictionnaire des photos des pilotes
        self.sprint_points_by_country = {}
        self.drivers_data = {}  # Dictionnaire principal
        self.race_keys = []  # Liste ordonnée des noms de colonnes GP

    def fetch_sprint_results(self):
        """
        Récupère les points marqués lors des courses sprint (si elles existent)
        et les associe précisément au bon GP (ex: USA - Miami vs USA - Austin)
        en utilisant le même nom de colonne que dans les résultats principaux.
        """
        print("🚀 Récupération des résultats de Sprint...")

        url = f"https://api.jolpi.ca/ergast/f1/{self.season}/sprint.json"
        response = requests.get(url)
        sprint_data = response.json()

        for race in sprint_data["MRData"]["RaceTable"]["Races"]:
            # Extraire pays et ville pour distinguer les GP doublons
            country_raw = race["Circuit"]["Location"]["country"]
            locality_raw = race["Circuit"]["Location"]["locality"]

            country = (
                unicodedata.normalize("NFKD", country_raw).encode("ascii", "ignore").decode("utf-8")
            )
            locality = (
                unicodedata.normalize("NFKD", locality_raw)
                .encode("ascii", "ignore")
                .decode("utf-8")
            )

            # Appliquer la même logique que pour les noms de colonne dans le tableau principal
            if country in ["USA", "Italy"]:
                col_name = f"{country} - {locality}"
            else:
                col_name = country

            results = race.get("SprintResults", [])
            self.sprint_points_by_country[col_name] = {}

            for result in results:
                driver = result["Driver"]
                full_name = f"{driver['givenName']} {driver['familyName']}".title()
                points = float(result.get("points", 0))
                self.sprint_points_by_country[col_name][full_name] = points

    @staticmethod
    def get_fallback_headshot(full_name):
        fallback = {
            "nico hulkenberg": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/N/NICHUL01_Nico_Hulkenberg/nichul01.png.transform/1col/image.png",
            "franco colapinto": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/F/FRACOL01_Franco_Colapinto/fracol01.png.transform/1col/image.png",
        }
        return fallback.get(normalize_name(full_name), "")

    def fetch_driver_images(self):
        """
        Récupère les images des pilotes via l'API OpenF1 (meeting_key requis)
        et stocke les URLs dans self.photo_map avec le nom complet comme clé.
        """
        print("📸 Récupération des images pilotes...")

        url = f"https://api.openf1.org/v1/drivers?meeting_key={self.meeting_key}"
        response = requests.get(url)
        drivers = response.json()

        for d in drivers:
            full_name = d["full_name"].title()
            image_url = d.get("headshot_url", "")
            # Si image_url est vide OU générique OU incomplète
            if (
                not image_url
                or image_url.strip() == ""
                or image_url.endswith("d_driver_fallback_image.png")
            ):
                image_url = self.get_fallback_headshot(full_name)
            if full_name and image_url:
                self.photo_map[full_name] = image_url

    def build_results_table(self):
        """
        Récupère les résultats de chaque Grand Prix et construit
        un tableau complet avec les points cumulés, les images, les teams, etc.
        Les points sprint sont ajoutés si disponibles.
        """
        print("🏁 Récupération des résultats de course...")

        for round in range(1, self.rounds + 1):
            url = f"https://api.jolpi.ca/ergast/f1/{self.season}/{round}/results.json"
            print(f"📦 Fetching round {round}...")
            try:
                response = requests.get(url)
                response.raise_for_status()
                race_data = response.json()
                race = race_data["MRData"]["RaceTable"]["Races"][0]
                results = race["Results"]
            except (IndexError, KeyError):
                print(f"❌ Pas encore de données pour le round {round}")
                continue

            # Identifier GP unique : col_name = "USA - Miami" ou "Australia"
            country_raw = race["Circuit"]["Location"]["country"]
            locality_raw = race["Circuit"]["Location"]["locality"]
            country = (
                unicodedata.normalize("NFKD", country_raw).encode("ascii", "ignore").decode("utf-8")
            )
            locality = (
                unicodedata.normalize("NFKD", locality_raw)
                .encode("ascii", "ignore")
                .decode("utf-8")
            )
            col_name = f"{country} - {locality}" if country in ["USA", "Italy"] else country

            self.race_keys.append(col_name)

            for result in results:
                driver = result["Driver"]
                constructor = result["Constructor"]
                full_name = f"{driver['givenName']} {driver['familyName']}".title()
                points = float(result["points"])

                # Ajouter les points sprint si disponibles
                sprint_points = self.sprint_points_by_country.get(col_name, {}).get(full_name, 0)
                points += sprint_points

                team = constructor["name"]
                # image = self.photo_map.get(full_name, "")
                image = self.photo_map.get(full_name, "") or self.get_fallback_headshot(full_name)

                if full_name not in self.drivers_data:
                    self.drivers_data[full_name] = {
                        "Pilote": full_name,
                        "image": image,
                        "team": team,
                        "start": 0,
                    }
                    for past in self.race_keys:
                        self.drivers_data[full_name][past] = 0

                # Mise à jour du score pour ce GP
                if len(self.race_keys) == 1:
                    self.drivers_data[full_name][col_name] = points
                else:
                    prev = self.race_keys[-2]
                    prev_points = self.drivers_data[full_name].get(prev, 0)
                    self.drivers_data[full_name][col_name] = prev_points + points

            # Ajouter le GP avec le même score que le précédent pour les pilotes absents
            for driver in self.drivers_data.values():
                if col_name not in driver:
                    prev = driver.get(self.race_keys[-2], 0) if len(self.race_keys) > 1 else 0
                    driver[col_name] = prev

            time.sleep(1)

    def export_csv(self):
        """
        Exporte le tableau des pilotes vers un fichier CSV, prêt à être utilisé dans Flourish.
        """
        df = pd.DataFrame.from_dict(self.drivers_data, orient="index")
        df.to_csv(self.output_file, index=False, encoding="utf-8-sig")

        print(f"\n✅ Fichier exporté : {self.output_file}")
        print(df)

        # export au format JSON
        json_file = self.output_file.replace(".csv", ".json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.drivers_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Fichier exporté : {json_file}")
