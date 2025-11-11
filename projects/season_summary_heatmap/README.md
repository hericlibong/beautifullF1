# 🏁 Season Summary Heatmap — Full & Leaders Analysis

## 🎯 Objectif

Ce module génère une **heatmap interactive de performance par pilote et par Grand Prix**, utilisable dans **Flourish** ou **D3.js**.
Deux versions cohabitent :

| Version           | Fichiers principaux                 | Sortie                           | Description                                                            |
| ----------------- | ----------------------------------- | -------------------------------- | ---------------------------------------------------------------------- |
| **V1 (complète)** | `exporter.py` + `main.py`           | `outputs/f1_full_heatmap.csv`    | Classement complet de tous les pilotes de la saison.                   |
| **V2 (leaders)**  | `exporter_lead.py` + `lead_main.py` | `outputs/f1_leaders_heatmap.csv` | Variante axée sur les leaders avec colonnes d’analyse supplémentaires. |

Les deux versions produisent des datasets compatibles avec le même gabarit de visualisation.

---

## ⚙️ Structure du projet

```
projects/season_summary_heatmap/
├── exporter.py                    # V1 : heatmap complète
├── main.py                        # V1 : entrypoint principal
├── exporter_lead.py               # V2 : heatmap leaders
├── lead_main.py                   # V2 : entrypoint leader
├── outputs/                       # Contient les CSV générés
│   ├── f1_full_heatmap.csv
│   └── f1_leaders_heatmap.csv
├── d3_dataviz/                    # Version D3.js (visu publique)
│   ├── index.html
│   ├── script.js
│   └── style.css
├── tests/                         # Tests unitaires
│   └── test_season_summary_heatmap.py
└── __init__.py
```

---

## 🚀 Exécution

### Version complète (V1)

```bash
PYTHONPATH=. python projects/season_summary_heatmap/main.py
```

**Sortie :** `projects/season_summary_heatmap/outputs/f1_full_heatmap.csv`

### Version leaders (V2)

```bash
PYTHONPATH=. python projects/season_summary_heatmap/lead_main.py
```

**Sortie :** `projects/season_summary_heatmap/outputs/f1_leaders_heatmap.csv`

---

## 🧩 Données générées

### Exemple de structure (V1)

| Driver | Team | Round | Points | Grid | Position | FastLap | ... |
|---------|------|--------|---------|------|-----------|------|
| Max Verstappen | Red Bull | 1 | 26 | 1 | 1 | 1:31.2 | ... |
| Lando Norris | McLaren | 1 | 18 | 2 | 2 | 1:31.8 | ... |

### Exemple de structure (V2)

Identique à V1 mais enrichi avec :

* `leader_gap` : écart avec le leader
* `consistency_index` : métrique de régularité
* `top5_rate` : % de top 5 cumulés

---

## 🎨 Visualisation D3.js

Le dossier `d3_dataviz/` contient une version autonome de la heatmap.

* `index.html` : conteneur principal
* `script.js` : logique D3.js (chargement du CSV, rendu dynamique)
* `style.css` : mise en forme

### Déploiement vers GitHub Pages (optionnel)

Pour publier la version D3 :

```bash
rsync -a projects/season_summary_heatmap/d3_dataviz/ docs/season_summary_heatmap/
```

Le résultat sera accessible sur :
`https://hericlibong.github.io/beautifullF1/season_summary_heatmap/`

---

## 🧹 Nettoyage et conventions

* Tous les fichiers CSV sont dans `outputs/`.
* `__pycache__/` et fichiers temporaires sont ignorés.
* Les règles `.gitignore` conservent uniquement les fichiers `.csv` et `.json` utiles.

---

## 🧪 Tests

Les tests valident la cohérence des colonnes générées et la présence de valeurs pour chaque GP.

```bash
pytest projects/season_summary_heatmap/tests -q
```

---

## 🔮 Prochaines étapes

1. Harmoniser les schémas V1/V2 pour une visualisation unique.
2. Ajouter une sortie JSON parallèle pour intégration D3 automatique.
3. Intégrer la heatmap D3 dans `/docs` avec une page de démonstration.

---

**Auteur :** Heric Libong
**Dernière mise à jour :** 2025-11-11
**Statut :** ✅ V1 et V2 opérationnelles, outputs et structure validés.
