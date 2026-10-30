"""Vérifie les données réellement servies par Pages, pas seulement le git push."""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

DOCS = Path(__file__).resolve().parents[2] / "docs"
BASE_URL = "https://hericlibong.github.io/beautifullF1/"
FILES = (
    "data/dashboard_2026.json",
    "data/qualifying_2026.json",
    "race_chart_builder/data/f1_race_chart_fastf1_2026.csv",
    "season_summary_heatmap/f1_2026_leaders_heatmap.csv",
)


def fingerprint(content: bytes) -> bytes:
    # Git peut convertir CRLF/LF entre le poste Windows et le runner Linux.
    return hashlib.sha256(content.replace(b"\r\n", b"\n")).digest()


def main() -> int:
    expected = {name: fingerprint((DOCS / name).read_bytes()) for name in FILES}
    for attempt in range(1, 13):
        errors = []
        for name, digest in expected.items():
            try:
                request = Request(
                    BASE_URL + name + f"?verification={time.time_ns()}",
                    headers={"Cache-Control": "no-cache", "User-Agent": "BeautifulF1-verifier"},
                )
                with urlopen(request, timeout=15) as response:
                    if fingerprint(response.read()) != digest:
                        errors.append(f"{name} : version publique différente")
            except Exception as exc:
                errors.append(f"{name} : {exc}")
        if not errors:
            print("[OK] Les quatre fichiers publics correspondent aux données validées.")
            return 0
        print(f"[WAIT] Publication Pages ({attempt}/12) : {'; '.join(errors)}", flush=True)
        if attempt < 12:
            time.sleep(15)
    print("[ECHEC] La publication publique n'est pas confirmée.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
