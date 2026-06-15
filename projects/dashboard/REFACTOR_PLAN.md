# Refactorisation & nettoyage du dashboard — Roadmap

> Branche dédiée : `refactor/dashboard-cleanup` — mergée vers `main` une fois toutes les cases cochées.
> Source de vérité de l'avancement de ce chantier. Mettre à jour les cases au fil de l'eau.

## Contexte

Le dashboard 2026 est fonctionnellement abouti mais une évaluation a révélé 6 faiblesses qui menacent sa maintenabilité sur la durée de la saison :

1. **Tests insuffisants** — 3 tests unitaires Python, zéro test front-end.
2. **Responsive partiel** — certaines zones (onglets/drill-downs) déséquilibrées sur petits écrans.
3. **`dashboard.js` monolithique** — 1294 lignes, IIFE + fonctions globales, non testable. **Priorité.**
4. **Pas de documentation opérationnelle** — aucun README de refresh après GP.
5. **Erreurs silencieuses** — `.catch(() => null)` masque les données manquantes.
6. **Performance non mesurée** — `circuits_2026.json` 152 Ko chargé d'emblée, rien minifié, pas de lazy-load.

**Contrainte non négociable** : le dashboard est réactualisé **chaque lundi (+ mardi) après chaque GP** via `refresh-after-gp.yml` → `build_all.py` → `sync_to_docs.py`. `docs/` est servi par GitHub Pages **sans bundler ni build step**. La refacto ne doit pas introduire de Node/npm dans le chemin de refresh, et `sync_to_docs.py` (copie récursive de `web/`) doit continuer à tout propager.

## Décisions actées

- **Tests E2E** : `pytest-playwright` (100% Python, intégré à pytest + CI existants).
- **Refacto JS** : modules ES6 natifs (`<script type="module">`), aucun bundler.
- **Branche** : `refactor/dashboard-cleanup`, merge en fin de chantier.

---

## Roadmap

### Étape 0 — Mise en place
- [x] Créer la branche `refactor/dashboard-cleanup`
- [x] Créer ce `REFACTOR_PLAN.md`
- [ ] Capturer un état de référence avant refacto (screenshots desktop + mobile des 5 onglets + drill-downs)

### Étape 1 — Filet de sécurité Python (tests unitaires d'abord)
- [ ] Étendre `tests/test_build.py` → `compute_standings`, `compute_kpis`, calendrier, collision "Spain" (round 7 vs 14)
- [ ] `tests/test_qualifying.py` — structure `qualifying_2026.json`
- [ ] `tests/test_gp_history.py` — schéma `gp_history.json`
- [ ] `tests/test_sync.py` — `sync_to_docs.py` copie tout `web/` (modules `.js` inclus) vers `docs/`
- [ ] `pytest projects/dashboard/tests -q` vert, couverture en hausse

### Étape 2 — Refacto `dashboard.js` en modules ES6 (PRIORITÉ)
Découpage cible sous `web/assets/` : `dashboard.js` (orchestrateur) + `modules/{i18n,utils,constants}.js` + `modules/render/{standings,driver,duel,teammates,circuit,history,calendar,embed}.js`.
- [ ] Extraire `i18n.js`, `utils.js`, `constants.js` (briques de base) + `export`
- [ ] Extraire chaque `render/*` avec `import` explicite des dépendances
- [ ] Réduire `dashboard.js` à l'orchestrateur (fetch + câblage + restauration d'état)
- [ ] `index.html` → `<script type="module" src="assets/dashboard.js">`
- [ ] `sync_to_docs.py` puis vérifier que tous les modules arrivent dans `docs/`
- [ ] Vérif manuelle : 5 onglets, 2 drill-downs, switch FR/EN, embed viz, countdown identiques

### Étape 3 — Tests E2E (pytest-playwright)
- [ ] `pytest-playwright` dans `requirements.txt` (+ note `playwright install chromium`)
- [ ] `tests/e2e/conftest.py` — fixture serveur `http.server` + page Playwright
- [ ] `tests/e2e/test_dashboard.py` — KPI, 5 onglets, drill-down pilote/circuit, FR/EN, embed
- [ ] `tests/e2e/test_responsive.py` — pas de débordement à 375/768/1024 px
- [ ] Câbler l'E2E au CI (`python-app.yml`), **pas** dans `refresh-after-gp.yml`

### Étape 4 — Responsive
- [ ] Audit à 375/768/1024 px de chaque onglet + drill-down
- [ ] Corriger `dashboard.css` : `dash-main-grid`, tableaux, duel empilé mobile, timeline, scatter
- [ ] Vérifier/compléter les breakpoints (600/900px)
- [ ] `test_responsive.py` vert + comparaison visuelle

### Étape 5 — Gestion d'erreur visible
- [ ] `fetchJson(url, {required})` dans `utils.js` (bannière UI si ressource requise manquante)
- [ ] Remplacer les `.catch(() => null)` épars
- [ ] État "données indisponibles" explicite par widget
- [ ] Test E2E : ressource manquante → bannière visible

### Étape 6 — Performance
- [ ] Baseline Lighthouse (desktop + mobile), consignée ici
- [ ] `circuits_2026.json` + `gp_history.json` en chargement à la demande (au 1er clic circuit)
- [ ] Vérifier `loading="lazy"` partout
- [ ] Trancher la minification selon la baseline (optionnelle, hors chemin de refresh)
- [ ] Lighthouse post-optim vs baseline

### Étape 7 — Documentation
- [ ] `projects/dashboard/README.md` (refresh après GP, ajout circuit, archi web/↔docs/, lancer les tests)
- [ ] Mettre à jour `PLAN.md` (tâches transverses) et `CLAUDE.md` (structure modules ES6)

### Étape 8 — Clôture
- [ ] `pytest` complet vert + `ruff check .` + `black --check .`
- [ ] `build_all.py --skip-fetch` OK (propagation intacte)
- [ ] Toutes les cases cochées
- [ ] Merge `refactor/dashboard-cleanup` → `main`

---

## Mesures Lighthouse (à remplir étape 6)

| | Avant | Après |
|---|---|---|
| Performance (desktop) | — | — |
| Performance (mobile) | — | — |

## Risques & garde-fous

- **Casser le refresh** → `test_sync.py` + `build_all.py --skip-fetch` à chaque étape, zéro Node dans le refresh.
- **Régression visuelle** → screenshots de référence + revue manuelle + E2E.
- **Modules ES6 / chemins** → `import` relatifs, testés en local (`http.server`) et compatibles GitHub Pages.
