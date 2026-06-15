"""Tests des fonctions pures du builder historique par circuit.

Réseau (Ergast/f1db/Wikipedia) exclu : on teste la jointure moteur `engine_for`
et la logique read-merge-write `merge_write` (IO local par clé circuitId).
"""

from __future__ import annotations

import json
from pathlib import Path

from projects.dashboard import build_gp_history as gh

# ---------- engine_for ----------


def test_engine_for_normalises_underscore_to_dash() -> None:
    emap = {(2010, "red-bull"): "Renault"}
    # Ergast renvoie "red_bull" ; le builder normalise en "red-bull"
    assert gh.engine_for(emap, 2010, "red_bull") == "Renault"


def test_engine_for_missing_returns_none() -> None:
    assert gh.engine_for({}, 1999, "ferrari") is None


# ---------- merge_write (read-merge-write par circuit) ----------


def _payload(circuit: str, n_editions: int = 1) -> dict:
    return {
        "circuitId": circuit,
        "circuitName": circuit.title(),
        "gpLabel": "Test",
        "yearFrom": 2000,
        "yearTo": 2000 + n_editions - 1,
        "editions": [{"year": 2000 + i, "winner": "X"} for i in range(n_editions)],
    }


def test_merge_write_creates_and_preserves_other_circuits(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / "docs" / "gp_history.json"
    web = tmp_path / "web" / "gp_history.json"
    monkeypatch.setattr(gh, "DOCS_JSON", docs)
    monkeypatch.setattr(gh, "WEB_JSON", web)
    # HERE.parents[1] sert au print() relatif → l'ancrer sous tmp_path
    monkeypatch.setattr(gh, "HERE", tmp_path / "a" / "b")

    # Premier circuit
    gh.merge_write("catalunya", _payload("catalunya", 2))
    # Deuxième circuit : ne doit PAS écraser le premier
    gh.merge_write("monza", _payload("monza", 1))

    for target in (docs, web):
        data = json.loads(target.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"catalunya", "monza"}
        assert len(data["catalunya"]["editions"]) == 2
        assert len(data["monza"]["editions"]) == 1


def test_merge_write_overwrites_same_circuit_key(tmp_path: Path, monkeypatch) -> None:
    docs = tmp_path / "docs" / "gp_history.json"
    web = tmp_path / "web" / "gp_history.json"
    monkeypatch.setattr(gh, "DOCS_JSON", docs)
    monkeypatch.setattr(gh, "WEB_JSON", web)
    monkeypatch.setattr(gh, "HERE", tmp_path / "a" / "b")

    gh.merge_write("catalunya", _payload("catalunya", 1))
    gh.merge_write("catalunya", _payload("catalunya", 3))  # re-run, plus d'éditions

    data = json.loads(docs.read_text(encoding="utf-8"))
    assert list(data.keys()) == ["catalunya"]
    assert len(data["catalunya"]["editions"]) == 3


def test_nat_flag_mapping_known_nationalities() -> None:
    assert gh.NAT_FLAG["British"] == "🇬🇧"
    assert gh.NAT_FLAG["Spanish"] == "🇪🇸"
    # Nationalité inconnue → chaîne vide via .get(nat, "")
    assert gh.NAT_FLAG.get("Martian", "") == ""
