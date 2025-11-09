import os  # noqa: F401
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest  # noqa: F401

from season_summary_heatmap.exporter import F1FlourishExporter


def test_init_with_valid_season():
    """Tests correct initialization of F1FlourishExporter with a valid season."""
    exporter = F1FlourishExporter(season=2023, output_csv="dummy.csv")
    # Basic attributes
    assert exporter.season == 2023
    assert exporter.output_csv == "dummy.csv"
    assert isinstance(exporter.schedule, object)
    assert exporter.standings == []
    assert exporter.df is None
    assert exporter.df_heatmap is None
    # Expected columns in the schedule
    for col in ["EventName", "ShortEventName", "RoundNumber"]:
        assert col in exporter.schedule.columns


def test_init_with_invalid_season():
    """Test that F1FlourishExporter initializes correctly with an invalid season."""
    exporter = F1FlourishExporter(season=2099)
    # The attribute must exist even if the schedule is empty
    assert hasattr(exporter, "schedule")
    # Empty or very partial DataFrame
    assert len(exporter.schedule) == 0 or "EventName" in exporter.schedule.columns
    assert exporter.standings == []
    assert exporter.df is None
    assert exporter.df_heatmap is None


def test_get_schedule_structure():
    """Test that the schedule structure is a non-empty DataFrame with required columns for a given season."""
    exporter = F1FlourishExporter(season=2023)
    schedule = exporter._get_schedule()
    # Check the type
    assert isinstance(schedule, pd.DataFrame)
    # Essential columns
    expected_cols = {"EventName", "ShortEventName", "RoundNumber"}
    assert expected_cols.issubset(schedule.columns)
    # The schedule should not be empty for a known season (unless the API is down)
    assert len(schedule) > 0


@patch("season_summary_heatmap.exporter.ff1.get_event_schedule")
@patch("season_summary_heatmap.exporter.ff1.get_session")
def test_fetch_results_full_season(
    mock_get_session, mock_get_event_schedule, fake_race, fake_event_schedule
):
    mock_get_event_schedule.return_value = fake_event_schedule
    mock_get_session.return_value = fake_race

    exporter = F1FlourishExporter(season=2023)
    exporter.fetch_results()

    assert len(exporter.standings) == 2
    assert exporter.standings[0]["Driver"] == "VER"


@patch("season_summary_heatmap.exporter.ff1.get_event_schedule")
@patch("season_summary_heatmap.exporter.ff1.get_session")
def test_fetch_results_with_missing_gp(
    mock_get_session, mock_get_event_schedule, fake_race, fake_event_schedule
):
    # We simulate two GPs: the first works, the second raises an exception
    mock_get_event_schedule.return_value = fake_event_schedule._append(
        {
            "EventName": "Imola Grand Prix",
            "ShortEventName": "Imola",
            "RoundNumber": 2,
            "EventFormat": "conventional",
        },
        ignore_index=True,
    )

    def session_side_effect(season, event_name, session_type):
        if event_name == "Bahrain Grand Prix":
            return fake_race
        else:
            raise Exception("No data for this GP")

    mock_get_session.side_effect = session_side_effect

    exporter = F1FlourishExporter(season=2023)
    exporter.fetch_results()
    # Only the first GP produced results (2 drivers)
    assert len(exporter.standings) == 2
    assert all(s["EventNameFull"] == "Bahrain Grand Prix" for s in exporter.standings)


@patch("season_summary_heatmap.exporter.ff1.get_event_schedule")
@patch("season_summary_heatmap.exporter.ff1.get_session")
def test_fetch_results_sprint_points(
    mock_get_session, mock_get_event_schedule, fake_results, fake_event_schedule
):
    # We convert the GP to "sprint_qualifying"
    event_schedule = fake_event_schedule.copy()
    event_schedule.at[0, "EventFormat"] = "sprint_qualifying"
    mock_get_event_schedule.return_value = event_schedule

    # We create a sprint session and a race session
    fake_sprint = MagicMock()
    fake_sprint.results = pd.DataFrame(
        [{"Abbreviation": "VER", "Points": 8}, {"Abbreviation": "HAM", "Points": 7}]
    )
    fake_sprint.load = MagicMock()

    fake_race = MagicMock()
    fake_race.results = fake_results
    fake_race.load = MagicMock()

    # Depending on the session type, return sprint or race
    def session_side_effect(season, event_name, session_type):
        if session_type == "S":
            return fake_sprint
        return fake_race

    mock_get_session.side_effect = session_side_effect

    exporter = F1FlourishExporter(season=2023)
    exporter.fetch_results()
    ver = [s for s in exporter.standings if s["Driver"] == "VER"][0]
    ham = [s for s in exporter.standings if s["Driver"] == "HAM"][0]
    assert ver["Points"] == 25 + 8
    assert ham["Points"] == 18 + 7


