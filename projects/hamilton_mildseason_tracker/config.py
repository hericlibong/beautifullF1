from __future__ import annotations

import os

# API base (Jolpica – Ergast-compatible)
JOLPICA_BASE_URL: str = os.getenv("JOLPICA_BASE_URL", "https://api.jolpi.ca/ergast/f1")

# Target driver (Ergast driverId)
DRIVER_ID: str = os.getenv("DRIVER_ID", "hamilton")

# Seasons
SEASON_START: int = int(os.getenv("SEASON_START", "2007"))
SEASON_END: int = int(os.getenv("SEASON_END", "2025"))

# HTTP
HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "30"))
RETRY_COUNT: int = int(os.getenv("RETRY_COUNT", "3"))
RETRY_BACKOFF: float = float(os.getenv("RETRY_BACKOFF", "1.5"))  # exponent base

# Output
OUTPUT_CSV: str = os.getenv(
    "OUTPUT_CSV", "hamilton_mildseason_tracker/hamilton_midseason_snapshot.csv"
)
OUTPUT_JSON: str = os.getenv(
    "OUTPUT_JSON", "hamilton_mildseason_tracker/hamilton_midseason_snapshot.json"
)
