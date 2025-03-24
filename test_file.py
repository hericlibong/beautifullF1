import pandas as pd
import requests



url = "https://api.jolpi.ca/ergast/f1/2025/2/results.json"
response = requests.get(url)
response.raise_for_status()
race_data = response.json()
race = race_data['MRData']['RaceTable']['Races'][0]
results = race['Results']
print(results[0]['Driver']['driverId'])
print(results[0]['Driver']['permanentNumber'])
print(results[0]['Constructor']['constructorId'])