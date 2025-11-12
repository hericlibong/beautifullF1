import os
import re
import unicodedata
from typing import Optional

import fastf1
import pandas as pd
import requests
from fastf1.ergast import Ergast

# --- Headshot overrides (prioritaires) ---
HEADSHOT_OVERRIDES = {
    # driverId Ergast -> URL souhaitée (prioritaire)
    # Alonso (doit fonctionner immédiatement via l'URL fournie)
    "alonso": "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/F/FERALO01_Fernando_Alonso/feralo01.png.transform/1col/image.png",
    # ajouter:
    "button": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Jenson_Button_2024_WEC_Fuji.jpg/250px-Jenson_Button_2024_WEC_Fuji.jpg",
    "rosberg": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Nico_Rosberg_2016_Malaysia_1.jpg/250px-Nico_Rosberg_2016_Malaysia_1.jpg",
    "kovalainen": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Heikki_Kovalainen_-_British_2012.jpg/250px-Heikki_Kovalainen_-_British_2012.jpg",
}

# (optionnel) chemin fallback local si tu veux déposer des images à toi
LOCAL_HEADSHOTS_DIR = None  # ex: "assets/headshots"

# --- config ---
CUTOFF_ROUND = 20
CSV_NAME = "hamilton_teammate_comparison_2007_2025.csv"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "outputs", CSV_NAME)

# Images: OpenF1 en priorité, fallback FastF1 session results
USE_OPENF1_IMAGES = True
OPENF1_TIMEOUT = 10

# Coéquipier principal par saison (équipe, nom complet, driverId Ergast)
TEAMMATES = {
    2007: ("McLaren", "Fernando Alonso", "alonso"),
    2008: ("McLaren", "Heikki Kovalainen", "kovalainen"),
    2009: ("McLaren", "Heikki Kovalainen", "kovalainen"),
    2010: ("McLaren", "Jenson Button", "button"),
    2011: ("McLaren", "Jenson Button", "button"),
    2012: ("McLaren", "Jenson Button", "button"),
    2013: ("Mercedes", "Nico Rosberg", "rosberg"),
    2014: ("Mercedes", "Nico Rosberg", "rosberg"),
    2015: ("Mercedes", "Nico Rosberg", "rosberg"),
    2016: ("Mercedes", "Nico Rosberg", "rosberg"),
    2017: ("Mercedes", "Valtteri Bottas", "bottas"),
    2018: ("Mercedes", "Valtteri Bottas", "bottas"),
    2019: ("Mercedes", "Valtteri Bottas", "bottas"),
    2020: ("Mercedes", "Valtteri Bottas", "bottas"),
    2021: ("Mercedes", "Valtteri Bottas", "bottas"),
    2022: ("Mercedes", "George Russell", "russell"),
    2023: ("Mercedes", "George Russell", "russell"),
    2024: ("Mercedes", "George Russell", "russell"),
    2025: ("Ferrari", "Charles Leclerc", "leclerc"),
}

HAM_DRIVER_ID = "hamilton"
HAM_NAME = "Lewis Hamilton"

# fastf1.Cache.enable_cache("~/.cache/fastf1")  # optionnel
erg = Ergast(result_type="pandas", auto_cast=True, limit=1000)


def _safe_first(resp) -> pd.DataFrame:
    """ErgastMultiResponse.content -> list[DataFrame] ; retourne le premier DataFrame."""
    if hasattr(resp, "content"):
        content = resp.content
        if isinstance(content, list):
            return content[0] if content else pd.DataFrame()
        return content if isinstance(content, pd.DataFrame) else pd.DataFrame()
    return pd.DataFrame()


def _get_points(season: int, round_cutoff: int, driver_id: str) -> Optional[float]:
    """Points cumulés du pilote 'driver_id' au round donné (inclut sprints si présents)."""
    try:
        resp = erg.get_driver_standings(season=season, round=round_cutoff)
        df = _safe_first(resp)
        if df.empty:
            return None
        # Normaliser driverId
        if "driverId" not in df.columns:
            if "Driver" in df.columns:
                df = df.copy()
                df["driverId"] = df["Driver"].apply(
                    lambda d: (d or {}).get("driverId", "").lower() if isinstance(d, dict) else ""
                )
            else:
                return None
        row = df.loc[df["driverId"].str.lower() == driver_id.lower()]
        if row.empty:
            return None
        return float(row.iloc[0]["points"])
    except Exception:
        return None


