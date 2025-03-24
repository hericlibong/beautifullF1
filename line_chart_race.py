import pandas as pd
import requests
import time
import unicodedata


# Configuration
season = 2025
rounds_to_checks = 2
output_file = "f1_race_chart_results.csv"

# Initialize variables
drivers_data = {}
race_keys = []

for round in range(1, rounds_to_checks + 1):
    url = f"https://api.jolpi.ca/ergast/f1/{season}/{round}/results.json"
    print(f'fecthing round {round}...')
    try:
        response = requests.get(url)
        response.raise_for_status()
        race_data = response.json()
        race = race_data['MRData']['RaceTable']['Races'][0]
        results = race['Results']
    except (IndexError, KeyError):
        print(f"Pas de données pour le {round}")
        continue 

    # Extraire le pays
    country_raw = race['Circuit']['Location']['country']
    country = unicodedata.normalize('NFKD', country_raw).encode('ascii', 'ignore').decode('utf-8')
    race_keys.append(country)

    for result in results:
        driver = result['Driver']
        constructor = result['Constructor']

        name = f"{driver['givenName']} {driver['familyName']}"
        points =float(result['points'])
        team = constructor['name']

        if name not in drivers_data:
            drivers_data[name] = {
                "Pilote": name,
                "team": team,
            }
            for past in race_keys:
                drivers_data[name][past] = 0

        if len(race_keys) == 1:
            drivers_data[name][country] = points
        else:
            prev = race_keys[-2]
            prev_points = drivers_data[name].get(prev, 0)
            drivers_data[name][country] = prev_points + points

    for driver in drivers_data.values():
        if country not in driver:
            prev = driver.get(race_keys[-2], 0) if len(race_keys) > 1 else 0
            driver[country] = prev

    time.sleep(1)

# Conversion
df = pd.DataFrame.from_dict(drivers_data, orient='index')
df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(df)

print(f"✅ Fichier exporté : {output_file}")





