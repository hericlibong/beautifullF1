"""Fixtures E2E : sert docs/ via http.server et fournit l'URL de base.

Les tests utilisent la fixture `page` de pytest-playwright. On sert le dossier
`docs/` (exactement ce que publie GitHub Pages) pour tester le site réel.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

try:
    from urllib.request import urlopen
except ImportError:  # pragma: no cover
    urlopen = None

# conftest.py est à projects/dashboard/tests/e2e/ → la racine du repo est parents[4]
ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "docs"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url() -> str:
    """Démarre un serveur statique sur docs/ pour la session de tests."""
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", str(DOCS)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    # Attendre que le serveur réponde
    for _ in range(50):
        try:
            urlopen(url, timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)
    try:
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=5)
