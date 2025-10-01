# from __future__ import annotations

# from typing import Any, Dict, Optional

# from .config import JOLPICA_BASE_URL
# from .http import HttpClient


# class ErgastClient:
#     """Client Jolpica/Ergast-compatible."""

#     def __init__(self, base_url: str = JOLPICA_BASE_URL, http: Optional[HttpClient] = None) -> None:
#         self.base_url = base_url.rstrip("/")
#         self.http = http or HttpClient()

#     def _url(self, path: str) -> str:
#         return f"{self.base_url}{path}"

#     # ---- Standings ----
#     def get_driver_standings_at(self, year: int, round_: int) -> Dict[str, Any]:
#         return self.http.get_json(self._url(f"/{year}/{round_}/driverStandings.json"))

#     # ---- Results (all season) ----
#     def get_season_results(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
#         return self.http.get_json(self._url(f"/{year}/results.json"), params={"limit": limit, "offset": offset})

#     # ---- Qualifying (all season) ----
#     def get_qualifying(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
#         return self.http.get_json(self._url(f"/{year}/qualifying.json"), params={"limit": limit, "offset": offset})

#     # ---- Sprint (all season) ----
#     def get_sprint_results(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
#         """
#         Ergast/Jolpica expose les Sprints via /{year}/sprint.json
#         (champs: RaceTable.Races[i].SprintResults[*].points, etc.)
#         """
#         return self.http.get_json(self._url(f"/{year}/sprint.json"), params={"limit": limit, "offset": offset})

#     # ---- Calendar (fallback when FastF1 schedule fails) ----
#     def get_season_calendar(self, year: int, limit: int = 1000) -> Dict[str, Any]:
#         """
#         Ergast endpoint that lists Races with their dates (used to compute summer gap).
#         Base already includes /f1; so /{year}.json is correct.
#         """
#         return self.http.get_json(self._url(f"/{year}.json"), params={"limit": limit})

# hamilton_mildseason_tracker/ergast_jolpica.py
# hamilton_mildseason_tracker/ergast_jolpica.py
from __future__ import annotations

import random
import time
from typing import Any, Dict, Optional

import requests
import requests_cache  # <= cache HTTP léger

from .config import JOLPICA_BASE_URL


class ErgastClient:
    """
    Client Jolpica/Ergast minimaliste:
    - Session cache via requests_cache (évite de refrapper l'API au 2e run)
    - Pacing doux entre requêtes
    - Retry court ciblé sur 429 uniquement
    """

    def __init__(
        self,
        base_url: str = JOLPICA_BASE_URL,
        timeout: int = 20,
        rate_limit_delay: float = 1.0,   # délai anti-429 après chaque appel
        cache_expire_seconds: int = 86400  # 24h; mets 604800 (=7j) si tu veux
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay

        # Cache SQLite (fichier .ergast_cache.sqlite) pour toutes les requêtes HTTP
        self.session = requests_cache.CachedSession(
            cache_name=".ergast_cache",
            backend="sqlite",
            expire_after=cache_expire_seconds
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # 3 tentatives max, retry seulement si 429
        last_exc: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                # Si la réponse vient du cache, pas de pacing, on renvoie direct
                from_cache = getattr(resp, "from_cache", False)

                if resp.status_code == 429:
                    # backoff simple + jitter
                    sleep_s = (self.rate_limit_delay * (attempt ** 2)) + random.uniform(0.15, 0.45)
                    time.sleep(sleep_s)
                    continue

                resp.raise_for_status()

                # Pacing léger uniquement si ce n'est pas du cache
                if not from_cache and self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

                return resp.json()

            except requests.HTTPError as exc:
                last_exc = exc
                # autres codes HTTP: on ne retry pas agressivement
                break
            except Exception as exc:
                # erreurs réseau ponctuelles: on retente une fois
                last_exc = exc
                time.sleep(0.5)

        raise RuntimeError(f"HTTP error for {url} (params={params}): {last_exc}")

    # ---- Standings à un round donné ----
    def get_driver_standings_at(self, year: int, round_: int) -> Dict[str, Any]:
        return self._get_json(self._url(f"/{year}/{round_}/driverStandings.json"))

    # ---- Résultats de toute la saison (courses principales) ----
    def get_season_results(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        return self._get_json(
            self._url(f"/{year}/results.json"),
            params={"limit": limit, "offset": offset},
        )

    # ---- Qualifications de toute la saison ----
    def get_qualifying(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        return self._get_json(
            self._url(f"/{year}/qualifying.json"),
            params={"limit": limit, "offset": offset},
        )

    # ---- Sprints de toute la saison ----
    def get_sprint_results(self, year: int, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        return self._get_json(
            self._url(f"/{year}/sprint.json"),
            params={"limit": limit, "offset": offset},
        )

    # ---- Calendrier (fallback si FastF1 indispo) ----
    def get_season_calendar(self, year: int, limit: int = 1000) -> Dict[str, Any]:
        return self._get_json(
            self._url(f"/{year}.json"),
            params={"limit": limit},
        )
