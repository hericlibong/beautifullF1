
# 🏁 Beautiful F1 — Automated Data Storytelling with Formula 1

![Python](https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flourish](https://img.shields.io/badge/Flourish-Ready-ff69b4?style=for-the-badge&logo=flourish&logoColor=white)
![OpenF1](https://img.shields.io/badge/OpenF1%20API-Used-blue?style=for-the-badge)
![D3.js](https://img.shields.io/badge/D3.js-Data%20Visualisations-F9A03C?style=for-the-badge&logo=d3.js&logoColor=white)
[![GitHub Pages](https://img.shields.io/badge/Gallery-GitHub%20Pages-222222?style=for-the-badge&logo=github)](https://hericlibong.github.io/beautifullF1/)
[![Last Commit](https://img.shields.io/github/last-commit/hericlibong/beautifullF1?style=flat-square)](https://github.com/hericlibong/beautifullF1/commits/main)


**Beautiful F1** is a data storytelling project focused on **automated visualizations using Formula 1 data**.  
The goal is to explore open F1 data sources (APIs, public datasets, etc.) and generate dynamic, narrative-driven visualizations using platforms like **Flourish**, **D3.js**, and other tools.

---

## 🎯 Project Purpose

- Collect and automate F1 race data (points, standings, sprints, images, etc.)
- Create clean, dynamic visualizations based on real-time or historical performance
- Focus on clear visual storytelling powered by reproducible Python scripts
- Allow quick and scalable reuse of data for presentations, articles, or experiments

---

## 📁 Repository Structure

Each folder in this repository corresponds to an independent and self-contained visualization project.

```text
beautifulF1/
│
├── race_chart_builder/        # Animated race chart builder using Flourish
├── season_summary_heatmap/    # Heatmap of points per GP (Flourish + D3.js)
├── wdc_projection_repo/       # Championship projection scenarios (D3.js)
└── docs/                      # GitHub Pages public visualisations & gallery
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

* **[jolpi.ca](https://api.jolpi.ca/ergast/f1/)** — Mirror of the historical Ergast API (includes sprints and circuits)
* **[openf1.org](https://openf1.org/)** — Real-time open-source F1 API (used for driver images)
* **[fastf1.dev](https://docs.fastf1.dev/)** — Python package for accessing and analyzing F1 results, schedules, timing data, and telemetry

---

### 📊 See the Chart in Action

You can view the animated race chart here: [Race Chart Viz](https://flo.uri.sh/visualisation/22260899/embed)

---

## 📂 Project: `season_summary_heatmap`

✅ Retrieves full-season driver results (points, positions, grid, etc.) for any year — even ongoing seasons  
✅ Aggregates and ranks drivers by total points  
✅ Enriches each row with team name, grid position, finishing position, driver photo, and more  
✅ Generates a **CSV** for Flourish heatmap templates **and** a standalone **D3.js heatmap** version  
✅ Fully automated enrichment (no manual intervention)

---

### 📈 Visualization Example

* Flourish version: [Season Summary Heatmap (Flourish)](https://flo.uri.sh/visualisation/XXXXX/embed)
* D3.js standalone version: [Live Demo](https://hericlibong.github.io/beautifullF1/season_summary_heatmap/index.html)

---

## 📂 Project: `wdc_projection_repo`

Interactive D3.js projection of the championship title race.

* Scenario sliders (leader performance %, driver performance %)
* Dynamic filtering by risk zone
* Built with Observable Plot and D3.js

Live version: [WDC Projection 2025](https://hericlibong.github.io/beautifullF1/wdc_projection_repo/index.html)

---

## 🖼️ D3.js Visualisations & Public Gallery

From August 2025, all public-facing visualisations are **directly accessible** via the `/docs` folder and **GitHub Pages**.

* **Public Gallery**: [https://hericlibong.github.io/beautifullF1/](https://hericlibong.github.io/beautifullF1/)
* Each visualisation has:

  * Its own folder in `/docs/{viz_name}/`
  * `index.html`, `style.css`, `script.js`, and associated CSV
  * A live link for embedding anywhere (iframe-ready)

**Benefits:**

* No duplication between development and public deployment
* All visualisations share a unified dark-themed gallery homepage
* Any update pushed to `/docs` is instantly reflected on GitHub Pages

---

## ⚙️ Installation

Clone the repository and install the required dependencies:

```bash
git clone https://github.com/hericlibong/beautifullF1.git
cd beautifullF1
pip install -r requirements.txt
```

Run any module:

```bash
cd season_summary_heatmap
python main.py
```

---

## 📤 Outputs

* **CSV files** for Flourish or direct integration in D3.js
* **JSON files** for programmatic reuse
* **Live GitHub Pages** versions for embedding

---

## 🧪 Tests & Quality

* **Pytest** for unit testing
* **pytest-cov** for coverage
* **Ruff** for linting
* **Black** for formatting
* Automated CI on each push (tests + lint + formatting checks)

---

## 📜 License

Open-source under MIT License.  
Data from third-party APIs remains the property of their providers.

---

## 👤 Author

Made by **[Heric Libong](https://github.com/hericlibong)** — developer and journalist passionate about visual storytelling and Formula 1.

```

