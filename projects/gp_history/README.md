# 🏁 GP History — Dataset Builder (per Grand Prix)

## Objectif

`projects/gp_history` sert à **construire des jeux de données historiques par Grand Prix** (GP) à partir de sources hétérogènes (CSV préparés, enrichissements WikiData, assets pilotes). Le périmètre actuel couvre **le Grand Prix du Mexique** ; l’architecture permet d’ajouter d’autres GP ensuite sans perturber les scripts existants.

---

## TL;DR (exécution rapide)

```bash
# Depuis la racine du repo
# (optionnel) isole l'environnement
# python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Exécuter le pipeline Mexique
PYTHONPATH=. python projects/gp_history/tools/run_mexico_full.py
```

> **Entrées** : `data/gp_history/mexican_grand_prix.csv`, `data/reference/wikidata_query_results.csv`
> **Sorties** : par défaut, **aucune sortie versionnée** ; si le pipeline écrit des artefacts, ils doivent aller dans `outputs/` (voir ci‑dessous).

---

## Structure du dossier

```
projects/gp_history/
├── asset/                      # Ressources statiques (ex. portraits pilotes)
│   └── drivers/
├── data/
│   ├── gp_history/             # Données brutes/spécifiques à un GP
│   │   └── mexican_grand_prix.csv
│   └── reference/              # Tables de référence (sources externes)
│       ├── wikidata_query_results.csv
│       └── llm/                # (parking) Fichiers générés par LLM, hors pipeline
│           ├── brazil_gp_history_first.csv
│           └── brazil_gp_history_updated.csv
├── outputs/                    # (facultatif) Artefacts exportés (CSV/JSON pour publication)
├── tools/                      # Scripts d’orchestration
│   ├── run_mexico_full.py      # 1‑click pipeline pour le GP du Mexique
│   ├── gp_history_builder_mexique_v1.py
│   └── enrichments/
│       ├── wikidata_fetch.py   # Récupération/completion via Wikidata
│       ├── images.py           # Gestion d’images/URLs
│       ├── engines.py          # Utilitaires de transformation
│       └── apply_wikidata_patch.py
└── __init__.py
```

### Décisions clés

* **`outputs/` est conservé** : dossier standardisé pour les exports publiables (Flourish/D3.js).
  Par défaut, il est ignoré par Git **sauf** CSV/JSON finaux explicitement gardés (règles globales du `.gitignore`).
* **`data/reference/llm/`** : parking pour des fichiers générés par LLM (non utilisés par les scripts).
  Cela évite toute confusion avec les entrées “officielles” du pipeline.

---

## Flux de données (actuel)

```
(data) mexican_grand_prix.csv
            │
            ▼
[tools/gp_history_builder_mexique_v1.py]
  ├─ lit et transforme les lignes GP Mexique
  ├─ s’appuie sur reference/wikidata_query_results.csv pour compléter
  └─ utilise enrichments/ (wikidata_fetch, images, engines, patches)
            │
            ▼
(outputs)  → à définir / stabiliser (CSV final prêt pour visualisation)
```

> **Note** : Au moment de l’écriture, le projet n’écrit pas encore un CSV final standardisé dans `outputs/`.
> Lors de l’itération suivante, nous figerons la/les colonne(s) de sortie et le nom du fichier (ex. `gp_history_mexico_enriched.csv`).

---

## Commandes utiles

### Lancer le pipeline Mexique

```bash
PYTHONPATH=. python projects/gp_history/tools/run_mexico_full.py
```

### Lancer le builder directement

```bash
PYTHONPATH=. python projects/gp_history/tools/gp_history_builder_mexique_v1.py \
  --input projects/gp_history/data/gp_history/mexican_grand_prix.csv \
  --reference projects/gp_history/data/reference/wikidata_query_results.csv \
  --out projects/gp_history/outputs/gp_history_mexico_enriched.csv
```

> Si les options CLI ne sont pas encore supportées, édite les constantes chemins dans le script ou ajoute des `argparse` (voir Roadmap).

---

## Conventions d’E/S (I/O)

* **Entrées (brutes)** : `data/gp_history/<gp_name>.csv`
  Format attendu (à stabiliser) : au minimum *year, race_name, driver, team, result*, etc.
* **Références** : `data/reference/*.csv` (ex. tables Wikidata, mapping images).
* **Sorties (publiables)** : `outputs/*.csv` `outputs/*.json`
  → **Seuls** les artefacts finaux prêts pour la publication sont versionnés (exceptions `.gitignore`).

---

## Règles Git / Ignore

Ces règles sont gérées **au niveau racine** du repo ; rappel local :

* Ignorés : `__pycache__/`, `outputs/**` (par défaut), données temporaires.
* Conservés : `outputs/*.csv` `outputs/*.json` **si** explicitement utiles (publiables).
* Les fichiers **LLM** sont parqués dans `data/reference/llm/` et ne participent pas au pipeline.

---

## Qualité & Dépendances

* **Python ≥ 3.10** recommandé.
* Paquets typiques : `pandas`, `requests`, `python-dateutil` (selon les imports des `tools/enrichments`).
* Style : `ruff` + `black` (voir racine du repo) — exécuter au besoin avant commit.

---

## Roadmap courte

1. **Standardiser la sortie Mexique** → écrire `outputs/gp_history_mexico_enriched.csv` (schéma figé + doc).
2. **Gabarit multi‑GP** :

   * `data/gp_history/<gp_key>/raw.csv`
   * `data/gp_history/<gp_key>/patched.csv`
   * `outputs/gp_history_<gp_key>_enriched.csv`
3. **Paramétrer les chemins** avec `argparse` (input/reference/output) et logs clairs.
4. **(Optionnel)** Ajouter un **Makefile** :

   ```makefile
   gp_mexico: ## Build dataset for Mexican GP
   	PYTHONPATH=. python projects/gp_history/tools/run_mexico_full.py
   ```

---

## Maintenance

* Avant d’ajouter un nouveau GP, **cloner le pattern ‘mexico’** (builder + fichier `raw.csv`) et ajuster uniquement le mapping.
* Documenter toute colonne ajoutée/supprimée dans ce README (section I/O) et dans l’en‑tête du CSV de sortie.

---

## Historique

* 2025‑11‑11 : rangement des CSV Brésil en `data/reference/llm/` ; clarification des conventions ; README initial.
