import pytest

@pytest.fixture
def fake_sprint_response():
    return {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "Circuit": {
                            "Location": {
                                "country": "France",
                                "locality": "Le Castellet"
                            }
                        },
                        "SprintResults": [
                            {
                                "Driver": {
                                    "givenName": "Pierre",
                                    "familyName": "Gasly"
                                },
                                "points": "8"
                            }
                        ]
                    }
                ]
            }
        }
    }
