# Race Chart Builder — Améliorations

Suivi des tâches pour la visualisation `race_chart_builder` (F1 2026).

## UX / interaction
- [~] ~~Recherche/filtre texte dans la légende~~ (abandonnée — redondante avec la légende cliquable)
- [x] Filtres rapides : "Top 5", "Par écurie"
- [x] Sélection au clic sur la ligne dans le graphique (pas seulement la légende)
- [x] URL partageable (`#drivers=Leclerc,Norris`)
- [x] Slider de progression pour scrubber l'animation manuellement

## Lisibilité
- [x] Anti-collision des endcaps (force-layout vertical en fin de courbe)
- [x] Switch échelle Y linéaire / log
- [x] Mode "écart au leader" (pts - max(pts))
- [x] Marqueurs de sprint distincts (icône ou trait pointillé)

## Données
- [x] Tooltip enrichi : position au GP, écart au leader, gain ce GP
- [~] ~~Mini sparkline par pilote dans la légende~~ (abandonnée — peu d'apport visuel)
- [~] ~~Sélecteur de saison (multi-saisons)~~ (abandonnée — pas de CSV historiques alignés)

## Technique
- [x] Responsive (mobile : adaptation marges, légende, contrôles, axes)
- [x] Accessibilité : navigation clavier légende, ARIA, contrastes
- [x] Lazy-load des photos pilotes
