from __future__ import annotations

from typing import Any, Dict, Optional

from .config import JOLPICA_BASE_URL
from .http import HttpClient


class ErgastClient:
    """Client Jolpica/Ergast-compatible."""

    def __init__(self, base_url: str = JOLPICA_BASE_URL, http: Optional[HttpClient] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http or HttpClient()

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # ---- Standings ----
    def get_driver_standings_at(self, year: int, round_: int) -> Dict[str, Any]:
        return self.http.get_json(self._url(f"/{year}/{round_}/driverStandings.json"))

    # ---- Results (all season) ----
    def get_season_results(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        return self.http.get_json(self._url(f"/{year}/results.json"), params={"limit": limit, "offset": offset})

    # ---- Qualifying (all season) ----
    def get_qualifying(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        return self.http.get_json(self._url(f"/{year}/qualifying.json"), params={"limit": limit, "offset": offset})

    # ---- Sprint (all season) ----
    def get_sprint_results(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """
        Ergast/Jolpica expose les Sprints via /{year}/sprint.json
        (champs: RaceTable.Races[i].SprintResults[*].points, etc.)
        """
        return self.http.get_json(self._url(f"/{year}/sprint.json"), params={"limit": limit, "offset": offset})

    # ---- Calendar (fallback when FastF1 schedule fails) ----
    def get_season_calendar(self, year: int, limit: int = 1000) -> Dict[str, Any]:
        """
        Ergast endpoint that lists Races with their dates (used to compute summer gap).
        Base already includes /f1; so /{year}.json is correct.
        """
        return self.http.get_json(self._url(f"/{year}.json"), params={"limit": limit})
