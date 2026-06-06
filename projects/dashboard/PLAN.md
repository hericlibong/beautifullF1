# Dashboard F1 2026 — Plan d'implémentation

Tableau de bord statique consolidant les visualisations existantes (race chart, heatmap) + nouveaux widgets, alimenté par FastF1 et publié sur GitHub Pages.

**Périmètre** : saison 2026 uniquement.
**Refresh** : automatique via GitHub Actions (`.github/workflows/refresh-after-gp.yml`), lundi + mardi 14h UTC après chaque GP. Trigger manuel possible depuis l'onglet Actions du repo.

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

### 3.5 Comparateur head-to-head — version (a) light
- [x] 4e onglet "Duel" dans la carte Classements
- [x] Deux dropdowns natifs alimentés par la liste des pilotes
- [x] Cartes pilotes côte à côte (couleur écurie, points totaux, moyenne, rang) + écart au centre
- [x] Score H2H par GP (qui a marqué + de pts à chaque course) avec barre proportionnelle
- [x] Mini line chart SVG : écart cumulé GP par GP
- [x] Tableau détaillé GP par GP : gain de chacun + Δ
- [~] ~~Qualifs gagnées, position d'arrivée par GP~~ — non disponible avec le CSV actuel ; nécessiterait extension du builder (cf. 3.6)

### 3.5.bis Onglet "Coéquipiers · Qualifs" — H2H qualif
- [x] Nouveau builder `build_qualifying_data.py` (FastF1 → temps de référence par pilote, gap au millième, compteur Q3)
- [x] Sprint Qualifs incluses (fallback meilleur tour via `laps` car Ergast ne sert pas la SQ)
- [x] Output `docs/data/qualifying_2026.json` + ajout au pipeline `build_all.py`
- [x] Onglet "Coéquipiers · Qualifs" : dropdown écurie (défaut = leader constructeurs), filtres Tous / Qualifs / Sprint Qualifs
- [x] Timeline SVG centrée sur 0 : cercle = Quali, losange = Sprint Quali, position = gap signé, tooltip au survol

### 3.7 Viz embarquées dans le cadre du dashboard
- [x] Mode embed (`?embed=1`) sur Race Line + Heatmap (header/footer/navbar masqués, fond transparent, SVG hauteur naturelle, pas de double cadre)
- [x] Carte "Visualisations" → ouvre la viz DANS le cadre principal (iframe), navbar header → page indépendante (double accès)
- [x] Iframe auto-redimensionnée à la hauteur du contenu (lecture same-origin + re-mesure + ResizeObserver) → aucun scroll interne
- [x] Bouton "← Retour" pour revenir aux onglets

## Hors plan — livré en cours de route
- [x] **Cleanup repo** : 17 fichiers obsolètes supprimés (~4000 lignes mortes)
- [x] **Refresh auto GitHub Actions** : `.github/workflows/refresh-after-gp.yml` (lundi + mardi 14h UTC) + `check_should_refresh.py` ; tests pytest avant commit
- [x] **driver_images.json** : fallback photos pilotes

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

**Implémentation — FAIT ✅**
- [x] `projects/dashboard/build_circuits_data.py` séparé (manuel, lent ; PAS dans le workflow auto car ~22 circuits × télémétrie)
- [x] Output `circuits_2026.json` (web/ + docs/) indexé par nom de GP : caractéristiques (longueur calculée, virages, tours), record du meilleur tour, 3 derniers vainqueurs, tracé `[(x,y)]` normalisé 0-1000 + rotation appliquée, sous-échantillonné à 120 points
- [x] Côté front : clic sur une ligne du calendrier → panneau inline (tracé SVG à gauche, specs + record + vainqueur 2026 + 3 derniers vainqueurs à droite)
- [x] Vainqueur 2026 lu côté front depuis le dashboard JSON (`calendar[].winner`), pas dans le builder circuits

**Décisions prises**
- [x] Vainqueurs historiques : **3 dernières saisons** (2023-2025)
- [x] Tracé SVG depuis **télémétrie complète** d'une saison réelle (fallback 2025→2024→2023 ; 2026 simulée n'a pas la position GPS)
- [x] Longueur **calculée auto** depuis la distance cumulée de la télémétrie

**Limites connues (acceptées)**
- Madrid (round 14, nouveau circuit) : fiche volontairement vide, pas de tracé historique
- Barcelona (round 7) : tracé issu de la saison "Spain" récente (Barcelona)

---

#### 3.6.bis — Enrichissement historique multi-décennies (gp_history)

