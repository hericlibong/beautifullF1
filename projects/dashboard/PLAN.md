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

### 2.1 Race chart builder
- [ ] Ajouter un mode "embed" à `race_chart_builder` (sans header propre, hauteur réduite)
- [ ] Intégrer dans le dashboard via `<iframe>` ou inclusion JS directe
- [ ] Lien "voir en détail" → page complète

### 2.2 Heatmap saison
- [ ] Mettre à jour la heatmap D3 existante avec les données 2026 (`projects/season_summary_heatmap`)
- [ ] Adapter au design system commun
- [ ] Intégrer comme widget dashboard
- [ ] Lien "voir en détail"

### 2.3 Synchronisation des données
- [ ] Faire en sorte que `build_dashboard_data.py` déclenche aussi les builders race_chart et heatmap (pipeline unifié)
- [ ] Vérifier que toutes les viz pointent vers les CSV consolidés (`docs/data/`)

---

## Phase 3 — Nouveaux widgets (3-5 jours, à prioriser)

### 3.1 Standings live
- [ ] Tableau classement pilotes (cumul + delta vs GP précédent)
- [ ] Tableau classement constructeurs
- [ ] Tri/filtre, hover synchronisé avec les autres widgets

### 3.2 Vue par pilote (drill-down)
- [ ] Sélection d'un pilote → fiche détaillée
- [ ] Mini-stats : meilleur résultat, podiums, victoires, position moyenne
- [ ] Sparkline de progression
- [ ] Historique GP par GP

### 3.3 Calendrier interactif
- [ ] Liste des 24 GP avec statut (joué, à venir)
- [ ] Marquage sprint
- [ ] Lien direct vers les détails du GP joué (résultats)

### 3.4 Comparateur head-to-head
- [ ] Sélection 2 pilotes
- [ ] Tableau comparatif : qualifs gagnées, courses devant, écart points cumulé
- [ ] Visualisation timeline des batailles

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
