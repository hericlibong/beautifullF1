from urllib.request import urlopen
import json


session_key=9689

response = urlopen(f'https://api.openf1.org/v1/drivers?session_key={session_key}')
drivers_data = json.loads(response.read().decode('utf-8'))
print(list(drivers_data[0].keys()))
for driver in drivers_data:
    print({
        'broadcast_name': driver['broadcast_name'],
        'first_name': driver['first_name'],
        'last_name': driver['last_name'],
        'headshot_url': driver['headshot_url'],
        'driver_number': driver['driver_number'],
        'team_name': driver['team_name'],
        'team_color': driver['team_color'],
    })