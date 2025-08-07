from unittest.mock import MagicMock

import pandas as pd
import pytest


@pytest.fixture
def fake_sprint_response():
    """
    Fixture that returns a simulated Ergast API response for sprint results.

    This fixture provides test data structured according to the Ergast API format
    to simulate the response of a Formula 1 sprint results query.

    Returns:
        dict: A dictionary containing:
            - MRData.RaceTable.Races: List of races with sprint results
            - Circuit.Location: Circuit information (country, locality)
            - SprintResults: List of results with drivers and points

    Example:
        The response includes Pierre Gasly at Le Castellet (France) with 8 points.
    """
    return {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "Circuit": {"Location": {"country": "France", "locality": "Le Castellet"}},
                        "SprintResults": [
                            {
                                "Driver": {"givenName": "Pierre", "familyName": "Gasly"},
                                "points": "8",
                            }
                        ],
                    }
                ]
            }
        }
    }


@pytest.fixture
def fake_results():
    return pd.DataFrame(
        [
            {
                "Abbreviation": "VER",
                "TeamName": "Red Bull",
                "FullName": "Max Verstappen",
                "Points": 25,
                "GridPosition": 1,
                "Position": 1,
                "HeadshotUrl": "url.png",
            },
            {
                "Abbreviation": "HAM",
                "TeamName": "Mercedes",
                "FullName": "Lewis Hamilton",
                "Points": 18,
                "GridPosition": 2,
                "Position": 2,
                "HeadshotUrl": None,
            },
        ]
    )


@pytest.fixture
def fake_race(fake_results):
    mock = MagicMock()
    mock.results = fake_results
    mock.load = MagicMock()
    return mock


@pytest.fixture
def fake_event_schedule():
    return pd.DataFrame(
        [
            {
                "EventName": "Bahrain Grand Prix",
                "ShortEventName": "Bahrain",
                "RoundNumber": 1,
                "EventFormat": "conventional",
            }
        ]
    )
