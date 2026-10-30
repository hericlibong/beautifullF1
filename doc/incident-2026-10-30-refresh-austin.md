# Austin non publié : diagnostic, correction et preuves — 30/10/2026

## Constat et cause établie

Le site servait toujours les données de Singapour du 12/10. Austin (25/10)
restait le prochain GP et le compte à rebours affichait indéfiniment « En cours ».
Le bandeau signalait correctement qu'Austin manquait aux données publiées.

Les quatre runs planifiés du 26 au 29/10 ont bien démarré. Le cron n'était
donc pas la cause de cet incident. Le validateur a refusé de publier :

- race chart : 17 GP, arrêté à Singapour ;
- heatmap : 18 GP, Austin présent ;
- des points de sprint avaient également disparu du race chart le 29/10.

Preuves : [premier échec du 26/10](https://github.com/hericlibong/beautifullF1/actions/runs/40391626548)
et [échec du 29/10](https://github.com/hericlibong/beautifullF1/actions/runs/40942541624).

Le race chart appelait `race.load()` et `sprint.load()` avec tours, télémétrie,
météo et messages, bien que seuls les classements soient nécessaires. Les
journaux montrent le live timing indisponible, puis trois chargements vides
d'Austin. La heatmap utilisait un chargement limité aux résultats et récupérait
Austin dans le même run. Le poste local a également confirmé la disponibilité
des 22 résultats d'Austin. La cause précise des réponses réseau vides n'est
pas exposée par FastF1 ; aucune saturation ou limite de débit n'est affirmée.

Deux défauts aggravaient la situation : un sprint en échec était silencieusement
remplacé par zéro point ; le nouveau GP manquant était ignoré tant qu'il
n'existait pas dans l'ancien CSV. Enfin, le cache déclaré dans le workflow
(`~/.fastf1_cache`) n'était pas activé par les builders : les runs indiquaient
qu'aucun répertoire n'était à sauvegarder.

## Fichiers de code créés ou modifiés

| Fichier | Raison et comportement obtenu |
|---|---|
| `projects/session_results.py` (créé) | Chargement commun léger, trois tentatives espacées de 5 puis 10 s, validation des identités/points/classement, activation du vrai cache |
| `projects/race_chart_builder/race_chart_builder_fastf1.py` | Utilisation du chargeur commun ; un GP ou sprint attendu indisponible interrompt la reconstruction ; aucune perte silencieuse |
| `projects/season_summary_heatmap/exporter_lead.py` | Même chargeur ; exclusion explicite des courses futures ; échec explicite d'une course passée indisponible |
| `projects/dashboard/validate_outputs.py` | Comparaison aux GP attendus à la date du contrôle, avec délai d'un jour ; deux builders également périmés ne suffisent plus à valider |
| `projects/dashboard/build_all.py` | Actualisation du calendrier et création préalable du répertoire de cache |
| `projects/dashboard/fetch_calendar.py` | Conservation de l'heure UTC officielle de chaque course |
| `projects/dashboard/calendar_2026.json` | Horaires FastF1 actualisés ; Mexico le 01/11 à 20:00 UTC |
| `projects/dashboard/build_dashboard_data.py` | Transmission de `raceStartUtc` au prochain GP |
| `projects/dashboard/web/assets/dashboard.js` | Compte à rebours fondé sur l'horaire officiel, au lieu de 14 h locale systématique |
| `projects/dashboard/web/assets/modules/utils.js` | Revalidation HTTP des JSON ; après 24 h, une course passée attend ses résultats et n'est plus « En cours » indéfiniment |
| `projects/dashboard/web/assets/i18n.json` | Texte « Résultats en attente » en français et anglais |
| `docs/assets/dashboard.js`, `docs/assets/modules/utils.js`, `docs/assets/i18n.json` | Miroirs des trois sources front-end, synchronisés pour Pages |
| `projects/dashboard/verify_publication.py` (créé) | Vérification des quatre fichiers de données réellement servis par Pages, avec attente de déploiement et comparaison de contenu normalisée CRLF/LF |
| `.github/workflows/refresh-after-gp.yml` | Quatre contrôles quotidiens (02:23, 08:23, 14:23, 20:23 UTC), trois tentatives de pipeline, cache actif `.cache/fastf1`, diagnostics conservés 14 jours, contrôle public même sans reconstruction |
| `.github/workflows/python-app.yml` | Image Ubuntu 24.04 explicite : Playwright 1.60 refuse Ubuntu 26, devenu `ubuntu-latest`. Ce second défaut a été découvert pendant la validation distante et empêchait les tests navigateur en CI |
| `.gitignore` | Exclusion du cache de données réseau `.cache/` |

Les nouveaux tests rejouent les symptômes :

- `projects/dashboard/tests/test_session_results.py` (créé) : réponse vide
  retentée, chargement sans télémétrie, points invalides et sprint absent ;
- `projects/dashboard/tests/test_validate_outputs.py` : deux sources périmées
  à Singapour ne peuvent pas valider Austin ; Mexico futur reste exclu ;
- `projects/dashboard/tests/test_verify_publication.py` (créé) : une ancienne
  version publique doit échouer même si le dépôt est correct ;
- `projects/dashboard/tests/e2e/test_dashboard.py` : course passée sans
  « ongoing » permanent et compte à rebours basé sur l'heure UTC officielle.

## Fichiers de données régénérés

La reconstruction a actualisé ces dix sorties, sans saisie manuelle des points :

- `projects/race_chart_builder/outputs/f1_race_chart_fastf1_2026.csv` ;
- `projects/race_chart_builder/web/data/f1_race_chart_fastf1_2026.csv` ;
- `docs/race_chart_builder/data/f1_race_chart_fastf1_2026.csv` ;
- `projects/season_summary_heatmap/outputs/f1_2026_leaders_heatmap.csv` ;
- `projects/season_summary_heatmap/d3_dataviz/f1_2026_leaders_heatmap.csv` ;
- `docs/season_summary_heatmap/f1_2026_leaders_heatmap.csv` ;
- `projects/dashboard/web/data/dashboard_2026.json` ;
- `docs/data/dashboard_2026.json` ;
- `projects/dashboard/web/data/qualifying_2026.json` ;
- `docs/data/qualifying_2026.json`.

Le présent document est nouveau. Le rapport
`doc/resolution-fraicheur-des-donnees.md` reçoit un renvoi vers cet incident
afin de conserver une trace continue des corrections successives.

## Vérifications avant publication

- Reconstruction complète depuis FastF1 réussie et cohérence des trois sorties
  confirmée par le validateur.
- Austin : 18e GP disputé, vainqueur Andrea Kimi Antonelli ; 101 points ajoutés
  (25, 18, 15, 12, 10, 8, 6, 4, 2, 1). Les points de tous les sprints sont inclus.
- Prochain GP : Mexico, dimanche 01/11 à 20:00 UTC, soit 21 h à Paris.
  Les premiers essais du vendredi 30/10 sont prévus à 18:30 UTC / 19 h 30 Paris
  selon le calendrier FastF1 consulté.
- 92 tests unitaires dashboard réussis.
- 20 tests navigateur Chromium réussis, dont les deux scénarios ajoutés pour
  la course passée et le compte à rebours officiel de Mexico.

## Publication et validation opérationnelle

- Correction et données publiées dans le commit `66d23b8`.
- [Déploiement Pages initial](https://github.com/hericlibong/beautifullF1/actions/runs/41035880736)
  réussi ; les quatre fichiers publics ont ensuite été comparés aux fichiers
  validés avec succès.
- Contrôle Chromium sur le site public : Austin figure parmi les GP joués,
  le bandeau est absent et la tuile du prochain GP indique Mexico.
- [Reconstruction complète distante](https://github.com/hericlibong/beautifullF1/actions/runs/41035898961)
  réussie en 2 min 43 s : tests, pipeline, validation et vérification publique.
  Les fichiers reconstruits sous Linux sont identiques à ceux préparés sous
  Windows : aucun nouveau changement à pousser. Le cache est réellement
  sauvegardé (`fastf1-results-Linux-41035898961`).
- La CI qualité a validé Ruff, Black et les tests unitaires, puis a identifié
  l'incompatibilité Playwright/Ubuntu 26 mentionnée dans la table des fichiers.
  L'image du job navigateur est donc fixée à Ubuntu 24.04.

## Limites opérationnelles

Le délai de publication d'un jour est conservé : Mexico sera attendu à partir
du lundi 02/11. Les quatre créneaux UTC offrent plusieurs possibilités de
rattrapage ; GitHub ne garantit toujours pas l'heure exacte d'un cron.

Le watchdog externe reste non déployé. Un arrêt complet de GitHub Actions ou
une désactivation du workflow ne peuvent donc pas être réparés par ce workflow
lui-même. Les corrections ci-dessus traitent les échecs observés et ajoutent
des preuves de résultat ; elles ne constituent pas une garantie d'absence de
toute panne future.

Les Sprint Qualifying indisponibles dans la source timing conservent les données
antérieures lorsqu'elles existent. Cela ne retire aucun point de sprint ou
de course ; la qualification sprint de Singapour reste absente côté source.
