# Résolution — fraîcheur et publication automatique des données

**Ouvert le :** 29/09/2026

**Document source :** `probleme-ouvert-fraicheur-des-donnees.md`

**Incidents liés :** `incident-2026-09-14-refresh-madrid.md`,
`incident-2026-09-28-refresh-baku.md`

**Statut :** mise en œuvre, publication et validations locale/distante
terminées ; premier cron automatique à 14:23 UTC encore à observer ; watchdog
externe non déployé

---

## 1. Objet et principe de traçabilité

Ce document est le journal de mise en œuvre de la résolution du problème de
fraîcheur. Il indique :

- les changements effectués et leur raison ;
- les fichiers sources et les copies publiées concernés ;
- les risques couverts et ceux qui restent ouverts ;
- les commandes de validation et leurs résultats ;
- les contrôles à réaliser après publication.

Les changements locaux préexistants dans le workflow, `web/index.html` et
`web/assets/modules/freshness.js` ont été conservés puis complétés. Le dossier
non suivi `.claude/` n'a pas été modifié.

## 2. État de départ constaté

Au début de l'intervention :

1. le correctif `7e24957` comparant les GP courus aux GP publiés était bien
   présent dans `origin/main` ;
2. le cron quotidien de production restait fixé à `14:00 UTC` ; son passage à
   `14:23 UTC` existait seulement dans la copie de travail ;
3. `freshness.js` existait localement mais n'était pas suivi par Git ;
4. l'orchestrateur `dashboard.js` n'appelait pas ce module ;
5. les traductions, styles, tests et copies publiques `docs/` manquaient ;
6. un calendrier absent produisait `should-refresh=false`, ce qui transformait
   une erreur de configuration en absence silencieuse de travail ;
7. aucun déclencheur indépendant de GitHub Actions n'était configuré.

## 3. Architecture retenue

```text
cron GitHub quotidien 14:23 UTC
ou workflow_dispatch manuel
ou repository_dispatch "scheduled-refresh"
                 │
                 ▼
       check_should_refresh.py
          │             │
   données à jour   GP manquant
       arrêt          tests + build
                           │
                           ▼
                   validation + sync docs/
                           │
                           ▼
                    commit/push du bot

En parallèle, à chaque ouverture du site :
dashboard_2026.json → freshness.js → date de mise à jour
                                  └→ bandeau si retard > 48 h
```

Le bandeau côté navigateur ne répare pas la publication, mais il ne dépend
pas du cron. Il rend donc visible une absence totale de run.

## 4. Changements effectués, fichier par fichier

### 4.1 Déclenchement et orchestration

#### `.github/workflows/refresh-after-gp.yml`

Modifications :

- cron quotidien décalé de `0 14 * * *` vers `23 14 * * *` ;
- ajout du point d'entrée `repository_dispatch`, type `scheduled-refresh`, pour
  un futur watchdog externe ;
- ajout d'un groupe `concurrency` sans annulation du run en cours, afin
  d'empêcher deux builds et deux `git push` concurrents ;
- exécution du contrôle de fraîcheur avant l'installation des dépendances ;
- installation de FastF1 et des autres dépendances uniquement lorsqu'un build
  est requis ou lorsqu'un lancement manuel force le pipeline ;
- libellés et commentaires corrigés pour décrire la comparaison
  couru/publié plutôt qu'une fenêtre de deux jours.

Pourquoi : diminuer la probabilité d'un cron abandonné en évitant le début
d'heure, conserver plusieurs chemins d'entrée, éviter les conflits de push et
rendre les contrôles quotidiens sans GP moins coûteux.

### 4.2 Décision de refresh

#### `projects/dashboard/check_should_refresh.py`

Modifications :

- ajout de `RefreshCheckError` ;
- validation explicite de l'existence et de la lisibilité du calendrier ;
- validation de la structure `rounds`, du nom et de la date ISO de chaque GP ;
- code de sortie `1` si aucune décision fiable ne peut être rendue ;
- maintien de la comparaison entre GP courus et GP publiés pour la décision
  normale.

Pourquoi : une configuration cassée ne doit jamais produire silencieusement
`should-refresh=false`. Un run rouge est observable ; une fausse absence de
travail ne l'est pas.

#### `projects/dashboard/tests/test_check_should_refresh.py`