def _get_cutoff_event(season: int, round_wanted: int):
    """Retourne (round_eff, EventName, EventDate) via le calendrier FastF1."""
    sched = fastf1.get_event_schedule(season)
    if "RoundNumber" in sched.columns:
        total_rounds = int(sched["RoundNumber"].max())
        r_eff = min(round_wanted, total_rounds)
        row = sched.loc[sched["RoundNumber"] == r_eff].iloc[0]
        name = row["EventName"]
        date = row["EventDate"]
    else:
        total_rounds = len(sched)
        r_eff = min(round_wanted, total_rounds)
        row = sched.iloc[r_eff - 1]
        name = row.get("EventName", "")
        date = row.get("EventDate", pd.NaT)
    return int(r_eff), str(name), pd.to_datetime(date)


# -----------------------------
#   Headshots (OpenF1 + FastF1)
# -----------------------------


def _norm(s: str) -> str:
    if not isinstance(s, str):
        return ""
    # minuscules, suppression accents/ponctuation
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def get_headshot_url(name: str, year: int, team_hint: str | None = None) -> str | None:
    """
    Cherche une photo de pilote (OpenF1 priorité, fallback FastF1).
    Recherche tolérante sur nom/équipe + tri par date/session la plus récente.
    """
    base = "https://api.openf1.org/v1/drivers"
    name_n = _norm(name)
    team_n = _norm(team_hint) if team_hint else ""

    # ---- 1) OPENF1 (robuste) ----
    try:
        # On commence par last_name (plus large), puis full_name (plus précis)
        last_name = name.split()[-1]
        queries = [{"last_name": last_name}, {"full_name": name}]
        best = None
        best_key = (-1, -1, "")  # tri: date/session_key, meeting_key, priorité de match

        for params in queries:
            r = requests.get(base, params=params, timeout=10)
            if not r.ok:
                continue
            data = r.json()
            for d in data:
                url = d.get("headshot_url") or ""
                if not url:
                    continue

                # Normalisations pour match
                full_n = _norm(d.get("full_name", ""))
                last_n = _norm(d.get("last_name", ""))
                team_dn = _norm(d.get("team_name", ""))

                # Score de nom: 2 = full_name exact, 1 = last_name, 0 = autre
                name_score = 0
                if full_n == name_n and full_n:
                    name_score = 2
                elif last_n and (last_n == _norm(last_name)):
                    name_score = 1

                # Team: préférer si le team_hint (normalisé) est contenu
                team_ok = True
                if team_n:
                    team_ok = team_n in team_dn  # "aston martin" ⊂ "aston martin aramco f1 team"

                # Clés de tri (date > session_key > meeting_key)
                date_val = d.get("date") or ""
                date_key = date_val if isinstance(date_val, str) else str(date_val or "")
                try:
                    sk = int(d.get("session_key") or 0)
                except Exception:
                    sk = 0
                try:
                    mk = int(d.get("meeting_key") or 0)
                except Exception:
                    mk = 0

                if name_score > 0 and team_ok:
                    key = (date_key, sk, mk, name_score)
                    if key > best_key:
                        best_key = key
                        best = url

        if best:
            return best
    except Exception:
        pass

    # ---- 2) Fallback FASTF1 (optionnel, inchangé) ----
    try:
        r_eff, _, _ = _get_cutoff_event(year, CUTOFF_ROUND)
        sess = fastf1.get_session(year, r_eff, "R")
        sess.load()
        res = getattr(sess, "results", None)
        if isinstance(res, pd.DataFrame) and not res.empty and "HeadshotUrl" in res.columns:
            last = _norm(name.split()[-1])
            mask = pd.Series(False, index=res.index)
            for col in ("FullName", "LastName", "BroadcastName"):
                if col in res.columns:
                    mask = mask | res[col].astype(str).map(_norm).str.contains(last, na=False)
            sub = res.loc[mask]
            if not sub.empty:
                url = sub.iloc[0].get("HeadshotUrl")
                if isinstance(url, str) and url.strip():
                    return url
    except Exception:
        pass

    return None


