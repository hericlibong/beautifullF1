


# 🏁 Beautifull F1 — Automated Data Storytelling with Formula 1

![Python](https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flourish](https://img.shields.io/badge/Flourish-Ready-ff69b4?style=for-the-badge&logo=flourish&logoColor=white)
![OpenF1](https://img.shields.io/badge/OpenF1%20API-Used-blue?style=for-the-badge)
[![Last Commit](https://img.shields.io/github/last-commit/hericlibong/beautifullF1?style=flat-square)](https://github.com/hericlibong/beautifullF1/commits/main)




**Beautifull F1** is a data storytelling project focused on **automated visualizations using Formula 1 data**.  
The goal is to explore open F1 data sources (APIs, public datasets, etc.) and generate dynamic, narrative-driven visualizations using platforms like **Flourish** and other tools.

---

## 🎯 Project Purpose

- Collect and automate F1 race data (points, standings, sprints, images, etc.)
- Create clean, dynamic visualizations based on real-time or historical performance
- Focus on clear visual storytelling powered by reproducible Python scripts
- Allow quick and scalable reuse of data for presentations, articles, or experiments

---

## 📁 Repository Structure

Each folder in this repository corresponds to an independent and self-contained visualization project.

```bash
beautifullF1/
│
├── race_chart_builder/        <- Animated race chart builder using Flourish
└── README.md                  <- This file
```

---

## 📂 Project: `race_chart_builder`

This folder contains a Python program that:

✅ Automatically retrieves Formula 1 race results (including sprints) using APIs  
✅ Aggregates drivers' points over time  
✅ Generates a **CSV file** compatible with [Flourish](https://flourish.studio/) for animated race charts  
✅ Also produces a **JSON file** with the same data structure

---

### 🔗 Data Sources

- **[jolpi.ca](https://api.jolpi.ca/ergast/f1/)**  
  Maintained mirror of the historical Ergast API (includes sprints and circuits)

- **[openf1.org](https://openf1.org/)**  
  Real-time open-source F1 API used here to retrieve driver photos

- **[fastf1.dev](https://docs.fastf1.dev/)**
  Python package for accessing and analyzing Formula 1 results, schedules, timing data and telemetry. 
---

### 📊 See the Chart in Action

You can view the animated race chart here: [Race Chart Viz](https://flo.uri.sh/visualisation/22260899/embed)

### ⚙️ Installation

Clone the repository and install the required dependencies:

```bash
git clone https://github.com/hericlibong/beautifullF1.git
cd beautifullF1
pip install -r requirements.txt
```

> Then navigate into the project folder of your choice:
```bash
cd race_chart_builder
python main.py
```

---

### 📤 Output

The script generates:

- `f1_race_chart_results.csv` → upload to Flourish to create a bar chart race
- `f1_race_chart_results.json` → same data in JSON format for reuse or debugging


---

## 📂 Project: `season_summary_heatmap`

This folder contains a Python module and automation script that:

✅ Retrieves full-season driver results (points, positions, grid, etc.) for any year — even a season in progress
✅ Aggregates and ranks drivers by total points
✅ Enriches each row with team name, grid position, finishing position, driver photo, and more
✅ Generates a **CSV file** in the exact format required for **Flourish heatmap** templates
✅ Allows direct integration of images and “narrative” data (pilot name, full GP name, etc.) in Flourish vignettes or tooltips

---

### 📈 Visualization Example

See the live heatmap for the 2025 season (demo):
[Season Summary Heatmap (Flourish)](https://flo.uri.sh/visualisation/XXXXX/embed)


---

### ⚡️ How to Use

From the project root:

```bash
cd season_summary_heatmap
python main.py
```

You can customize the season/year and output file in `main.py`.

---

### 🧩 Output

The script produces:

* `f1_2025_heatmap_flourish_enriched.csv` — ready for import into Flourish (“categorical heatmap” or similar)
* The file is structured for maximum compatibility, with each row :

  * Driver abbreviation and name
  * Team name
  * Grand Prix (short and full labels)
  * Points (per round and total)
  * Rank in championship
  * Grid/start and finish positions
  * Driver headshot image (for custom tooltips)

---

### 🖼️ Images & Enrichment

Driver photos and other enriched data are fetched directly via Fast-F1 (or patched for substitute drivers).
No manual intervention is needed — everything is automated.

---

### 💡 Why this format?

* Compatible with Flourish heatmap and advanced “storytelling” templates
* Automates missing data handling (in-progress season, rookies, etc.)
* Reproducible, testable, and easy to extend for other seasons or new features

---





### 🧱 Requirements

Minimal dependencies:

```txt
pandas>=1.5
requests>=2.28
```

> Compatible with Python 3.9 and above (tested on Python 3.12)

---

Bien sûr, voici une **section “Tests & Quality”** prête à intégrer juste avant la licence ou après les requirements dans ton README actuel (en anglais, dans le ton de la doc) :

---

## 🧪 Tests & Quality

This project uses modern Python tools to ensure code reliability and quality:

* **Pytest** for unit testing
* **pytest-cov** for code coverage
* **Ruff** for fast linting and code quality (replaces flake8/isort)
* **Black** for automatic code formatting

### 🔍 Running the tests

From the project root, run:

```bash
pytest
```

*(Coverage is reported automatically thanks to the configuration in `pyproject.toml`)*

### 🔎 Checking code quality

```bash
ruff check .
black --check .
```

*(To auto-fix code style, run: `black .` and/or `ruff check . --fix`)*

### 🚦 Continuous Integration (CI)

Each push or pull request to the `main` branch automatically runs:

* Unit tests with coverage
* Ruff linter checks
* Black formatting checks
  The CI build will fail if any of these steps fail.

### 🗂️ Coverage Policy

Only main scripts and modules are covered. Test files, `__init__.py`, and the non-versioned `test_computing` directory are excluded to keep the coverage rate meaningful.

---

## 📜 License

Open-source project under the MIT License.  
Data from third-party APIs (openf1.org, jolpi.ca) remains the property of their respective providers.

---

## 👤 Author

Made by **[Heric Libong](https://github.com/hericlibong)** — developer and journalist passionate about visual storytelling and Formula 1.