Modifications :

- adaptation du test de calendrier absent ;
- transformation d'une date invalide en erreur attendue ;
- ajout des cas JSON illisible, liste `rounds` vide et code de sortie de `main`.

Pourquoi : verrouiller le comportement fail-loud et empêcher sa régression.

### 4.3 Visibilité de la fraîcheur sur le site

#### `projects/dashboard/web/assets/modules/freshness.js`

Fichier local préexistant ajouté au périmètre publié. Il :

- compare la date des GP au statut `played` du JSON publié ;
- utilise un seuil de 48 heures ;
- retourne la liste des GP manquants ;
- affiche la date `generatedAt` dans le pied de page ;
- affiche un bandeau persistant en cas de retard ;
- journalise aussi le retard dans la console.

Pourquoi : ce contrôle s'exécute chez le visiteur et reste donc fonctionnel
même si le workflow GitHub n'a créé aucun run.

#### `projects/dashboard/web/assets/dashboard.js`

Modifications : import de `initFreshness` et appel après le chargement des
données et l'initialisation des traductions.

Pourquoi : le module existait mais n'était jamais exécuté.

#### `projects/dashboard/web/index.html`

Modifications : ajout du conteneur d'alerte avec `role="alert"` et
`aria-live="polite"`, plus un emplacement pour la date de mise à jour.

Pourquoi : fournir des cibles accessibles au module sans générer la structure
de page dynamiquement.

#### `projects/dashboard/web/assets/i18n.json`

Modifications : messages français et anglais pour la date de mise à jour,
l'alerte d'un GP manquant et l'alerte de plusieurs GP manquants.

Pourquoi : conserver le fonctionnement bilingue du dashboard.

#### `projects/dashboard/web/assets/dashboard.css`

Modifications : styles du bandeau de fraîcheur et de la date de mise à jour.

Pourquoi : rendre l'alerte visible sans rompre le design existant, y compris
sur mobile.

### 4.4 Tests de publication et du navigateur

#### `projects/dashboard/tests/test_sync.py`

Modification : `freshness.js` fait partie des modules imbriqués dont la copie
vers `docs/` est vérifiée.

#### `projects/dashboard/tests/e2e/test_dashboard.py`

Modifications :

- test de la date de mise à jour lorsque les données sont courantes ;
- test d'un JSON simulant un GP vieux de trois jours encore absent ;
- vérification que le bandeau contient le nom du GP manquant.

Pourquoi : tester le comportement dans un vrai navigateur, sans ajouter Node,
bundler ou infrastructure JavaScript au chemin de publication.

### 4.5 Documentation

#### `doc/probleme-ouvert-fraicheur-des-donnees.md`

Modifications : statut actualisé, lien vers le présent rapport, correction de
l'état du commit `7e24957` et précision sur la réactivation nécessaire après
une désactivation pour inactivité.

#### `projects/dashboard/README.md`

Modifications : fréquence quotidienne, heure 14h23 UTC, logique de rattrapage,
alerte de 48 heures et module `freshness.js`.

#### `projects/dashboard/PLAN.md`

Modifications : suppression des anciennes mentions lundi/mardi, consignation
du rattrapage quotidien et du bandeau, watchdog externe laissé comme décision
d'infrastructure.

#### `projects/dashboard/REFACTOR_PLAN.md`

Modification : contrainte opérationnelle mise en cohérence avec le contrôle
quotidien.

#### `CLAUDE.md`

Modification : description de la chaîne de refresh alignée sur le workflow
actuel, afin que les interventions futures ne réintroduisent pas l'ancien
modèle lundi/mardi.

### 4.6 Copies GitHub Pages

Les fichiers suivants sont produits par
`python projects/dashboard/sync_to_docs.py`, jamais modifiés à la main :

- `docs/index.html` ;
- `docs/assets/dashboard.js` ;
- `docs/assets/dashboard.css` ;
- `docs/assets/i18n.json` ;
- `docs/assets/modules/freshness.js`.

## 5. Validation locale

