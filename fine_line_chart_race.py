import pandas as pd
import requests
import time
import unicodedata

# === CONFIGURATION ===
season = 2025
rounds_to_checks = 2
output_file = "f1_race_chart_results.csv"
meeting_key_openf1 = 1255

# === 1. RÉCUPÉRER LES PHOTOS PILOTES VIA OPENF1 ===
print("📸 Récupération des images pilotes...")
url = f"https://api.openf1.org/v1/drivers?meeting_key={meeting_key_openf1}"
response = requests.get(url)
drivers_openf1 = response.json()

# Créer un dictionnaire {full_name: headshot_url}
photo_map = {}
for d in drivers_openf1:
    full_name = d["full_name"].title()  # Ex: Max Verstappen
    image_url = d.get("headshot_url", "")
    if full_name and image_url:
        photo_map[full_name] = image_url

# === 2. COLLECTER LES DONNÉES DE COURSES (JOLPI.CA) ===
print("🏁 Récupération des résultats de course...")
drivers_data = {}
race_keys = []

for round in range(1, rounds_to_checks + 1):
    url = f"https://api.jolpi.ca/ergast/f1/{season}/{round}/results.json"
    print(f'Fetching round {round}...')
    try:
        response = requests.get(url)
        response.raise_for_status()
        race_data = response.json()
        race = race_data['MRData']['RaceTable']['Races'][0]
        results = race['Results']
    except (IndexError, KeyError):
        print(f"❌ Pas encore de données pour le round {round}")
        continue

    # Extraire le pays du GP
    country_raw = race['Circuit']['Location']['country']
    country = unicodedata.normalize('NFKD', country_raw).encode('ascii', 'ignore').decode('utf-8')
    race_keys.append(country)

    for result in results:
        driver = result['Driver']
        constructor = result['Constructor']

        full_name = f"{driver['givenName']} {driver['familyName']}".title()
        points = float(result['points'])
        team = constructor['name']
        image = photo_map.get(full_name, "")

        if full_name not in drivers_data:
            drivers_data[full_name] = {
                "Pilote": full_name,
                "image": image,
                "team": team,
                "start": 0,
            }
            for past in race_keys:
                drivers_data[full_name][past] = 0

        if len(race_keys) == 1:
            drivers_data[full_name][country] = points
        else:
            prev = race_keys[-2]
            prev_points = drivers_data[full_name].get(prev, 0)
            drivers_data[full_name][country] = prev_points + points

    for driver in drivers_data.values():
        if country not in driver:
            prev = driver.get(race_keys[-2], 0) if len(race_keys) > 1 else 0
            driver[country] = prev

    time.sleep(1)

# === 3. EXPORT CSV FINAL ===
df = pd.DataFrame.from_dict(drivers_data, orient='index')
df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n✅ Fichier exporté avec images : {output_file}")
print(df)
