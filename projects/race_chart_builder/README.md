# 🏁 Race Chart Builder — Dataset Automatisé FastF1

## 🎯 Objectif

Ce module génère automatiquement un **dataset cumulatif des points F1 par Grand Prix**, exploitable dans des visualisations **Flourish** ou **D3.js**.
Il utilise l’API **FastF1** comme source principale et s’exécute sous Python sans dépendances externes lourdes.

---

## ⚙️ Structure actuelle

```
projects/race_chart_builder/
├── race_chart_builder_fastf1.py      # ✅ Version principale (à utiliser)
├── outputs/                          # Contient les CSV/JSON générés
│   ├── f1_race_chart_fastf1.csv      # Dataset principal
│   ├── f1_race_chart_results.csv     # Sortie legacy (ancienne version)
│   └── f1_race_chart_results.json    # Sortie legacy JSON
├── drafts/                           # Anciennes versions (non maintenues)
│   ├── legacy_race_chart_builder.py
│   └── main_legacy.py
├── tests/                            # Tests unitaires
│   └── test_race_chart_builder.py
└── __init__.py
```

---

## 🚀 Utilisation

Exécution directe depuis la racine du projet :

```bash
PYTHONPATH=. python projects/race_chart_builder/race_chart_builder_fastf1.py
```

La commande génère automatiquement un fichier CSV dans :

```
projects/race_chart_builder/outputs/f1_race_chart_fastf1.csv
```

---

## 🧩 Données générées

Chaque ligne du CSV correspond au cumul des points d’un pilote après chaque Grand Prix.

### Colonnes principales

| Colonne  | Description                                            |
| -------- | ------------------------------------------------------ |
| `Pilote` | Nom du pilote                                          |
| `image`  | URL de la photo du pilote (source : OpenF1)            |
| `team`   | Nom de l’équipe                                        |
| `start`  | Points avant le début de la saison (généralement 0)    |
| `GPs…`   | Colonnes dynamiques par Grand Prix avec points cumulés |

### Exemple de structure de sortie

```
Pilote,image,team,start,Australia,China,Japan,Bahrain,Saudi Arabia,...
Lando Norris,https://media.formula1.com/...png,McLaren,0,25.0,44.0,62.0,77.0,...
```

---

## 📦 Gestion des versions

* **Version actuelle (FastF1)** : stable et utilisée pour toutes les nouvelles générations de datasets.
* **Version legacy (drafts)** : conservée pour référence, non exécutée ni versionnée.

---

## 🧹 Nettoyage et conventions

* Tous les fichiers générés (CSV, JSON) sont stockés dans `outputs/`.
* Le dossier `drafts/` contient uniquement des implémentations anciennes.
* `__pycache__/` est ignoré par Git.

---

## 🧪 Tests

Les tests unitaires se trouvent dans `projects/race_chart_builder/tests/` et valident :

* L’existence du fichier CSV de sortie.
* La présence des colonnes clés (`Pilote`, `team`, `points`, etc.).

Exécution :

```bash
pytest projects/race_chart_builder/tests -q
```

---

## 🔮 Prochaines étapes

1. Ajouter une option CLI (`--season`, `--topn`, `--include-sprint`) si besoin.
2. Générer aussi une sortie JSON à partir du CSV (optionnel).
3. Connecter la sortie à une visualisation Flourish automatisée.

---

## 🧾 Notes internes

* Les fichiers `f1_race_chart_results.*` proviennent de la **V1** ; ils restent dans `outputs/` pour compatibilité.
* Les futures versions de la visualisation pointeront uniquement sur `f1_race_chart_fastf1.csv`.

---

**Auteur :** Heric Libong
**Dernière mise à jour :** 2025‑11‑11
**Statut :** ✅ Structure validée, version FastF1 active.
