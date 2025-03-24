from urllib.request import urlopen
import json

# Create a session object
response = urlopen('https://api.openf1.org/v1/sessions?date_start>2025-01-01')
data = json.loads(response.read().decode('utf-8'))

# Sort data by 'date_start' in ascending order
sorted_data = sorted(data, key=lambda x: x.get('date_start', ''))
print(sorted_data)