def test_build_dataframe_basic(fake_results):
    # Simule un exporter déjà alimenté
    exporter = F1FlourishExporter(season=2023)
    exporter.standings = [
        {
            "Driver": "VER",
            "DriverName": "Max Verstappen",
            "Team": "Red Bull",
            "EventName": "Bahrain",
            "EventNameFull": "Bahrain Grand Prix",
            "RoundNumber": 1,
            "Points": 25,
            "GridPosition": 1,
            "FinishPosition": 1,
            "HeadshotUrl": "ver.png",
        },
        {
            "Driver": "HAM",
            "DriverName": "Lewis Hamilton",
            "Team": "Mercedes",
            "EventName": "Bahrain",
            "EventNameFull": "Bahrain Grand Prix",
            "RoundNumber": 1,
            "Points": 18,
            "GridPosition": 2,
            "FinishPosition": 2,
            "HeadshotUrl": None,
        },
        {
            "Driver": "VER",
            "DriverName": "Max Verstappen",
            "Team": "Red Bull",
            "EventName": "Jeddah",
            "EventNameFull": "Saudi Arabian Grand Prix",
            "RoundNumber": 2,
            "Points": 26,
            "GridPosition": 1,
            "FinishPosition": 1,
            "HeadshotUrl": "ver.png",
        },
        {
            "Driver": "HAM",
            "DriverName": "Lewis Hamilton",
            "Team": "Mercedes",
            "EventName": "Jeddah",
            "EventNameFull": "Saudi Arabian Grand Prix",
            "RoundNumber": 2,
            "Points": 15,
            "GridPosition": 3,
            "FinishPosition": 2,
            "HeadshotUrl": None,
        },
    ]
    exporter.build_dataframe()
    df = exporter.df
    # Vérifie la présence des colonnes essentielles
    expected_cols = {
        "Driver",
        "DriverName",
        "Team",
        "EventName",
        "Points",
        "TotalPoints",
        "Rank",
        "RankLabel",
    }
    assert expected_cols.issubset(df.columns)
    # Vérifie la cohérence des totaux par pilote
    ver_points = df[df["Driver"] == "VER"]["TotalPoints"].iloc[0]
    ham_points = df[df["Driver"] == "HAM"]["TotalPoints"].iloc[0]
    assert ver_points == 25 + 26
    assert ham_points == 18 + 15
    # Le classement doit être correct : VER > HAM
    ver_rank = df[df["Driver"] == "VER"]["Rank"].iloc[0]
    ham_rank = df[df["Driver"] == "HAM"]["Rank"].iloc[0]
    assert ver_rank < ham_rank


def test_rank_to_label_variants():
    exporter = F1FlourishExporter(season=2023)
    # 1 -> "1er"
    assert exporter._rank_to_label(1) == "1er"
    # 2 -> "2e"
    assert exporter._rank_to_label(2) == "2e"
    # 3 -> "3e"
    assert exporter._rank_to_label(3) == "3e"
    # 5 -> "5e"
    assert exporter._rank_to_label(5) == "5e"
    # NaN -> ""
    import numpy as np

    assert exporter._rank_to_label(np.nan) == ""


def test_patch_headshots_patch_COL_variants():
    exporter = F1FlourishExporter(season=2023)
    # Simule la df avec valeurs à patcher
    exporter.df = pd.DataFrame(
        [
            {"Driver": "COL", "HeadshotUrl": None},
            {"Driver": "COL", "HeadshotUrl": ""},
            {"Driver": "COL", "HeadshotUrl": "None"},
            {"Driver": "COL", "HeadshotUrl": "nan"},
        ]
    )
    exporter.patch_headshots()
    # Attendu : toutes les lignes ont la bonne url patchée
    expected_url = "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/F/FRACOL01_Franco_Colapinto/fracol01.png.transform/1col/image.png"
    assert all(exporter.df["HeadshotUrl"] == expected_url)


def test_patch_headshots_no_effect_other_drivers():
    exporter = F1FlourishExporter(season=2023)
    # Simule la df pour un pilote non patché avec une vraie url
    exporter.df = pd.DataFrame(
        [
            {"Driver": "VER", "HeadshotUrl": "https://media.formula1.com/drivers/VER.png"},
            {"Driver": "HAM", "HeadshotUrl": "https://media.formula1.com/drivers/HAM.png"},
        ]
    )
    old_urls = exporter.df["HeadshotUrl"].copy()
    exporter.patch_headshots()
    # Attendu : aucune modification pour VER et HAM
    assert all(exporter.df["HeadshotUrl"] == old_urls)