| Contrôle | Commande | Résultat |
|---|---|---|
| Tests ciblés refresh et sync | `pytest projects/dashboard/tests/test_check_should_refresh.py projects/dashboard/tests/test_sync.py -q --no-cov` | **17 réussis** |
| Tests unitaires dashboard | `pytest projects/dashboard/tests -q -m "not e2e" --no-cov` | **83 réussis** |
| Lint Python | `ruff check` sur les quatre fichiers Python modifiés | **réussi** |
| Format Python | `black --check` sur les quatre fichiers Python modifiés | **réussi**, aucun changement requis |
| Validation i18n | `python -m json.tool projects/dashboard/web/assets/i18n.json` | **réussie** |
| Décision sur les données réelles | `python projects/dashboard/check_should_refresh.py` | **false**, 15 GP publiés, dernier : Azerbaijan 26/09 |
| Synchronisation GitHub Pages | `python projects/dashboard/sync_to_docs.py` | **réussie**, 23 fichiers copiés |
| Tests E2E dashboard et fraîcheur | `pytest projects/dashboard/tests/e2e/test_dashboard.py -m e2e --no-cov -q` | **10 réussis** |
| Cohérence des copies | empreintes SHA-256 `web/` / `docs/` sur les cinq fichiers concernés | **5 paires identiques** |
| Diff Git | `git diff --check` | **réussi** |

Le premier lancement E2E s'est arrêté avant les tests, car Chromium n'était
pas installé dans l'environnement. Chromium a été téléchargé dans
`.tmp-playwright-browsers`, les 10 tests ont ensuite réussi, puis ce répertoire
temporaire et le cache `.uv-cache` ont été supprimés. Cet incident
d'environnement n'était pas une erreur du dashboard.

## 6. Validation après publication

### 6.1 Publication du correctif

- commit publié sur `main` : `7f6da74` —
  `fix(ci): fiabilise et rend visible la fraîcheur des données` ;
- workflow `Refresh data after GP` toujours actif, identifiant `282902040` ;
- contrôle qualité `Python scripts quality check` : **succès** sur `7f6da74` ;
- déploiement `pages-build-deployment` : **succès** sur `7f6da74`.

### 6.2 Run de validation forcé

Run GitHub Actions :
`https://github.com/hericlibong/beautifullF1/actions/runs/36492539108`

Résultat : **succès**, 3 min 44 s, sur le commit `7f6da74`.

Preuves relevées dans les logs :

- `check_should_refresh.py` : `should-refresh=false`, 15 GP publiés, dernier
  Azerbaijan le 26/09 ;
- `workflow_dispatch` a correctement forcé la suite du pipeline ;
- installation des dépendances : succès ;
- tests unitaires du workflow : succès ;
- `validate_outputs.py` : succès ;
- synchronisation dashboard : 23 fichiers ;
- pipeline complet : succès ;
- étape de commit : `Aucun changement à pousser.`

Ce dernier point confirme qu'un lancement manuel sur des données déjà à jour
reste idempotent et ne crée pas un commit artificiel.

### 6.3 GitHub Pages

Vérification directe de `https://hericlibong.github.io/beautifullF1/` :

- le HTML public contient `#dash-freshness` et `#dash-updated` ;
- `assets/modules/freshness.js` répond en HTTP **200** ;
- le module public expose `STALE_AFTER_DAYS = 2`, `checkFreshness` et
  `initFreshness`.

### 6.4 Preuves qui demandent encore du temps réel

Les points suivants ne peuvent pas être simulés par un run manuel :

1. observer le premier événement `schedule` créé à partir de 14:23 UTC ;
2. confirmer qu'un jour sans GP ce run s'arrête avant l'installation des
   dépendances ;
3. lors du prochain GP, confirmer le comportement automatique complet sans
   intervention manuelle.

### 6.5 Avertissements GitHub non bloquants

Le run a remonté deux avis de maintenance sans impact sur son résultat :

- GitHub force actuellement les actions `checkout@v4`, `setup-python@v5` et
  `cache@v4` de Node.js 20 vers Node.js 24 ; il faudra suivre les futures
  versions majeures de ces actions ;
- l'image `ubuntu-latest` doit migrer vers Ubuntu 26 à partir du 19/10/2026 ;
  la prochaine exécution après migration devra être surveillée.

## 7. Watchdog externe : préparé mais non déployé

Le workflow accepte maintenant l'événement `repository_dispatch` de type
`scheduled-refresh`. Cela prépare l'intégration sans imposer une plateforme.

Le déploiement externe reste volontairement séparé, car il exige :

