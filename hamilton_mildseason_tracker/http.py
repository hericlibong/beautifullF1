# from __future__ import annotations

# import logging
# import time
# from typing import Any, Dict, Optional

# import requests

# from .config import HTTP_TIMEOUT, RETRY_BACKOFF, RETRY_COUNT


# class HttpClient:
#     """Minimal HTTP client with retries and timeouts."""

#     def __init__(self, timeout: int = HTTP_TIMEOUT) -> None:
#         self.session = requests.Session()
#         self.timeout = timeout

#     def get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
#         last_exc: Optional[Exception] = None
#         for attempt in range(1, RETRY_COUNT + 1):
#             try:
#                 resp = self.session.get(url, params=params, timeout=self.timeout)
#                 resp.raise_for_status()
#                 return resp.json()
#             except Exception as exc:  # pragma: no cover (réseau)
#                 last_exc = exc
#                 wait_s = (RETRY_BACKOFF ** attempt)
#                 logging.warning("HTTP retry %s/%s %s params=%s (%s)", attempt, RETRY_COUNT, url, params, exc)
#                 time.sleep(wait_s)
#         raise RuntimeError(f"HTTP error for {url}: {last_exc}")