def test_finalize_dataframe_structure_and_order():
    exporter = F1FlourishExporter(season=2023)
    # Simule une df préparée par build_dataframe
    exporter.df = pd.DataFrame(
        [
            {
                "Driver": "VER",
                "DriverName": "Max Verstappen",
                "Team": "Red Bull",
                "EventName": "Bahrain",
                "EventNameFull": "Bahrain Grand Prix",
                "Points": 25,
                "TotalPoints": 51,
                "Rank": 1,
                "RankLabel": "1er",
                "HeadshotUrl": "ver.png",
                "GridPosition": 1,
                "FinishPosition": 1,
            },
            {
                "Driver": "HAM",
                "DriverName": "Lewis Hamilton",
                "Team": "Mercedes",
                "EventName": "Bahrain",
                "EventNameFull": "Bahrain Grand Prix",
                "Points": 18,
                "TotalPoints": 33,
                "Rank": 2,
                "RankLabel": "2e",
                "HeadshotUrl": "ham.png",
                "GridPosition": 2,
                "FinishPosition": 2,
            },
            {
                "Driver": "VER",
                "DriverName": "Max Verstappen",
                "Team": "Red Bull",
                "EventName": "Jeddah",
                "EventNameFull": "Saudi Arabian Grand Prix",
                "Points": 26,
                "TotalPoints": 51,
                "Rank": 1,
                "RankLabel": "1er",
                "HeadshotUrl": "ver.png",
                "GridPosition": 1,
                "FinishPosition": 1,
            },
        ]
    )
    # Mock l’ordre dans schedule
    exporter.schedule = pd.DataFrame(
        [
            {"ShortEventName": "Bahrain", "RoundNumber": 1, "EventName": "Bahrain Grand Prix"},
            {"ShortEventName": "Jeddah", "RoundNumber": 2, "EventName": "Saudi Arabian Grand Prix"},
        ]
    )
    exporter.finalize_dataframe()
    df_heat = exporter.df_heatmap

    # Colonnes attendues dans le bon ordre
    expected_cols = [
        "Driver",
        "DriverName",
        "Team",
        "EventName",
        "EventNameFull",
        "Points",
        "TotalPoints",
        "Rank",
        "RankLabel",
        "HeadshotUrl",
        "GridPosition",
        "FinishPosition",
    ]
    assert list(df_heat.columns) == expected_cols

    # Vérifie le type catégorie
    assert pd.api.types.is_categorical_dtype(df_heat["Driver"])
    assert pd.api.types.is_categorical_dtype(df_heat["EventName"])

    # Vérifie que l’ordre des pilotes est respecté (par points décroissants)
    pilots_order = df_heat["Driver"].cat.categories.tolist()
    assert pilots_order[0] == "VER"  # Plus de points
    assert pilots_order[-1] == "HAM"
    # L’ordre des GP respecte le calendrier
    events_order = df_heat["EventName"].cat.categories.tolist()
    assert events_order == ["Bahrain", "Jeddah"]


def test_finalize_dataframe_nan_and_int_casting():
    exporter = F1FlourishExporter(season=2023)
    # Un pilote sans grid position ni finish position (NaN)
    exporter.df = pd.DataFrame(
        [
            {
                "Driver": "VER",
                "DriverName": "Max Verstappen",
                "Team": "Red Bull",
                "EventName": "Bahrain",
                "EventNameFull": "Bahrain Grand Prix",
                "Points": 25,
                "TotalPoints": 51,
                "Rank": 1,
                "RankLabel": "1er",
                "HeadshotUrl": "ver.png",
                "GridPosition": None,
                "FinishPosition": None,
            }
        ]
    )
    exporter.schedule = pd.DataFrame(
        [{"ShortEventName": "Bahrain", "RoundNumber": 1, "EventName": "Bahrain Grand Prix"}]
    )
    exporter.finalize_dataframe()
    df_heat = exporter.df_heatmap
    # Les colonnes doivent être du bon type, même avec NaN
    assert pd.api.types.is_integer_dtype(df_heat["TotalPoints"])
    assert pd.api.types.is_integer_dtype(df_heat["Rank"])
    assert pd.api.types.is_integer_dtype(df_heat["GridPosition"])
    assert pd.api.types.is_integer_dtype(df_heat["FinishPosition"])
    # Valeur manquante = <NA> (pas 0, pas nan classique)
    assert pd.isna(df_heat["GridPosition"].iloc[0])
    assert pd.isna(df_heat["FinishPosition"].iloc[0])