def resolve_headshot_url(
    name: str, driver_id: str, year: int, team_hint: str | None = None
) -> str | None:
    """
    Résolution d'image avec priorités:
    1) Override explicite (HEADSHOT_OVERRIDES)
    2) Fichier local (si LOCAL_HEADSHOTS_DIR défini)
    3) OpenF1 / FastF1 via get_headshot_url (logique existante)
    """
    # 1) override prioritaire
    url = HEADSHOT_OVERRIDES.get(driver_id.lower())
    if url:
        return url

    # 2) fichier local optionnel
    if LOCAL_HEADSHOTS_DIR:
        for ext in (".jpg", ".png", ".jpeg", ".webp"):
            p = os.path.join(LOCAL_HEADSHOTS_DIR, f"{driver_id.lower()}{ext}")
            if os.path.isfile(p):
                return p

    # 3) logique existante OpenF1 -> FastF1
    return get_headshot_url(name, year, team_hint=team_hint)


# ----------------------------------------------------------------------
# *** AJOUT MINIMAL POUR CUT-OFF = PROCHAIN GP (last + 1) ***
# ----------------------------------------------------------------------


def _get_last_completed_round(season: int) -> Optional[int]:
    """Dernier round réellement clôturé pour 'season' (via standings Ergast)."""
    try:
        resp = erg.get_driver_standings(season=season, round="last")
        df = _safe_first(resp)
        if df.empty:
            return None
        for col in ("round", "Round"):
            if col in df.columns:
                try:
                    return int(df.iloc[0][col])
                except Exception:
                    pass
        return None
    except Exception:
        return None


def _get_reference_next_round(reference_year: int = max(TEAMMATES.keys())) -> int:
    """Calcule K_next = (dernier round cloturé du REFERENCE_YEAR) + 1."""
    last_done = _get_last_completed_round(reference_year)
    if last_done is None:
        # si indispo, on garde le comportement antérieur (R18) + 1
        return CUTOFF_ROUND + 1
    return int(last_done) + 1


# -----------------------------
#   Build dataset
# -----------------------------
records = []

# -> NOUVEAU: cutoff = prochain GP du REFERENCE_YEAR (ex: si R18 fini, on prend 19)
k_next = _get_reference_next_round()

for year, (team, teammate_name, teammate_id) in TEAMMATES.items():
    # On applique ce cutoff à chaque saison, borné par son calendrier propre
    r_eff, gp_name, gp_date = _get_cutoff_event(year, k_next)

    ham_pts = _get_points(year, r_eff, HAM_DRIVER_ID)
    tm_pts = _get_points(year, r_eff, teammate_id)
    gap = (ham_pts - tm_pts) if (ham_pts is not None and tm_pts is not None) else None

    ham_img = resolve_headshot_url(HAM_NAME, HAM_DRIVER_ID, year, team_hint=team)
    tm_img = resolve_headshot_url(teammate_name, teammate_id, year, team_hint=team)

    records.append(
        {
            "year": year,
            "round_cutoff": r_eff,
            "gp_name_cutoff": gp_name,
            "gp_date_cutoff": gp_date,
            "team": team,
            "hamilton_points": ham_pts,
            "teammate_name": teammate_name,
            "teammate_points_to_date": tm_pts,
            "teammate_gap": gap,
            # "hamilton_headshot_url": ham_img,
            # "teammate_headshot_url": tm_img
        }
    )

out = pd.DataFrame.from_records(records)
out.to_csv(OUTPUT_FILE, index=False)
print(f"✅ Dataset exporté : {OUTPUT_FILE}  |  Cutoff = prochain GP (K_next={k_next})")
print(out.head(10))
