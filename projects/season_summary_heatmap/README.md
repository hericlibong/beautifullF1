# 🏁 Season Summary Heatmap — Full & Leaders Analysis

## 🎯 Objectif

Ce module génère une **heatmap interactive de performance par pilote et par Grand Prix**, utilisable dans **Flourish** ou **D3.js**.
Deux versions cohabitent :

| Version           | Fichiers principaux                 | Sortie                           | Description                                                            |
| ----------------- | ----------------------------------- | -------------------------------- | ---------------------------------------------------------------------- |
| **V1 (complète)** | `exporter.py` + `main.py`           | `outputs/f1_<season>_full_heatmap.csv`    | Classement complet de tous les pilotes de la saison.                   |
| **V2 (leaders)**  | `exporter_lead.py` + `lead_main.py` | `outputs/f1_<season>_leaders_heatmap.csv` | Variante axée sur les leaders avec colonnes d’analyse supplémentaires. |

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
│   ├── f1_2025_full_heatmap.csv
│   ├── f1_2025_leaders_heatmap.csv
│   ├── f1_2026_full_heatmap.csv
│   └── f1_2026_leaders_heatmap.csv
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

**Sortie par défaut :** `projects/season_summary_heatmap/outputs/f1_2025_full_heatmap.csv`

### Version leaders (V2)

```bash
PYTHONPATH=. python projects/season_summary_heatmap/lead_main.py
```

**Sortie par défaut :** `projects/season_summary_heatmap/outputs/f1_2025_leaders_heatmap.csv`

### Générer une autre saison

Les deux entrypoints acceptent `--season` et `--output`. Si `--output` est un nom relatif,
le fichier est écrit dans `projects/season_summary_heatmap/outputs/`. Les sorties 2025 ne
sont donc pas écrasées tant que le nom de fichier reste saisonné.

```bash
PYTHONPATH=. python projects/season_summary_heatmap/main.py --season 2026 --output f1_2026_full_heatmap.csv
PYTHONPATH=. python projects/season_summary_heatmap/lead_main.py --season 2026 --output f1_2026_leaders_heatmap.csv
```

FastF1 fournit la grille depuis `race.results` : le pipeline ne fixe pas le nombre de pilotes
et accepte la grille 2026 à 22 pilotes / 11 équipes. Pour les week-ends sprint, les formats
FastF1 `sprint`, `sprint_shootout` et `sprint_qualifying` déclenchent le chargement de la
session `S` et l'ajout des points sprint.

Comme la saison 2026 est en cours, seules les courses avec résultats disponibles dans FastF1
produisent des lignes. Les courses futures peuvent apparaître dans le calendrier FastF1, mais
elles sont ignorées si leurs résultats ne sont pas encore chargés.

---

## 🧩 Données générées

### Exemple de structure (V1)

| Driver | Team | Round | Points | Grid | Position | FastLap | ... |
|---------|------|--------|---------|------|-----------|------|
| Max Verstappen | Red Bull | 1 | 26 | 1 | 1 | 1:31.2 | ... |
| Lando Norris | McLaren | 1 | 18 | 2 | 2 | 1:31.8 | ... |

### Exemple de structure (V2)

Identique à V1 mais enrichi avec :

* `SprintPoints` : points marqués en Sprint
* `FinishIcon` : icône podium basée sur la position finale
* `GridGain` : gain ou perte entre grille et arrivée
* `CumulativePoints`, `AvgPointsToDate`, `Last5Avg` : métriques de forme cumulées
* `PodiumRate`, `PointsRate`, `AvgGridGain` : métriques de régularité

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
ruff check projects/season_summary_heatmap
pytest projects/season_summary_heatmap/tests -q
```

---

## 🔮 Prochaines étapes

1. Harmoniser les schémas V1/V2 pour une visualisation unique.
2. Ajouter une sortie JSON parallèle pour intégration D3 automatique.
3. Intégrer la heatmap D3 dans `/docs` avec une page de démonstration.

---

**Auteur :** Heric Libong
**Dernière mise à jour :** 2026-05-06
**Statut :** ✅ V1 et V2 opérationnelles, outputs et structure validés.
