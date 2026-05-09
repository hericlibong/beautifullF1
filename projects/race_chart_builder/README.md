# 🏁 Race Chart Builder — Dataset Automatisé FastF1

## 🎯 Objectif

Ce module génère automatiquement un **dataset cumulatif des points F1 par Grand Prix**, exploitable dans des visualisations **Flourish** ou **D3.js**.
Il utilise l'API **FastF1** comme source principale et s'exécute sous Python sans dépendances externes lourdes.

---

## ⚙️ Structure actuelle

```
projects/race_chart_builder/
├── race_chart_builder_fastf1.py      # ✅ Builder principal (FastF1)
├── sync_to_docs.py                   # Recopie web/ vers docs/race_chart_builder/
├── web/                              # Source canonique de la viz publiée
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   └── data/
│       └── f1_race_chart_fastf1_<season>.csv
├── outputs/                          # CSV générés par le builder
│   └── f1_race_chart_fastf1_<season>.csv
├── drafts/                           # Itérations locales, ignorées par git
└── __init__.py
```

---

## 🚀 Utilisation

Exécution directe depuis la racine du projet :

```bash
python projects/race_chart_builder/race_chart_builder_fastf1.py --season 2026
```

La commande génère un fichier CSV dans :

```
projects/race_chart_builder/outputs/f1_race_chart_fastf1_<season>.csv
```

Pour régénérer **toutes** les données du dashboard d'un coup (race chart + heatmap + KPI + sync vers `docs/`) :

```bash
python projects/dashboard/build_all.py
```

---

## 🧩 Données générées

Chaque ligne du CSV correspond au cumul des points d'un pilote après chaque Grand Prix.

### Colonnes principales

| Colonne  | Description                                            |
| -------- | ------------------------------------------------------ |
| `Pilote` | Nom du pilote                                          |
| `image`  | URL de la photo du pilote (source : OpenF1)            |
| `team`   | Nom de l'équipe                                        |
| `start`  | Points avant le début de la saison (généralement 0)    |
| `GPs…`   | Colonnes dynamiques par Grand Prix avec points cumulés |

### Exemple de structure de sortie

```
Pilote,image,team,start,Australia,China,Japan,Bahrain,Saudi Arabia,...
Lando Norris,https://media.formula1.com/...png,McLaren,0,25.0,44.0,62.0,77.0,...
```

---

## 📦 Gestion des versions

* **Version actuelle (FastF1)** : stable, utilisée pour toutes les nouvelles générations de datasets.
* **Drafts** : itérations locales conservées dans `drafts/`, ignorées par git.

---

## 🧹 Nettoyage et conventions

* Tous les fichiers générés (CSV) sont stockés dans `outputs/`.
* La copie consommée par la viz publiée vit dans `web/data/`, propagée vers `docs/` par `sync_to_docs.py`.
* `__pycache__/` et `drafts/` sont ignorés par Git.

---

## 🔮 Prochaines étapes

1. Options CLI complémentaires (`--topn`, `--include-sprint`).
2. Générer aussi une sortie JSON à partir du CSV (optionnel).

---

**Auteur :** Heric Libong
**Statut :** ✅ Structure validée, version FastF1 active.