def test_export_creates_valid_csv(tmp_path):
    exporter = F1FlourishExporter(season=2023, output_csv=tmp_path / "test_flourish.csv")
    # Simule une df_heatmap prête à l’export
    exporter.df_heatmap = pd.DataFrame(
        [
            {
                "Driver": "VER",
                "DriverName": "Max Verstappen",
                "Team": "Red Bull",
                "EventName": "Bahrain",
                "EventNameFull": "Bahrain Grand Prix",
                "Points": 25,
                "TotalPoints": 51,
                "Rank": 1,
                "RankLabel": "1er",
                "HeadshotUrl": "ver.png",
                "GridPosition": 1,
                "FinishPosition": 1,
            },
            {
                "Driver": "HAM",
                "DriverName": "Lewis Hamilton",
                "Team": "Mercedes",
                "EventName": "Bahrain",
                "EventNameFull": "Bahrain Grand Prix",
                "Points": 18,
                "TotalPoints": 33,
                "Rank": 2,
                "RankLabel": "2e",
                "HeadshotUrl": "ham.png",
                "GridPosition": 2,
                "FinishPosition": 2,
            },
        ]
    )
    exporter.export()

    # Vérifie que le fichier existe bien
    output_file = tmp_path / "test_flourish.csv"
    assert output_file.exists()

    # Vérifie le contenu et les colonnes
    df_out = pd.read_csv(output_file)
    expected_cols = [
        "Driver",
        "DriverName",
        "Team",
        "EventName",
        "EventNameFull",
        "Points",
        "TotalPoints",
        "Rank",
        "RankLabel",
        "HeadshotUrl",
        "GridPosition",
        "FinishPosition",
    ]
    assert list(df_out.columns) == expected_cols
    # Vérifie la présence des pilotes
    assert set(df_out["Driver"]) == {"VER", "HAM"}


@patch("season_summary_heatmap.exporter.ff1.get_event_schedule")
@patch("season_summary_heatmap.exporter.ff1.get_session")
def test_pipeline_e2e_full_mocked(mock_get_session, mock_get_event_schedule, tmp_path):
    # 1. Mock calendrier avec deux courses (dont une sprint)
    mock_get_event_schedule.return_value = pd.DataFrame(
        [
            {
                "EventName": "Bahrain Grand Prix",
                "ShortEventName": "Bahrain",
                "RoundNumber": 1,
                "EventFormat": "conventional",
            },
            {
                "EventName": "Baku Grand Prix",
                "ShortEventName": "Baku",
                "RoundNumber": 2,
                "EventFormat": "sprint_qualifying",
            },
        ]
    )

    # 2. Mock résultats course et sprint
    fake_race = MagicMock()
    fake_race.results = pd.DataFrame(
        [
            {
                "Abbreviation": "VER",
                "TeamName": "Red Bull",
                "FullName": "Max Verstappen",
                "Points": 25,
                "GridPosition": 1,
                "Position": 1,
                "HeadshotUrl": "ver.png",
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
    fake_race.load = MagicMock()

    fake_sprint = MagicMock()
    fake_sprint.results = pd.DataFrame(
        [{"Abbreviation": "VER", "Points": 8}, {"Abbreviation": "HAM", "Points": 7}]
    )
    fake_sprint.load = MagicMock()

    # 3. Switch session type : S = sprint, R = course
    def session_side_effect(season, event_name, session_type):
        if event_name == "Baku Grand Prix" and session_type == "S":
            return fake_sprint
        return fake_race

    mock_get_session.side_effect = session_side_effect

    # 4. Pipeline complet
    output_file = tmp_path / "e2e_flourish.csv"
    exporter = F1FlourishExporter(season=2023, output_csv=output_file)
    exporter.fetch_results()
    exporter.build_dataframe()
    exporter.patch_headshots()
    exporter.finalize_dataframe()
    exporter.export()

    # 5. Vérif finale sur le CSV
    df_out = pd.read_csv(output_file)
    # Deux GPs, deux pilotes, sprint points bien additionnés sur Baku
    assert "Baku" in df_out["EventName"].values
    assert df_out.loc[df_out["EventName"] == "Baku", "Points"].tolist() == [25 + 8, 18 + 7]
    # Colonnes attendues
    expected_cols = [
        "Driver",
        "DriverName",
        "Team",
        "EventName",
        "EventNameFull",
        "Points",
        "TotalPoints",
        "Rank",
        "RankLabel",
        "HeadshotUrl",
        "GridPosition",
        "FinishPosition",
    ]
    assert list(df_out.columns) == expected_cols
    # Test global : pas d’exception sur tout le pipeline
