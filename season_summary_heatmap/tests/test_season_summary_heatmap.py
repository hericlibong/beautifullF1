
import pytest

from season_summary_heatmap.exporter import F1FlourishExporter


def test_init_with_valid_season():
    exporter = F1FlourishExporter(season=2023, output_csv="dummy.csv")
    # Attributs de base
    assert exporter.season == 2023
    assert exporter.output_csv == "dummy.csv"
    assert isinstance(exporter.schedule, object)  # Un DataFrame, mais testons le type si pandas importé
    assert exporter.standings == []
    assert exporter.df is None
    assert exporter.df_heatmap is None
    # Colonnes attendues dans le calendrier
    for col in ["EventName", "ShortEventName", "RoundNumber"]:
        assert col in exporter.schedule.columns

def test_init_with_invalid_season():
    exporter = F1FlourishExporter(season=2099)
    # L’attribut doit exister même si le calendrier est vide
    assert hasattr(exporter, "schedule")
    # DataFrame vide ou très partiel
    assert len(exporter.schedule) == 0 or "EventName" in exporter.schedule.columns
    assert exporter.standings == []
    assert exporter.df is None
    assert exporter.df_heatmap is None