En complément de FastF1 (qui couvre l'ère récente avec précision technique), `projects/gp_history/` contient déjà des CSV historiques curatés via LLM, qui remontent jusqu'aux années 1960. Ces données apportent une **profondeur narrative** inaccessible à FastF1 seul.

**État existant**
- ✅ `projects/gp_history/data/gp_history/mexican_grand_prix.csv` — 25 lignes, schéma anglais : `Year, GP, Circuit, Winner, WinnerWinsOnThisGP, WinnerGridPos, Constructor, EngineManufacturer, ConstructorWinsOnThisGP, P2, P3, SeasonChampion, Trophies, WinnerImageURL`
- ✅ Pipeline Python : `gp_history_builder_mexique_v1.py` + `run_mexico_full.py`, enrichissement Wikidata
- ⚠️ CSV Australie (chez l'utilisateur) avec **schéma français divergent** : `Year, Circuit, Vainqueur, flag_winner, Nb victoires (vainqueur), Start_position_winner, Constructeur, nb_victoires_team, Motoriste, second, third, world champio, icones, image_winner`
- ⚠️ Visualisation Flourish "scatter year × cumulative wins, color = team" comme proof-of-concept

**Intégration au drill-down circuit (3.6 principal)**
Dans le panneau drill-down d'un GP, prévoir 2 zones :
- **Zone "Saison en cours" (FastF1)** : tracé SVG, longueur, record du tour, vainqueur 2026
- **Zone "Histoire" (gp_history)** : timeline année × vainqueur, comptage des victoires par écurie, photo du vainqueur historique au survol — équivalent inline du Flourish actuel

**Sous-tâches**
- [ ] **Harmoniser le schéma** : choisir une convention unique (anglais recommandé pour s'aligner sur le Mexique existant et FastF1) ; convertir le CSV Australie au format Mexique
- [ ] **Importer le CSV Australie** dans `projects/gp_history/data/gp_history/australian_grand_prix.csv` après conversion de schéma
- [ ] **Étendre le pipeline `gp_history`** pour générer un fichier de sortie consommable par le dashboard : `docs/data/gp_history.json` indexé par GP, avec pour chaque GP la liste `[{year, winner, team, grid, p2, p3, champion, photo}, ...]`
- [ ] **Couverture progressive** : ajouter les CSV au fur et à mesure (Mexique ✅, Australie en cours, puis circuits historiques majeurs : Monaco, Italy, Britain, Belgium…). Le drill-down affiche "Données historiques indisponibles" pour les circuits non encore couverts
- [ ] **Composant front "timeline historique"** dans le drill-down : graphe scatter inline en SVG (Year × victoires cumulées, couleur écurie), avec tooltip au survol affichant photo + détails — réplique simplifiée du Flourish
- [ ] **À terme** : remplacer la curation LLM par un builder semi-automatique (Wikidata + scraping ponctuel des résultats officiels), en gardant une étape de relecture manuelle

**Décisions à arbitrer**
- [ ] Schéma cible définitif (recommandation : anglais, format Mexique) — qui implique de convertir le CSV Australie
- [ ] Profondeur historique par GP : tout disponible, ou plafond (ex. depuis 1985) ?
- [ ] La viz Flourish standalone existante : la remplacer par la version embarquée du dashboard, ou la garder comme produit dérivé indépendant ?
- [ ] Sortie : un seul gros JSON `gp_history.json` ou un fichier par circuit (`docs/data/gp_history/{circuit_slug}.json`) ?

---

## Tâches transverses (à faire au fur et à mesure)

- [ ] Tests d'accessibilité sur la page dashboard (clavier, ARIA, contrastes)
- [ ] Responsive mobile (breakpoints 600px et 900px)
- [ ] Performance : lazy-load des widgets sous le pli
- [ ] README dashboard expliquant comment refresh la donnée après un GP
- [ ] Commit régulier après chaque sous-tâche cochée

---

## Bugs / dettes connus

- [x] **Collision "Spain"** — partiellement réglé côté calendrier/dashboard/circuits : round 7 = Barcelona (name "Spain"), round 14 = Madrid (name "Spain - Madrid", fiche vide). ⚠️ Reste à traiter dans `race_chart_builder._col_name` ET `season_summary_heatmap` avant que Madrid soit couru (round 14, sept. 2026), sinon les deux GP partageront la même colonne CSV.
- [x] **Photos pilotes vides sur le site déployé** — réglé via `projects/dashboard/driver_images.json` (mapping abréviation FIA → URL), utilisé en fallback quand FastF1 ne fournit pas `HeadshotUrl` (runner Linux).

## Décisions à reprendre plus tard

- Pipeline GitHub Actions automatique (rejeté pour l'instant — refresh manuel suffit)
- Multi-saisons (rejeté — focus 2026)
- Backend dynamique (non — restera statique)
