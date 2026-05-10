# Dashboard F1 2026 — Plan d'implémentation

Tableau de bord statique consolidant les visualisations existantes (race chart, heatmap) + nouveaux widgets, alimenté par FastF1 et publié sur GitHub Pages.

**Périmètre** : saison 2026 uniquement.
**Refresh** : manuel, ~24h après chaque GP, via scripts Python locaux + `sync_to_docs.py`.

---

## Phase 1 — Socle (1-2 jours)

### 1.1 Design system commun
- [x] Extraire les variables CSS partagées (couleurs F1, typo, espacements, breakpoints) depuis `race_chart_builder/style.css`
- [x] Créer `docs/assets/dashboard.css` avec ces tokens et les styles de base (body, header, layout grid, cards)
- [x] Définir les composants réutilisables : `.dash-card`, `.dash-kpi`, `.dash-section`, `.dash-grid`
- [x] Documenter les couleurs d'écuries dans une seule source (`docs/assets/teams.json`) consommée par toutes les viz

### 1.2 Page d'accueil dashboard
- [x] Refondre `docs/index.html` (galerie statique → dashboard 2026)
- [x] Header : titre "F1 2026 — Dashboard", date du dernier GP joué, lien GitHub
- [x] Bandeau KPI : 4 indicateurs en haut
  - [x] Leader actuel (nom + points)
  - [x] Écart leader / 2e
  - [x] Dernier vainqueur (nom + GP)
  - [x] Prochain GP (nom + date + sprint ou non)
- [x] Grille de widgets en dessous (placeholders pour Phase 2)

### 1.3 Pipeline data dashboard
- [x] Créer `projects/dashboard/build_dashboard_data.py` — agrège le CSV race chart + le calendrier en un JSON
- [x] Définir le schéma `docs/data/dashboard_2026.json` (season, lastGp, nextGp, kpis)
- [x] Tests pytest minimaux pour le builder (`projects/dashboard/tests/`)
- [x] Créer `projects/dashboard/sync_to_docs.py` (copie additive web/ → docs/)

### 1.4 Manifest & navigation
- [x] `docs/assets/manifest.json` : liste des viz disponibles avec titre, route, statut available
- [x] Composant JS top-nav (`assets/navbar.js`) chargeant le manifest, sticky en haut, brand cliquable, liens actifs
- [x] Cartes de viz du dashboard rendues dynamiquement depuis le manifest
- [x] Navbar incluse sur race_chart_builder + season_summary_heatmap (retour dashboard)

---

## Phase 2 — Intégration des viz existantes (2-3 jours)

### 2.1 Race chart builder — ~~intégration embed~~
- [~] ~~Mode "embed", iframe sur le dashboard, lien "voir en détail"~~ — **abandonné** : rendu grossier et doublon visuel avec les pages dédiées. Le race chart reste accessible via la navbar.

### 2.2 Heatmap saison
- [x] La heatmap D3 a été mise à jour en 2026 (canonique : `projects/season_summary_heatmap/d3_dataviz/`)
- [x] `sync_to_docs.py` créé pour propager la heatmap dans `docs/season_summary_heatmap/`
- [x] Navbar + dashboard.css ajoutés au canonique pour cohérence visuelle entre pages
- [~] ~~Adapter au design system commun (refonte profonde)~~ — reporté
- [~] ~~Intégrer comme widget iframe sur le dashboard~~ — **abandonné** (cf. 2.1)

### 2.3 Synchronisation des données
- [x] Pipeline unifié : `projects/dashboard/build_all.py` orchestre tout en une commande
  - 1) `race_chart_builder_fastf1.py --season 2026` → outputs/CSV
  - 2) copie CSV → `web/data/`
  - 3) `lead_main.py --season 2026` → outputs/CSV (heatmap)
  - 4) copie CSV → `d3_dataviz/`
  - 5) `build_dashboard_data.py` → JSON
  - 6) sync_to_docs × 3 (race_chart, heatmap, dashboard)
  - Flag `--skip-fetch` pour rejouer la propagation sans toucher FastF1
- [~] ~~Consolider tous les CSV dans `docs/data/`~~ — **non fait** : chaque viz garde son CSV à côté de son HTML (pattern actuel suffisant). Le pipeline fait quand même la cohérence.

---

## Phase 3 — Nouveaux widgets (3-5 jours, à prioriser)

### 3.1 Standings live
- [x] Tableau classement pilotes (rang, nom, écurie, points, Δ dernier GP, écart leader)
- [x] Tableau classement constructeurs (agrégation par écurie)
- [x] Données calculées par `compute_standings` dans `build_dashboard_data.py`
- [x] Affichés directement sur l'accueil sous le bandeau KPI
- [~] ~~Tri/filtre, hover synchronisé avec les autres widgets~~ — reporté (priorité basse)

### 3.2 Vue par pilote (drill-down) — version (a) light
- [x] Clic sur une ligne du tableau pilotes → panneau détaillé inline sous la ligne
- [x] En-tête : photo + nom + écurie (avec couleur)
- [x] Mini-stats : rang, points, Δ dernier GP, écart leader
- [x] Sparkline cumul saison (SVG inline, pas de D3 sur le dashboard)
- [x] Tableau GP par GP : nom GP, gain au GP, cumul
- [~] ~~Podiums, victoires, position moyenne, qualifs~~ — non disponible avec le CSV actuel ; nécessite extension du builder côté `race_chart_builder` ou nouveau builder dédié

