# Dashboard F1 2026 — Plan d'implémentation

Tableau de bord statique consolidant les visualisations existantes (race chart, heatmap) + nouveaux widgets, alimenté par FastF1 et publié sur GitHub Pages.

**Périmètre** : saison 2026 uniquement.
**Refresh** : manuel, ~24h après chaque GP, via scripts Python locaux + `sync_to_docs.py`.

---

## Phase 1 — Socle (1-2 jours)

### 1.1 Design system commun
- [ ] Extraire les variables CSS partagées (couleurs F1, typo, espacements, breakpoints) depuis `race_chart_builder/style.css`
- [ ] Créer `docs/assets/dashboard.css` avec ces tokens et les styles de base (body, header, layout grid, cards)
- [ ] Définir les composants réutilisables : `.dash-card`, `.dash-kpi`, `.dash-section`, `.dash-grid`
- [ ] Documenter les couleurs d'écuries dans une seule source (`docs/assets/teams.json`) consommée par toutes les viz

### 1.2 Page d'accueil dashboard
- [ ] Refondre `docs/index.html` (galerie statique → dashboard 2026)
- [ ] Header : titre "F1 2026 — Dashboard", date du dernier GP joué, lien GitHub
- [ ] Bandeau KPI : 4 indicateurs en haut
  - [ ] Leader actuel (nom + points)
  - [ ] Écart leader / 2e
  - [ ] Dernier vainqueur (nom + GP)
  - [ ] Prochain GP (nom + date + sprint ou non)
- [ ] Grille de widgets en dessous (placeholders pour Phase 2)

### 1.3 Pipeline data dashboard
- [ ] Créer `projects/dashboard/build_dashboard_data.py` — script qui agrège tous les outputs en un seul JSON consommé par le front
- [ ] Définir le schéma `docs/data/dashboard_2026.json` :
  ```
  { season, lastGp, nextGp, kpis, drivers, teams, calendar }
  ```
- [ ] Tests pytest minimaux pour le builder (`projects/dashboard/tests/`)
- [ ] Adapter `sync_to_docs.py` (ou créer un `sync_dashboard.py`) pour propager `projects/dashboard/web/` → `docs/`

### 1.4 Manifest & navigation
- [ ] `docs/assets/manifest.json` : liste des viz disponibles avec titre, vignette, route
- [ ] Composant JS de navigation latérale (ou top nav) chargeant le manifest
- [ ] Lien dashboard ↔ viz détaillées (race chart, heatmap) avec retour

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

## Décisions à reprendre plus tard

- Pipeline GitHub Actions automatique (rejeté pour l'instant — refresh manuel suffit)
- Multi-saisons (rejeté — focus 2026)
- Backend dynamique (non — restera statique)
