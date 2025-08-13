from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from .config import OUTPUT_CSV, OUTPUT_JSON


@dataclass
class YearRecord:
    year: int
    round_cutoff: int
    gp_name_cutoff: str
    gp_date_cutoff: str
    hamilton_rank: int
    hamilton_points: float
    leader_points: float
    points_behind: float
    pct_of_leader: float
    wins_to_date: int
    podiums_to_date: int
    poles_to_date: int
    dnf_to_date: int
    races_started: int
    # compat ascendant : on laisse l'ancien champ
    races_scored_pct: float
    # nouveaux champs
    race_scored_pct_main: float
    weekend_scored_pct: float
    zero_point_weekends_to_date: int
    constructor_id: str
    teammate_points_to_date: Optional[float]
    teammate_gap: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def write_csv(rows: List[YearRecord], path: str = OUTPUT_CSV) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].to_dict().keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r.to_dict())


def write_json(rows: List[YearRecord], path: str = OUTPUT_JSON, indent: int = 2) -> None:
    data = [r.to_dict() for r in rows]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
