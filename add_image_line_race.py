import requests
import pandas as pd

# === CONFIGURATION ===
MEETING_KEY = 1255  # Assure-toi que ce meeting contient tous les pilotes
CSV_FILE_IN = "f1_race_chart_results.csv"
CSV_FILE_OUT = "f1_race_chart_avec_images.csv"

# === 1. Récupérer les données pilotes depuis OpenF1 ===
url = f"https://api.openf1.org/v1/drivers?meeting_key={MEETING_KEY}"
response = requests.get(url)
drivers_openf1 = response.json()

# Créer un mapping : {driver_number: headshot_url}
photo_map = {}
for driver in drivers_openf1:
    number = driver.get("driver_number")
    image_url = driver.get("headshot_url", "")
    if number and image_url:
        photo_map[int(number)] = image_url

# === 2. Charger le fichier CSV existant (généré depuis jolpi.ca) ===
df = pd.read_csv(CSV_FILE_IN)

# === 3. Injection des images ===
# Astuce : extraire le numéro à partir de l’ordre dans la course d’ouverture (optionnel)
# OU créer ton propre mapping manuellement si besoin

# On fait correspondre par le nom s'il n'y a pas de numéro, mais ici on simplifie

# Boucle sur chaque pilote du fichier
for i, row in df.iterrows():
    name = row["Pilote"]
    # Tentative de correspondance : initiale + nom = full_name en OpenF1
    last_name = name.split(". ")[-1].upper()
    match = None

    for d in drivers_openf1:
        if d["last_name"].upper() == last_name:
            match = d
            break

    if match:
        df.at[i, "image"] = match.get("headshot_url", "")

# === 4. Exporter le fichier avec images ===
df.to_csv(CSV_FILE_OUT, index=False, encoding='utf-8-sig')
print(f"✅ Images ajoutées dans : {CSV_FILE_OUT}")
print(df)
