"""
Beautifull F1 — enrichments/images.py (v1)

Ajoute une seule colonne : `WinnerImageURL` pour chaque ligne (année) du CSV.

Stratégie déterministe, simple :
1) OpenF1 (si trouvé pour le pilote) → `headshot_url`
2) Wikipedia (PageImages API) → miniature de l’infobox
3) Sinon: None

Aucune écriture disque par défaut (on ne télécharge pas l'image).

Dépendances: requests
"""
from __future__ import annotations

import re
from typing import Optional
import requests
import pandas as pd

OPENF1_BASE = "https://api.openf1.org/v1"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"  # accepte titre encodé


# --- Utils ---------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Nettoie un nom (accents retirés côté Wikipédia auto; on garde simple ici)."""
    # Unifier espaces, enlever caractères parasites
    n = re.sub(r"\s+", " ", name).strip()
    # Corrections fréquentes
    fixes = {
        "Sergio Pérez": "Sergio Perez",
        "Carlos Sainz Jr.": "Carlos Sainz Jr.",
        "Max Verstappen": "Max Verstappen",
        "Michael Schumacher": "Michael Schumacher",
        "Lewis Hamilton": "Lewis Hamilton",
        "Nico Rosberg": "Nico Rosberg",
    }
    return fixes.get(n, n)


# --- OpenF1 -------------------------------------------------------------

def _openf1_headshot_by_name(name: str) -> Optional[str]:
    """Essaie de trouver un headshot OpenF1 par nom approximatif.
    OpenF1 n'est pas exhaustif historiquement; marche bien pour l'ère récente.
    """
    # Endpoint drivers (sans session_key), on filtre par nom si dispo
    # Note: OpenF1 ne garantit pas une recherche textuelle souple; on récupère un set large puis on filtre côté client.
    try:
        resp = requests.get(f"{OPENF1_BASE}/drivers", timeout=8)
        resp.raise_for_status()
        drivers = resp.json()
    except Exception:
        return None

    target = _normalize_name(name).lower()
    for d in drivers:
        # Le payload peut contenir 'full_name' ou 'first_name'/'last_name'
        full = (
            (d.get("full_name") or "").strip()
            or (f"{d.get('first_name','')} {d.get('last_name','')}").strip()
        )
        if not full:
            continue
        if full.lower() == target or target in full.lower():
            url = d.get("headshot_url") or d.get("headshot")
            if url:
                return url
    return None


# --- Wikipedia ----------------------------------------------------------

def _wikipedia_image_by_name(name: str) -> Optional[str]:
    """Récupère l'image principale via l'API REST 'summary' (PageImages)."""
    title = _normalize_name(name).replace(" ", "_")
    try:
        r = requests.get(WIKI_SUMMARY + title, headers={"accept": "application/json"}, timeout=8)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None

    # Champs possibles: thumbnail['source'] ou originalimage['source']
    thumb = (data.get("thumbnail") or {}).get("source")
    orig = (data.get("originalimage") or {}).get("source")
    return orig or thumb


# --- Public API ---------------------------------------------------------

def enrich_winner_image(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne un nouveau DataFrame avec une colonne `WinnerImageURL`.

    Hypothèses:
      - la colonne `Winner` contient le nom complet du vainqueur (ex. "Max Verstappen").
    """
    if "Winner" not in df.columns:
        return df.copy()

    urls: list[str | None] = []
    for name in df["Winner"].astype(str).tolist():
        url = _openf1_headshot_by_name(name)
        if not url:
            url = _wikipedia_image_by_name(name)
        urls.append(url)

    out = df.copy()
    out["WinnerImageURL"] = urls
    return out
