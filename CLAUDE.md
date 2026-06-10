# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Beautiful F1 — automated F1 data storytelling. Python builders fetch data (FastF1, Jolpica/Ergast, f1db, Wikidata/Wikipedia), produce CSV/JSON, and static HTML/JS/CSS visualisations consume them. Everything publishes to GitHub Pages from `docs/` (no backend, no bundler, vanilla JS). Current focus: the 2026 season dashboard (`projects/dashboard/`), which is the GitHub Pages home page.

## Commands

```bash
pip install -r requirements.txt

# Tests (pytest configured in pyproject.toml, coverage on by default)
pytest                                        # everything
pytest projects/dashboard/tests -q            # one project
pytest projects/dashboard/tests/test_x.py::test_name   # single test

# Lint / format (CI enforces both on push/PR to main)
ruff check .
black --check .          # black . to apply; line-length 100 for both

# Full data pipeline (FastF1 fetch → CSVs → dashboard JSON → sync to docs/)
python projects/dashboard/build_all.py
python projects/dashboard/build_all.py --skip-fetch   # re-propagate without hitting FastF1

# Per-circuit history (manual, slow — run once per circuit, then sync)
python projects/dashboard/build_gp_history.py --circuit catalunya --year-from 1991 --year-to 2025 --label Espagne

# Propagate dashboard web/ → docs/
python projects/dashboard/sync_to_docs.py

# Local preview (serves docs/, the deployed site)
python -m http.server 8000 --directory docs   # also defined in .claude/launch.json
```

Local Python may be 3.9 (CI uses 3.12) — avoid 3.10+ only syntax in code that runs locally, or guard it. `from __future__ import annotations` is used for typing.

## Architecture — the canonical → docs sync pattern (critical)

Every visualisation lives twice:

1. **Canonical source** under `projects/<name>/web/` (or `d3_dataviz/` for the heatmap) — edit HERE
2. **Deployed copy** under `docs/` — produced by each project's `sync_to_docs.py` (additive copy, never deletes)

`docs/` is what GitHub Pages serves. After editing dashboard front-end files, run `python projects/dashboard/sync_to_docs.py` before committing, and commit both copies. If you edit `docs/` directly (e.g. to hot-test), mirror the change back into `projects/.../web/` or it will be overwritten by the next sync.

## Data flow

```
FastF1 / Jolpica-Ergast / f1db / Wikipedia
        │  (Python builders in projects/*/)
        ▼
outputs/*.csv, web/data/*.json     (per-project)
        │  sync_to_docs.py / build_all.py
        ▼
docs/   (GitHub Pages: dashboard home + viz subfolders)
```

- `projects/dashboard/build_all.py` orchestrates the regular refresh: race chart CSV → heatmap CSV → `dashboard_2026.json` → 3× sync. Run automatically by `.github/workflows/refresh-after-gp.yml` (Mon+Tue 14:00 UTC after a GP; `check_should_refresh.py` gates it; commits as github-actions bot).
- Two builders are **manual only** (too slow / rate-limited for CI): `build_circuits_data.py` (FastF1 telemetry → `circuits_2026.json`) and `build_gp_history.py` (Jolpica + f1db + Wikipedia → `gp_history.json`, read-merge-write per `circuitId` key).
- Jolpica/Ergast rate-limits (HTTP 429): builders use sleeps + exponential retry — keep this when extending them.

## Dashboard front-end (projects/dashboard/web/)

Single page, vanilla JS (`assets/dashboard.js`, one async IIFE that fetches all JSON via `Promise.all`). Key conventions:

- **i18n**: FR/EN via `assets/i18n.json` + `t(key, vars)`; language persisted in `localStorage("bf1-lang")`; switching reloads the page and restores the active tab/embedded viz through `sessionStorage` (restore block runs at the END of the IIFE — order matters).
- **Tabs** (Pilotes / Constructeurs / Calendrier / Duel / Coéquipiers) are panes in one card; drill-downs (driver, circuit) are inline `<li>`/`<tr>` panels injected after the clicked row.
- **Embedded viz**: Race Line and Heatmap load in an iframe with `?embed=1&lang=xx`; both viz pages support an embed mode that hides their chrome.
- **Team colors**: current teams from `assets/teams.json` (keyed by display name); historic teams from `HISTORY_TEAM_COLORS` in dashboard.js (keyed by Ergast `teamId`, because display names differ, e.g. "Red Bull" vs "Red Bull Racing").
- **GP_TO_CIRCUIT** map in dashboard.js links calendar GP names to `gp_history.json` keys (Ergast circuitId) — extend it when adding a circuit's history.
- All charts are inline SVG built by string templates — no D3 on the dashboard (D3 only in `season_summary_heatmap/d3_dataviz/`).

## Known traps

- **"Spain" collision**: 2026 has two Spanish GPs — round 7 Barcelona (`name: "Spain"`) and round 14 Madrid (`name: "Spain - Madrid"`). Handled in dashboard/calendar/circuits, but NOT yet in `race_chart_builder._col_name` or `season_summary_heatmap` — must be fixed before Madrid (Sept 2026) or both GPs share one CSV column.
- **Driver photos**: FastF1's `HeadshotUrl` is unreliable on CI; `projects/dashboard/driver_images.json` is the fallback mapping (FIA abbreviation → URL).
- Coverage/ruff/black all exclude `test_computing/`, `projects/*/drafts/`, and the paused projects (`quali_duels`, `wdc_projection_repo`) — don't "fix" those.
- `projects/dashboard/PLAN.md` is the living roadmap (decisions, done/remaining work) — update it as features land; read it first for context on the dashboard.

## Project map (active)

- `projects/dashboard/` — 2026 dashboard: builders + `web/` front-end + PLAN.md
- `projects/race_chart_builder/` — animated cumulative points race chart ("Race Line")
- `projects/season_summary_heatmap/` — leaders heatmap (D3), canonical in `d3_dataviz/`
- `projects/gp_history/` — legacy LLM-curated historical CSVs + Wikidata enrichment tools (superseded for new circuits by `dashboard/build_gp_history.py`)
- `projects/hamilton_midseason_tracker/` — Hamilton 2007–2025 analysis (Flourish datasets)
