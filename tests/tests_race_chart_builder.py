from race_chart_builder.race_chart_builder import normalize_name, F1RaceChartBuilder
from unittest.mock import patch, MagicMock


def test_normalize_name():
    assert normalize_name("Éstéban Ocon") == "esteban ocon"
    assert normalize_name(" Lando   Norris ") == "lando   norris"
    assert normalize_name("Frédéric Vasseur") == "frederic vasseur"


def test_get_fallback_headshot_known():
    # Exact name in the fallback table
    assert F1RaceChartBuilder.get_fallback_headshot("Nico Hulkenberg").startswith("https://")
    assert F1RaceChartBuilder.get_fallback_headshot("Franco Colapinto").startswith("https://")

def test_get_fallback_headshot_unknown():
    # Name not present returns empty string
    assert F1RaceChartBuilder.get_fallback_headshot("Lewis Hamilton") == ""


def test_constructor_initializes_fields():
    builder = F1RaceChartBuilder(2025, 3, 1234)
    assert builder.season == 2025
    assert builder.rounds == 3
    assert builder.meeting_key == 1234
    assert builder.output_file == "f1_race_chart_results.csv"
    # Check that key attributes are initialized as empty
    assert builder.photo_map == {}
    assert builder.sprint_points_by_country == {}
    assert builder.drivers_data == {}
    assert builder.race_keys == []


def test_fetch_sprint_results_simple_mock(fake_sprint_response):
    builder = F1RaceChartBuilder(2025, 1, 123)
    # Uses the fake_sprint_response fixture

    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_sprint_response
        mock_get.return_value = mock_resp

        builder.fetch_sprint_results()

    assert "France" in builder.sprint_points_by_country
    assert builder.sprint_points_by_country["France"]["Pierre Gasly"] == 8.0
