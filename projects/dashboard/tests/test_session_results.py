"""Rejoue les pannes Austin : résultats vides et sprint perdu silencieusement."""

from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
import session_results as sr

from projects.race_chart_builder import race_chart_builder_fastf1 as rc


def results(points=25):
    return pd.DataFrame(
        [
            dict(
                FullName="Max Verstappen",
                Abbreviation="VER",
                TeamName="Red Bull Racing",
                Points=points,
                Position=1,
            )
        ]
    )


def test_empty_result_is_retried_without_telemetry(monkeypatch):
    empty = SimpleNamespace(results=pd.DataFrame(), load=Mock())
    good = SimpleNamespace(results=results(), load=Mock())
    get_session = Mock(side_effect=[empty, good])
    monkeypatch.setattr(sr.fastf1, "get_session", get_session)
    monkeypatch.setattr(sr.time, "sleep", Mock())
    assert sr.load_results(2026, 18, "Race") is good
    good.load.assert_called_once_with(laps=False, telemetry=False, weather=False, messages=False)
    assert get_session.call_count == 2


@pytest.mark.parametrize("points", [float("nan"), float("inf"), -1, 0])
def test_incomplete_points_block_publication(monkeypatch, points):
    session = SimpleNamespace(results=results(points), load=Mock())
    monkeypatch.setattr(sr.fastf1, "get_session", Mock(return_value=session))
    with pytest.raises(RuntimeError, match="round 18"):
        sr.load_results(2026, 18, "Race", attempts=1)


def test_missing_sprint_cannot_be_published_as_zero(tmp_path, monkeypatch):
    schedule = pd.DataFrame(
        [
            dict(
                RoundNumber=17,
                Country="Singapore",
                Location="Marina Bay",
                EventName="Singapore Grand Prix",
                EventFormat="sprint_qualifying",
                Session5DateUtc=pd.Timestamp("2026-10-11T12:00:00"),
            )
        ]
    )
    monkeypatch.setattr(rc.fastf1, "get_event_schedule", Mock(return_value=schedule))
    race = SimpleNamespace(results=results())
    monkeypatch.setattr(rc, "load_results", Mock(side_effect=[race, RuntimeError("sprint absent")]))
    builder = rc.RaceChartBuilderFastF1(2026)
    builder.output_file = str(tmp_path / "race.csv")
    with pytest.raises(RuntimeError, match="sprint absent"):
        builder.build_results_table()
    assert not (tmp_path / "race.csv").exists()
