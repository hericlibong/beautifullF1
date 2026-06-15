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

### Étape 1 — Filet de sécurité Python (tests unitaires d'abord) ✅
- [x] Étendre `tests/test_build.py` → `compute_standings`, `compute_kpis`, calendrier, collision "Spain" (round 7 vs 14)
- [x] `tests/test_qualifying.py` — `format_lap`, `build_teammate_pairs` (logique duels)
- [x] `tests/test_gp_history.py` — `engine_for`, `merge_write` (read-merge-write par circuit)
- [x] `tests/test_sync.py` — `sync_to_docs.py` copie tout `web/` (modules `.js` inclus) vers `docs/`
- [x] `pytest projects/dashboard/tests -q` vert (3 → 26 tests)

### Étape 2 — Refacto `dashboard.js` en modules ES6 (PRIORITÉ) ✅
Découpage sous `web/assets/` : `dashboard.js` (orchestrateur, 1294 → ~190 lignes) + `modules/{i18n,utils,constants}.js` + `modules/render/{standings,driver,duel,teammates,circuit,history,calendar,embed}.js`.
- [x] Extraire `i18n.js`, `utils.js`, `constants.js` (briques de base) + `export`
- [x] Extraire chaque `render/*` avec `import` explicite des dépendances
- [x] Réduire `dashboard.js` à l'orchestrateur (fetch + câblage + restauration d'état)
- [x] `index.html` → `<script type="module" src="assets/dashboard.js">`
- [x] `sync_to_docs.py` puis vérifier que tous les modules arrivent dans `docs/`
- [x] Vérif iso-fonctionnelle via E2E navigateur (8/8 verts) : onglets, drill-downs, FR/EN, embed
- [x] Nettoyage : variables mortes supprimées (`avg/scored/ties` dans le duel)

### Étape 3 — Tests E2E (pytest-playwright) ✅
- [x] `pytest-playwright` (+ deps) dans `requirements.txt`
- [x] `tests/e2e/conftest.py` — fixture serveur `http.server` sur `docs/` + page Playwright
- [x] `tests/e2e/test_dashboard.py` — KPI, 5 onglets, drill-down pilote/circuit+histoire, FR/EN, embed (8/8 verts)
- [x] Marqueur `e2e` déclaré dans `pyproject.toml`
- [x] Câbler au CI `python-app.yml` : pytest réactivé (unitaires + E2E avec `playwright install`), **pas** dans `refresh-after-gp.yml`
- [→] `tests/e2e/test_responsive.py` — écrit, livré avec l'étape 4 (pilote les correctifs CSS)

### Étape 4 — Responsive ✅
- [x] Audit à 375/768/1024 px de chaque onglet + drill-down (via `test_responsive.py`) → débordements isolés à 375px
- [x] Corriger `dashboard.css` : `min-width:0` sur les cartes (items de grille), onglets `flex-wrap`, scroll interne des panneaux larges, pickers duel empilés
- [x] Breakpoints 600/900px complétés
- [x] `test_responsive.py` vert (6/6) — suite E2E complète 14/14

### Étape 5 — Gestion d'erreur visible ✅
- [x] `fetchJson(url, {required, fallback})` + `showErrorBanner()` dans `utils.js` (message bilingue indépendant de l'i18n)
- [x] `Promise.all` de l'orchestrateur réécrit avec `fetchJson` (requis vs optionnel), `.catch(() => null)` supprimés
- [x] Dégradation propre par widget (teammates "indisponible" déjà géré, circuits/duel non bloquants)
- [x] Tests E2E : ressource requise manquante → bannière ; ressource optionnelle → dégradation sans bannière

### Étape 6 — Performance ✅
- [x] Baseline mesurée (poids du chargement initial via Playwright — choisi plutôt que Lighthouse CLI pour éviter d'introduire du Node ; mesure directement le problème identifié)
- [x] `circuits_2026.json` (152 Ko) + `gp_history.json` (27 Ko) en chargement à la demande (1er affichage onglet Calendrier)
- [x] `qualifying_2026.json` (80 Ko) en chargement à la demande (1er affichage onglet Coéquipiers)
- [x] `loading="lazy"` déjà présent sur toutes les images (vérifié)
- [x] Minification : **écartée** — gain marginal vs réintroduction d'un build step (contraire à la contrainte no-build / refresh auto)

### Étape 7 — Documentation ✅
- [x] `projects/dashboard/README.md` (refresh après GP, ajout circuit, archi web/↔docs/, lancer les tests)
- [x] `PLAN.md` (tâches transverses cochées) et `CLAUDE.md` (structure modules ES6, fetchJson, lazy-load, tests) mis à jour

### Étape 8 — Clôture ✅
- [x] `pytest` complet vert (26 unitaires + 16 E2E) + `ruff check .` + `black --check .`
- [x] `build_all.py --skip-fetch` OK, zéro dérive de données (propagation intacte)
- [x] Nettoyage annexe : variable morte + format dans `build_gp_history.py`
- [x] Toutes les cases cochées
- [x] Merge `refactor/dashboard-cleanup` → `main`

---

## Mesures de performance (étape 6)

Poids des ressources chargées au **premier rendu** (onglet Pilotes), mesuré via Playwright sur `docs/` servi localement :

| | Avant | Après |
|---|---|---|
| Poids initial total | 399,9 Ko | **148,3 Ko** (−63 %) |
| `circuits_2026.json` (152 Ko) | chargé d'emblée | différé (onglet Calendrier) |
| `qualifying_2026.json` (80 Ko) | chargé d'emblée | différé (onglet Coéquipiers) |
| `gp_history.json` (27 Ko) | chargé d'emblée | différé (onglet Calendrier) |

## Risques & garde-fous

- **Casser le refresh** → `test_sync.py` + `build_all.py --skip-fetch` à chaque étape, zéro Node dans le refresh.
- **Régression visuelle** → screenshots de référence + revue manuelle + E2E.
- **Modules ES6 / chemins** → `import` relatifs, testés en local (`http.server`) et compatibles GitHub Pages.