### 3.3 Remarques utilisateur
Tâches issues du feedback en cours de route.
- [x] **3.3.1 — Refonte layout de l'accueil (option A)** : grille 2 colonnes (classements à gauche 2/3, raccourcis viz à droite 1/3) avec onglets Pilotes/Constructeurs dans une seule carte
- [x] **3.3.2 — Countdown prochain GP** : tuile KPI dédiée, format adaptatif (jours / j+h / h+m), tick toutes les 60 s

### 3.4 Calendrier interactif
- [x] Liste des 22 GP avec statut (joué ✓ / prochain ▶ / à venir ·)
- [x] Marquage sprint (badge "S" jaune)
- [x] Vainqueur affiché à côté de chaque GP joué (couleur écurie)
- [x] Highlight du prochain GP (bordure jaune + badge "Prochain")
- [x] Auto-scroll sur le prochain GP au chargement
- [x] Compteur "X / 22 GP" dans l'en-tête de la carte
- [x] Calendrier ajouté au JSON par `build_dashboard_data.py`
- [~] ~~Lien direct vers détails du GP joué~~ — pas de page de détails GP encore (à voir si besoin plus tard)

### 3.5 Comparateur head-to-head
- [ ] Sélection 2 pilotes
- [ ] Tableau comparatif : qualifs gagnées, courses devant, écart points cumulé
- [ ] Visualisation timeline des batailles

### 3.6 Calendrier interactif — drill-down circuit
Rendre chaque ligne du calendrier cliquable, comme pour les pilotes, et ouvrir un panneau détaillé sur le circuit. **Toutes les données ci-dessous sont récupérables via FastF1 (vérifié).**

**Objectif** : transformer le simple listing en une fiche par GP.

**Audit des sources FastF1 (réalisé)**
| Donnée | API FastF1 | Notes |
|---|---|---|
| Nom officiel | `event.OfficialEventName` | ex. "FORMULA 1 CRYPTO.COM MIAMI GRAND PRIX 2026" |
| Pays + ville | `event.Country` / `event.Location` | dispo direct |
| Nombre de tours | `session.total_laps` | session = Race (R) |
| Format week-end | `event.EventFormat` | sprint_qualifying / conventional |
| Sessions + horaires | `event.Session1..5` + `*Date(Utc)` | utile pour le calendrier détaillé |
| Coordonnées des virages | `session.get_circuit_info().corners` | DataFrame X/Y/Number/Angle |
| Rotation du tracé | `session.get_circuit_info().rotation` | pour orienter correctement le SVG |
| Tracé complet du circuit | `lap.get_telemetry()['X','Y']` du meilleur tour | nuage de points qui dessine la trajectoire |
| Longueur du circuit | calculable depuis les distances cumulées de telemetry | non exposée directement |
| Meilleur tour en course | `session.laps.pick_fastest()` | pilote + temps + compound + lap n° |
| Vainqueur 2026 (post-course) | `session.results.iloc[0]` | déjà calculé dans `winners_by_gp` |
| Vainqueurs précédents | `fastf1.get_session(YYYY, gp, 'R').results.iloc[0]` | itérer sur 3-5 saisons passées |

**Données NON disponibles dans FastF1 (à compléter ailleurs si voulu)**
- Drapeau du pays → emoji depuis le pays, ou icône statique
- Lien Wikipedia → URL templatée depuis nom de circuit, ou Wikidata si on veut être propre

**Implémentation**
- [ ] Créer `projects/dashboard/build_circuits_data.py` séparé (le builder fera plusieurs requêtes FastF1, on évite d'alourdir `build_dashboard_data.py`)
- [ ] Output : `projects/dashboard/web/data/circuits_2026.json` indexé par nom de GP, contenant pour chaque circuit :
  - en-tête (nom, ville, pays, format),
  - caractéristiques (laps, longueur estimée, nb de virages),
  - records (meilleur tour 2026 + saisons précédentes si dispo),
  - top 3-5 vainqueurs récents,
  - tracé : tableau de points `[(x, y), ...]` + rotation pour rendu SVG inline
- [ ] Ajouter une étape au pipeline `build_all.py`
- [ ] Côté front : clic sur une ligne du calendrier → panneau drill-down inline (même pattern UX que la fiche pilote, avec mini SVG du circuit)

**Décisions à prendre avant de commencer**
- [ ] Inclure les vainqueurs historiques (3 dernières saisons ?) ou seulement 2026 ?
- [ ] Tracé SVG depuis telemetry (lent, ~30-60 s pour les 22 GP au build) ou tracé simplifié depuis seulement les coordonnées des virages ?
- [ ] Longueur calculée auto, ou laissée vide en attendant une source plus fiable ?

---

## Tâches transverses (à faire au fur et à mesure)

- [ ] Tests d'accessibilité sur la page dashboard (clavier, ARIA, contrastes)
- [ ] Responsive mobile (breakpoints 600px et 900px)
- [ ] Performance : lazy-load des widgets sous le pli
- [ ] README dashboard expliquant comment refresh la donnée après un GP
- [ ] Commit régulier après chaque sous-tâche cochée

---

## Bugs / dettes connus

- [ ] Collision de nommage "Spain" : FastF1 nomme à la fois Madrid (round 7) et Barcelona (round 14) "Spanish Grand Prix" → notre `_col_name` de `race_chart_builder` génère le même libellé pour les deux. À fixer avant le round 7 (mi-juin 2026) en ajoutant "Spain" aux pays multi-GP.

## Décisions à reprendre plus tard

- Pipeline GitHub Actions automatique (rejeté pour l'instant — refresh manuel suffit)
- Multi-saisons (rejeté — focus 2026)
- Backend dynamique (non — restera statique)