- le choix d'un hébergeur ou ordonnanceur ;
- la création et le stockage d'un secret GitHub ;
- le choix du canal d'alerte ;
- une autorisation pour agir sur le workflow distant.

Le watchdog devra suivre cet ordre :

1. lire l'état du workflow ;
2. s'il est `disabled_inactivity`, appeler l'API d'activation ;
3. envoyer `repository_dispatch` avec le type `scheduled-refresh` ;
4. vérifier qu'un run a été créé ;
5. après le délai admis, comparer le dernier GP attendu à la donnée
   publique et alerter si le retard persiste.

## 8. Couverture finale attendue

| Risque | Couverture après publication |
|---|---|
| GP du samedi hors d'une fenêtre glissante | Éliminé par comparaison couru/publié |
| Un cron GitHub isolé est sauté | Rattrapage au run quotidien suivant |
| Charge GitHub au début de l'heure | Probabilité réduite par `14:23` |
| Deux déclenchements simultanés | Sérialisés par `concurrency` |
| Calendrier absent ou invalide | Run rouge explicite |
| Données anciennes sans aucun run | Bandeau calculé côté navigateur |
| Désactivation après 60 jours | Non couvert avant déploiement du watchdog |
| Notification proactive hors du site | Non couverte avant choix du canal d'alerte |

## 9. Retour arrière

En cas de régression front-end, le module peut être débranché en retirant
son import et son appel dans `dashboard.js`, puis en resynchronisant `docs/`.
Cela ne touche pas au pipeline de données.

En cas de problème avec le nouveau cron, `workflow_dispatch` reste disponible.
Le retour temporaire à une autre minute ne doit pas réintroduire une exécution
uniquement hebdomadaire ni la logique de fenêtre glissante supprimée par
`7e24957`.

## 10. Revue complémentaire du 29/09/2026

Une revue externe de l'implémentation a confirmé le diagnostic et relevé quatre
points non bloquants. Aucun changement de code n'est engagé à ce stade.

### 10.1 Premier run réellement planifié

Au 29/09 à 00:49 heure de Paris, aucun run `schedule` utilisant le nouveau cron
n'avait encore pu avoir lieu. Le premier créneau attendu est le 29/09 après
14:23 UTC, soit 16:23 heure de Paris. Il faut observer plusieurs runs avant de
comparer utilement leur retard aux anciennes mesures.

**Classement :** preuve opérationnelle encore attendue, mais pas un défaut de
code ni un blocage avant l'heure planifiée.

### 10.2 Seuil du bandeau à 48 heures

Avec le rattrapage quotidien, un cron du lundi sauté peut faire apparaître le
bandeau le mardi avant que le run de 14:23 UTC ne corrige automatiquement les
données. Le signal reste factuellement exact, mais peut sembler plus alarmant
que nécessaire pendant cette fenêtre.

**Décision :** conserver 48 heures pour le moment. Réévaluer après quelques
runs réels ; options futures : seuil de trois jours ou deux niveaux de message
(`rattrapage attendu` puis `retard anormal`).

### 10.3 Sémantique ARIA du bandeau

Le conteneur combine actuellement `role="alert"` et `aria-live="polite"`.
`role="alert"` implique normalement une annonce assertive ; la combinaison est
donc ambiguë selon les lecteurs d'écran.

**Décision :** correction différée car elle ne bloque ni l'affichage ni la
publication. Au prochain passage front-end/accessibilité, retenir une seule
sémantique : probablement `role="status"` avec `aria-live="polite"` pour cette
alerte non urgente.

### 10.4 Couverture unitaire de `checkFreshness`

Les tests E2E couvrent les données courantes et un GP manquant, mais pas encore
la branche plusieurs GP, la valeur exacte de `daysLate` ni la borne du seuil.

**Décision :** dette de test acceptée. La couverture navigateur actuelle est
suffisante pour la mise en production ; compléter ces cas lors d'un futur
chantier de tests JavaScript, sans introduire maintenant une infrastructure
Node dans le pipeline.

### 10.5 Priorité restante

Le risque le plus important reste la désactivation après 60 jours d'inactivité.
Le watchdog externe doit être choisi et déployé avant l'intersaison de décembre
2026. Le bandeau actuel ne remplace pas une notification proactive.
