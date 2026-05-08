# race_chart_builder — visualisation web

Visualisation D3.js v7 de l'évolution du championnat pilotes (saison 2026).

## Emplacements

Cette visualisation existe **en deux endroits** dans le repo :

- **`projects/race_chart_builder/web/`** *(ici)* — co-localisée avec le code Python qui génère la donnée (`race_chart_builder_fastf1.py`). C'est la copie de travail / source canonique.
- **`docs/race_chart_builder/`** — copie servie par **GitHub Pages** (publique sur https://hericlibong.github.io/beautifullF1/race_chart_builder/).

Les deux dossiers doivent rester **synchronisés**. À chaque modification ici, recopier dans `docs/race_chart_builder/` avant push.

## Structure

```
web/
├── index.html
├── script.js          # logique D3 (animation, scrub, filtres, tooltip…)
├── style.css
├── data/
│   └── f1_race_chart_fastf1_2026.csv   # généré par race_chart_builder_fastf1.py
├── TASKS.md           # suivi des améliorations
└── README.md
```

## Lancer en local

Depuis la racine `docs/` (ou `projects/race_chart_builder/web/`) :

```bash
python -m http.server 8000
# puis http://localhost:8000/race_chart_builder/  (si servi depuis docs/)
# ou    http://localhost:8000/                    (si servi depuis web/)
```

## Régénérer la donnée

```bash
python projects/race_chart_builder/race_chart_builder_fastf1.py
```

Le CSV de sortie alimente directement `web/data/f1_race_chart_fastf1_2026.csv`.
