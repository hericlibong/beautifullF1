# Dashboard F1 2026

Tableau de bord statique de la saison 2026 — page d'accueil du site (GitHub Pages).
Builders Python → JSON → front-end vanilla JS (modules ES6), publié dans `docs/`.

> Roadmap technique en cours : voir [`REFACTOR_PLAN.md`](REFACTOR_PLAN.md).
> Décisions produit / historique : voir [`PLAN.md`](PLAN.md).

## Après chaque Grand Prix (refresh des données)

Le refresh est **automatique** : le workflow `.github/workflows/refresh-after-gp.yml`
tourne lundi + mardi à 14h UTC après un GP, lance `build_all.py` et committe les
données (bot `github-actions`). `check_should_refresh.py` décide s'il doit s'exécuter.

Pour rejouer **manuellement** le refresh (depuis la racine du repo) :

```bash
python projects/dashboard/build_all.py            # fetch FastF1 → CSV → JSON → sync docs/
python projects/dashboard/build_all.py --skip-fetch   # re-propager sans re-fetcher FastF1
```

Étapes orchestrées : race chart CSV → heatmap CSV → `dashboard_2026.json`
+ `qualifying_2026.json` → `sync_to_docs.py` ×3.

**Vérifications après refresh :**
1. `pytest -m "not e2e"` — les builders produisent toujours des données valides.
2. Ouvrir le site en local (voir ci-dessous) et vérifier le dernier GP / classements.
3. Committer les deux copies (`projects/dashboard/web/` **et** `docs/`).

## Ajouter l'historique d'un circuit

Builder lent (APIs Ergast/f1db/Wikipedia, rate-limité) → **manuel**, hors workflow auto :

```bash
python projects/dashboard/build_gp_history.py \
    --circuit catalunya --year-from 1991 --year-to 2025 --label Espagne
```

Puis **mapper le nom de GP au circuitId** dans `web/assets/modules/constants.js`
(objet `GP_TO_CIRCUIT`), sinon l'onglet Calendrier n'affichera pas l'historique.
Enfin `python projects/dashboard/sync_to_docs.py`.

Le tracé + specs d'un circuit (télémétrie FastF1) se génèrent avec
`build_circuits_data.py` (manuel aussi).

## Architecture web/ ↔ docs/ (important)

Chaque fichier front vit **deux fois** :

- **Source canonique** : `projects/dashboard/web/` — **éditer ICI**.
- **Copie publiée** : `docs/` — produite par `sync_to_docs.py` (copie additive, ne supprime rien).

Après toute édition de `web/`, lancer `python projects/dashboard/sync_to_docs.py`
et committer les deux copies. Si on édite `docs/` directement (hot-test), reporter
le changement dans `web/` ou il sera écrasé au prochain sync.

### Front-end (web/assets/)

`index.html` charge `dashboard.js` en `<script type="module">` (modules ES6 natifs,
aucun bundler). Structure :

```
assets/
  dashboard.js              orchestrateur : fetch + KPI + câblage des modules
  modules/
    i18n.js                 FR/EN (t, setI18n, switcher)
    utils.js                formatage + fetchJson + bannière d'erreur
    constants.js            GP_TO_CIRCUIT, couleurs historiques
    render/
      standings.js          classements + drill-down pilote
      driver.js  duel.js  teammates.js
      calendar.js  circuit.js  history.js
      embed.js              viz embarquées (iframe)
```

**Chargement à la demande** : `circuits_2026.json`, `gp_history.json` (onglet
Calendrier) et `qualifying_2026.json` (onglet Coéquipiers) ne sont chargés qu'au
premier affichage de leur onglet — le chargement initial reste léger.

## Lancer le site en local

```bash
python -m http.server 8000 --directory docs   # http://localhost:8000
```

## Tests

```bash
pytest projects/dashboard/tests -m "not e2e"   # unitaires (builders, sync)

# E2E navigateur (Playwright) — une fois le navigateur installé :
python -m playwright install chromium
pytest projects/dashboard/tests/e2e -m e2e --no-cov
```

Les tests E2E servent `docs/` via un serveur local et vérifient le rendu réel
(onglets, drill-downs, FR/EN, embed, responsive 375/768/1024 px, bannière d'erreur).
CI : `python-app.yml` lance ruff + black + pytest (unitaires puis E2E).
