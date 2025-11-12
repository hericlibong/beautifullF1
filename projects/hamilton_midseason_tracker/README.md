Parfait 👌 Voici le **README dédié** à `projects/hamilton_midseason_tracker`, épuré et parfaitement aligné sur ta nouvelle structure.
Il documente uniquement les trois scripts principaux, leurs sorties CSV, et leur lien avec les visualisations Flourish.

---

# 🏁 Hamilton Midseason Tracker — 2007–2025 Analysis

## 🎯 Objectif
Ce module analyse la **performance de Lewis Hamilton** à mi-saison entre **2007 et 2025**, à travers trois axes :
1. Ses résultats saisonniers globaux (points, podiums, poles, etc.)
2. Ses comparaisons directes avec ses coéquipiers
3. Ses duels en qualifications

Les données générées sont exploitées dans **Flourish** pour raconter visuellement la dégradation (ou non) de ses performances au fil des saisons.

---

## ⚙️ Structure du projet

```

projects/hamilton_midseason_tracker/
├── ham_snapshot_2007_2025.py               # Snapshot saison par saison
├── ham_teammate_comparison_builder.py      # Comparaisons Hamilton vs. coéquipiers
├── ham_quali_duels_builder.py              # Duels de qualifications
├── **main**.py                             # Permet de lancer le package en mode module
├── outputs/
│   ├── hamilton_2007_2025_snapshot.csv
│   ├── hamilton_teammate_comparison_2007_2025.csv
│   └── hamilton_quali_duels_2007_2025_until_R21.csv
└── drafts/
└── old_pipeline/                       # Anciens modules mis hors version

````

---

## 🚀 Exécution des scripts

### 1️⃣ Snapshot global (2007–2025)
Génère un tableau complet des performances de Hamilton :
```bash
PYTHONPATH=. python projects/hamilton_midseason_tracker/ham_snapshot_2007_2025.py
````

**Sortie :** `projects/hamilton_midseason_tracker/outputs/hamilton_2007_2025_snapshot.csv`

---

### 2️⃣ Comparaison avec les coéquipiers

Construit la série de données du **gap de points** avec chaque coéquipier :

```bash
PYTHONPATH=. python projects/hamilton_midseason_tracker/ham_teammate_comparison_builder.py
```

**Sortie :** `projects/hamilton_midseason_tracker/outputs/hamilton_teammate_comparison_2007_2025.csv`

---

### 3️⃣ Duels en qualifications

Mesure le **ratio de victoires/défaites** contre les coéquipiers en qualif :

```bash
PYTHONPATH=. python projects/hamilton_midseason_tracker/ham_quali_duels_builder.py
```

**Sortie :** `projects/hamilton_midseason_tracker/outputs/hamilton_quali_duels_2007_2025_until_R21.csv`

---

## 📈 Visualisations Flourish associées

| Visualisation                                                   | Description                                                         | Lien                                                                        |
| --------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **Hamilton’s Points Share vs. Championship Leader (2007–2025)** | Évolution de la part de points par rapport au leader du championnat | [Voir sur Flourish](https://public.flourish.studio/visualisation/24689576/) |
| **Gap vs. Teammate Before the Last Races**                      | Écarts cumulés face au coéquipier avant les dernières manches       | [Voir sur Flourish](https://public.flourish.studio/visualisation/25604375/) |
| **Qualification Duels: Hamilton vs. Teammate**                  | Bilan des duels en qualification par saison                         | [Voir sur Flourish](https://public.flourish.studio/visualisation/25940671/) |

---

## 🧹 Nettoyage et organisation

* Tous les scripts historiques (ex: `compute.py`, `config.py`, `export.py`, etc.) ont été déplacés dans `drafts/old_pipeline/`.
* Seuls les **3 scripts actifs** et leurs **3 CSV de sortie** sont versionnés.
* Les fichiers temporaires, caches et brouillons sont ignorés par Git.

---

## 🔮 Prochaines étapes

1. Uniformiser les noms de colonnes des 3 CSV pour un usage multiplateforme (Flourish + D3).
2. Ajouter une fonction d’exécution globale dans `__main__.py` pour lancer les trois scripts à la suite.
3. Préparer une intégration directe dans la future **Flourish Gallery** (docs/hamilton_midseason_tracker/).

---

**Auteur :** Heric Libong
**Dernière mise à jour :** 2025-11-12
**Statut :** ✅ Stable — Data storytelling complet, outputs vérifiés

```

---

