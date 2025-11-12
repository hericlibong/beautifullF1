
# 🏁 Beautiful F1 — Automated Data Storytelling with Formula 1

![Python](https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flourish](https://img.shields.io/badge/Flourish-Ready-ff69b4?style=for-the-badge&logo=flourish&logoColor=white)
![OpenF1](https://img.shields.io/badge/OpenF1%20API-Used-blue?style=for-the-badge)
![D3.js](https://img.shields.io/badge/D3.js-Data%20Visualisations-F9A03C?style=for-the-badge&logo=d3.js&logoColor=white)
[![GitHub Pages](https://img.shields.io/badge/Gallery-GitHub%20Pages-222222?style=for-the-badge&logo=github)](https://hericlibong.github.io/beautifullF1/)
[![Last Commit](https://img.shields.io/github/last-commit/hericlibong/beautifullF1?style=flat-square)](https://github.com/hericlibong/beautifullF1/commits/main)

---

**Beautiful F1** is a data storytelling project focused on **automated visualizations using Formula 1 data**.  
The goal is to explore open F1 data sources (APIs, public datasets, etc.) and generate dynamic, narrative-driven visualizations using platforms like **Flourish**, **D3.js**, and other tools.

---

## 🎯 Project Purpose

- Collect and automate F1 race data (points, standings, sprints, images, etc.)
- Create clean, dynamic visualizations based on real-time or historical performance
- Focus on clear visual storytelling powered by reproducible Python scripts
- Allow quick and scalable reuse of data for presentations, articles, or experiments

---

## 📁 Repository Structure (2025)

Each project under `/projects` is **independent**, **documented**, and **reproducible**.  
Only stable and versioned projects are included below.

```text
beautifulF1/
│
├── projects/
│   ├── gp_history/                # Grand Prix history datasets (Flourish + Wikidata)
│   ├── race_chart_builder/        # Animated race chart builder using FastF1 + Flourish
│   ├── season_summary_heatmap/    # Full-season and leader heatmaps (Flourish + D3.js)
│   └── hamilton_midseason_tracker/ # Lewis Hamilton’s mid-season 2007–2025 analysis
│
├── docs/                          # GitHub Pages visualisations gallery
├── test_computing/                # Local drafts (ignored from version control)
└── README.md
````

Projects currently in **pause** or **local-only stage** (not versioned):

* `projects/quali_duels/`
* `projects/wdc_projection_repo/`

---

## 📂 Project Highlights

### 🏎️ `projects/race_chart_builder`

Automated generator for **animated race charts** (Flourish-compatible).
Fetches results from **FastF1** and **OpenF1**, builds cumulative points per driver, and exports:

* `outputs/f1_race_chart_fastf1.csv` (Flourish dataset)

Run manually:

```bash
python projects/race_chart_builder/race_chart_builder_fastf1.py
```

---

### 🔥 `projects/season_summary_heatmap`

Generates **Flourish and D3.js heatmaps** for season-overview visualizations.

Two versions coexist:

* `exporter.py` + `main.py` → full grid (`f1_full_heatmap.csv`)
* `exporter_lead.py` + `lead_main.py` → leaders only (`f1_leaders_heatmap.csv`)

Visual version deployed to:
👉 [docs/season_summary_heatmap/](https://hericlibong.github.io/beautifullF1/season_summary_heatmap/)

---

### 🧠 `projects/gp_history`

Processes historical GP data using **Wikidata** and curated sources.
Exports cleaned CSVs such as:

* `data/gp_history/mexican_grand_prix.csv`
* `data/reference/wikidata_query_results.csv`

Scripts and enrichment tools are modularized under `tools/enrichments/`.

---

### 🏁 `projects/hamilton_midseason_tracker`

Analyzes **Hamilton’s mid-season performance** across 2007–2025.
Three scripts build the datasets used for visual storytelling:

| Script                               | Output                                         | Description                |
| ------------------------------------ | ---------------------------------------------- | -------------------------- |
| `ham_snapshot_2007_2025.py`          | `hamilton_2007_2025_snapshot.csv`              | Season snapshot            |
| `ham_teammate_comparison_builder.py` | `hamilton_teammate_comparison_2007_2025.csv`   | Hamilton vs teammate gap   |
| `ham_quali_duels_builder.py`         | `hamilton_quali_duels_2007_2025_until_R21.csv` | Qualification head-to-head |

These feed Flourish visualizations such as:

* [Hamilton’s points share vs leader](https://public.flourish.studio/visualisation/24689576/)
* [Teammate gap evolution](https://public.flourish.studio/visualisation/25604375/)
* [Qualification duels](https://public.flourish.studio/visualisation/25940671/)

---

## 🖼️ D3.js Visualisations & Public Gallery

All public-facing visualisations are accessible through GitHub Pages at:
👉 **[https://hericlibong.github.io/beautifullF1/](https://hericlibong.github.io/beautifullF1/)**

Each visualization resides in its own subfolder under `/docs/{viz_name}/`, e.g.:

```
docs/
├── index.html
├── season_summary_heatmap/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── hamilton_midseason_tracker/
```

Any update to `/docs` is instantly reflected on GitHub Pages.

---

## ⚙️ Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/hericlibong/beautifullF1.git
cd beautifullF1
pip install -r requirements.txt
```

Run any stable module (example):

```bash
python projects/hamilton_midseason_tracker/ham_snapshot_2007_2025.py
```

---

## 📤 Outputs

All outputs are stored in each module’s `/outputs` directory.

* **CSV files** for Flourish or D3.js
* **JSON files** for programmatic integration
* **Published D3 visualisations** under `/docs`

---

## 🧪 Tests & Quality

* **Pytest** for unit testing (`projects/**/tests/`)
* **pytest-cov** for coverage
* **Ruff** for linting
* **Black** for formatting
* Continuous integration on each push (tests + lint + formatting)

---

## 📜 License

Open-source under MIT License.
Data from third-party APIs remains property of their providers.

---

## 👤 Author

Made by **[Heric Libong](https://github.com/hericlibong)** — developer and journalist passionate about visual storytelling and Formula 1.

```

---

### 🔍 Résumé des ajustements

✅ Arborescence revue selon la structure réelle :  
`projects/{gp_history,race_chart_builder,season_summary_heatmap,hamilton_midseason_tracker}`  
✅ Suppression des anciens projets non suivis (`quali_duels`, `wdc_projection_repo`) — mentionnés comme *paused*.  
✅ Cohérence entre les chemins, noms de fichiers et scripts.  
✅ Maintien du ton et du style de ton README original (aucun branding altéré).  

---


