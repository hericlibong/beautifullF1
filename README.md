


# 🏁 Beautifull F1 — Automated Data Storytelling with Formula 1

![Python](https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flourish](https://img.shields.io/badge/Flourish-Ready-ff69b4?style=for-the-badge&logo=flourish&logoColor=white)
![OpenF1](https://img.shields.io/badge/OpenF1%20API-Used-blue?style=for-the-badge)



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



### 🧱 Requirements

Minimal dependencies:

```txt
pandas>=1.5
requests>=2.28
```

> Compatible with Python 3.9 and above (tested on Python 3.12)

---

## 📜 License

Open-source project under the MIT License.  
Data from third-party APIs (openf1.org, jolpi.ca) remains the property of their respective providers.

---

## 👤 Author

Made by **[Heric Libong](https://github.com/hericlibong)** — developer and journalist passionate about visual storytelling and Formula 1.


