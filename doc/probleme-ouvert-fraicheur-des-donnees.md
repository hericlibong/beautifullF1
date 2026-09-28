# Problème ouvert — rien ne garantit ni ne surveille la publication des données

**Ouvert le :** 28/09/2026
**Statut :** partiellement résolu dans le dépôt le 29/09/2026 ; garantie externe encore à déployer
**Lié à :** `incident-2026-09-14-refresh-madrid.md`, `incident-2026-09-28-refresh-baku.md`
**À qui ça appartient :** décision d'infrastructure (choix d'un déclencheur et d'un canal d'alerte)

> Mise en œuvre et preuves : voir `resolution-fraicheur-des-donnees.md`.

Ce document décrit ce qui reste cassé *après* le correctif du 28/09, pourquoi ce
reste ne peut pas être réglé par du code dans ce dépôt, et quelles options
existent avec leurs compromis. Il ne décrit pas l'incident de Bakou lui-même —
c'est l'objet de `incident-2026-09-28-refresh-baku.md`.

---

## 1. Le problème en une phrase

La publication des données repose entièrement sur un déclencheur que GitHub ne
garantit pas d'exécuter, et **aucun mécanisme ne signale qu'il n'a pas été
exécuté** — donc une panne de publication est indétectable autrement qu'en
regardant le dashboard à l'œil.

## 2. Contexte — comment la publication est censée se produire

La chaîne complète, du GP au site publié :

```
GP couru (dimanche, parfois samedi)
   │
   │  ⟵ SEUL déclencheur automatique : cron GitHub Actions
   ▼
.github/workflows/refresh-after-gp.yml
   ├─ check_should_refresh.py   → doit-on rafraîchir ?
   ├─ pytest (unit)
   ├─ build_all.py              → FastF1 → CSV → JSON → sync docs/
   ├─ validate_outputs.py       → les données produites sont-elles cohérentes ?
   └─ git commit + push         (bot github-actions)
   │
   ▼
pages-build-deployment → GitHub Pages
```

Point structurant : **il n'y a pas de serveur.** Aucun processus ne tourne en
permanence, rien ne « surveille » quoi que ce soit. Si le cron ne part pas, il
ne se passe strictement rien — pas d'erreur, pas de run, pas de trace. Le site
continue de servir les dernières données publiées, sans indiquer leur âge.

C'est le choix d'architecture du projet (site statique, zéro backend) et il est
bon. Mais il a pour corollaire que **le déclencheur est le maillon critique
unique**, et qu'il faut le traiter comme tel.

## 3. Les faits mesurés

Historique complet des 36 runs `schedule` du workflow, depuis sa création
(25/05/2026) jusqu'au 28/09/2026. Heure planifiée : **14:00 UTC**.

| Fait | Valeur |
|--|--|
| Runs planifiés partis à l'heure | **0 sur 36** |
| Retard minimum observé | 19 min (18/08) |
| Retard médian | **2 h 36** |
| Retard maximum | **5 h 52** (31/08) |
| Crons purement non exécutés | **1** — lundi 28/09 |

Évolution du retard, par période :

| Période | Retard typique |
|--|--|
| fin mai → fin juin | 2 h 12 → 5 h 21 |
| juillet | 1 h 00 → 2 h 52 |
| mi-août | **19 à 47 min** (meilleure période) |
| fin août → fin septembre | **3 h 28 → 5 h 52** |

Deux lectures importantes :

1. **Aucun run n'est jamais parti à l'heure demandée.** Le cron n'a jamais été
   ponctuel, pas une seule fois en quatre mois.
2. **La dégradation est récente et nette.** Après une accalmie en août
   (retards sous l'heure), les six derniers runs affichent 3 h 28 à 5 h 52. Le
   cron sauté du 28/09 n'est pas une anomalie isolée : c'est le point d'arrivée
   d'une tendance visible depuis un mois.

Le 28/09 est le **premier** cron non exécuté — les 18 paires lundi/mardi
précédentes sont toutes complètes. Le taux d'échec observé est donc de 1 sur 37,
mais sur un historique court et avec une tendance qui se dégrade : il serait
imprudent d'en tirer une probabilité rassurante.

## 4. Pourquoi ce n'est pas réparable ici

La documentation GitHub Actions est explicite sur deux points :

- **Les workflows planifiés sont « best-effort ».** Ils « peuvent être retardés
  pendant les périodes de forte charge » et il n'existe **aucune garantie
  d'exécution**. Un cron sauté n'est pas un bug à corriger, c'est le
  fonctionnement documenté du service.
- **Les créneaux en début d'heure sont explicitement cités comme les plus
  chargés**, avec la recommandation de planifier à une minute décalée. Notre
  cron est à `0 14 * * *` — pile au pire moment possible.

Aucune ligne de Python ni de YAML dans ce dépôt ne peut forcer GitHub à exécuter
un run. Le correctif du 28/09 rend le système *tolérant* aux crons sautés ; il
ne les empêche pas et ne les détecte pas.

## 5. Décomposition — trois problèmes distincts

Il est important de ne pas les confondre : ils ont des causes et des remèdes
différents.

### P1 — Le cron peut ne pas partir

**Ce que c'est :** best-effort documenté, voir §4.
**Sous notre contrôle :** partiellement — on peut réduire la probabilité
(décaler l'heure, augmenter la fréquence) mais pas l'éliminer.
**Couverture actuelle :** cron passé au quotidien le 28/09 puis décalé à
14:23 UTC le 29/09. Il faut désormais plusieurs jours consécutifs sautés pour
perdre un GP, au lieu d'un seul. Gain réel mais probabiliste.

### P2 — Le workflow peut être désactivé pour inactivité

**Ce que c'est :** GitHub désactive automatiquement les workflows planifiés après
**60 jours sans activité sur le dépôt**.
**Pourquoi ça mord ici :** l'intersaison F1 va de début décembre à début mars,
soit environ **90 jours**. Si aucun commit n'est poussé pendant cette période, le
workflow sera désactivé avant le premier GP de 2027, et la saison démarrera sans
aucune publication automatique.
**Sous notre contrôle :** oui, entièrement — mais pas par le correctif actuel,
qui n'y change rien.
**À vérifier :** GitHub notifie en principe le propriétaire du dépôt avant
désactivation. À confirmer, et à ne pas considérer comme un filet fiable (un mail
dans la boîte de réception n'est pas un mécanisme).

### P3 — Rien ne signale l'absence de publication

**Ce que c'est :** le vrai problème de fond. Les trois incidents connus se sont
tous manifestés de la même façon : **des données fausses ou figées, aucun run en
échec, découverte à l'œil par l'utilisateur.**
**Sous notre contrôle :** oui, entièrement.
**Couverture actuelle :** depuis le 29/09, le site affiche toujours la date de
génération et calcule dans le navigateur un bandeau si un GP manque depuis plus
de 48 h. Cette détection ne dépend pas d'un run GitHub. Il n'existe toutefois
pas encore de notification proactive hors du site.

**L'angle mort décisif, à bien comprendre avant de choisir une solution :** une
alerte hébergée dans un workflow GitHub planifié hérite exactement de la
défaillance qu'elle est censée détecter. Si le cron ne part pas, l'alerte ne part
pas non plus. Le 28/09, une telle alerte serait restée muette. **Un surveillant
qui dépend du mécanisme surveillé ne surveille rien.**

## 6. Ce que le correctif du 28/09 couvre exactement

Commit `7e24957`, poussé sur `origin/main` le 28/09. Au moment de l'ouverture de
ce document il n'avait pas encore subi son premier cycle planifié quotidien.

| Problème | Couvert ? |
|--|--|
| Fenêtre de 2 jours ratant un GP du samedi | **oui, éliminé par construction** + 11 tests |
| Perte définitive après un seul cron sauté | **oui** — tout run ultérieur rattrape |
| P1 — cron qui ne part pas | partiellement (probabilité réduite) |
| P2 — désactivation à 60 jours | **non** |
| P3 — absence de détection | **oui sur le site** ; notification proactive non couverte |

Effet secondaire introduit, à connaître : si un GP passé ne peut jamais être
intégré (course annulée mais laissée au calendrier, panne durable de FastF1),
`check_should_refresh.py` répondra `true` indéfiniment et le pipeline tournera
chaque jour sans converger. Si le pipeline échoue, cela produit un run rouge
quotidien — visible, donc plutôt utile. S'il réussit sans rien changer, la boucle
est silencieuse et sans coût notable.

## 7. Options de résolution

### Option A — Décaler l'heure du cron

```yaml
schedule:
  - cron: "23 14 * * *"   # au lieu de "0 14 * * *"
```

**Coût :** une ligne.
**Couvre :** réduit le retard et le risque d'abandon (recommandation officielle
GitHub, cf. §4). **Ne règle rien structurellement** — c'est une optimisation.
**Verdict :** mis en œuvre le 29/09, ne dispense d'aucune autre option.

### Option B — Alerte de fraîcheur dans un workflow GitHub

Un job qui échoue bruyamment si un GP est couru depuis plus de 48 h sans être
publié. La logique de détection existe déjà : `check_should_refresh.py` répond
exactement à cette question, il suffit d'en faire un code de sortie non nul
au-delà d'un seuil.

**Coût :** faible, ~20 lignes, entièrement dans ce dépôt. Je peux l'écrire.
**Couvre :** le cas « le pipeline tourne mais échoue ou n'intègre pas le GP ».
**Ne couvre pas :** le cas du 28/09 — cf. l'angle mort du §P3. Le workflow
d'alerte dépend du même cron défaillant.
**Verdict :** utile en complément, **insuffisant seul**. Ne pas s'en contenter en
croyant le problème réglé : ce serait le piège principal de ce dossier.

### Option C — Déclencheur externe, indépendant du cron GitHub

Un service tiers appelle l'API GitHub pour lancer le workflow
(`workflow_dispatch` ou `repository_dispatch`) : cron-job.org, un cron sur une
machine personnelle, un Cloudflare Worker, une GitHub App, un runner planifié
ailleurs.

**Coût :** un token (PAT à portée restreinte, stocké en secret) + un service
externe à maintenir. C'est la seule option qui sort du repo.
**Couvre :** **P1**. Pour couvrir aussi P2, le service doit appeler l'API
d'activation du workflow avant le dispatch lorsqu'il est en état
`disabled_inactivity` ; un simple dispatch n'est pas considéré ici comme une
garantie suffisante contre la désactivation.
**Compromis :** introduit une dépendance externe et un secret à faire tourner ;
le service externe devient à son tour un maillon à surveiller.
**Verdict :** la seule option qui apporte une garantie d'exécution.

### Option D — Rendre la panne visible côté site

Le front-end connaît déjà `generatedAt` et le calendrier complet. Il peut donc
calculer lui-même qu'un GP est couru depuis plus de 48 h sans figurer dans les
données, et l'afficher — bandeau, date de dernière mise à jour, indicateur de
retard.

**Coût :** faible, front-end pur, aucune infrastructure.
**Couvre :** **P3, et sans dépendre d'aucun cron** — c'est sa propriété
décisive. Le signal est calculé chez le visiteur, à chaque chargement de page.
Aurait fonctionné le 28/09, et fonctionnerait même workflow désactivé.
**Ne couvre pas :** ne répare rien, ne prévient personne activement — il faut
ouvrir le site. Mais il rend la panne impossible à manquer au lieu d'exiger de
comparer mentalement le classement à la réalité.
**Verdict :** mis en œuvre le 29/09. C'est le meilleur rapport couverture/coût
du lot. Bénéfice éditorial en prime : afficher la fraîcheur d'une donnée publiée
est de toute façon une bonne pratique.

### Option E — Traiter la désactivation à 60 jours (P2)

Trois approches : un commit automatique périodique pendant l'intersaison ; un
watchdog externe qui vérifie l'état, réactive puis déclenche le workflow ; ou
assumer le risque et le réactiver à la main en février, avec un rappel calendaire.

**Verdict :** à décider avant décembre 2026. C'est une échéance datée, pas une
question ouverte.

## 8. Recommandation

**A + D en priorité**, parce qu'ils sont intégralement dans ce dépôt, sans
dépendance externe, et que D est le seul mécanisme de détection qui ne partage
pas la défaillance qu'il surveille.

**C si l'on veut une vraie garantie d'exécution**, et parce qu'il règle P2 au
passage.

**B en complément**, jamais en remplacement de D.

À dire clairement : **aucune combinaison ne donne une garantie à 100 %.** C + D
est ce qui s'en approche le plus — une exécution qui ne dépend plus de GitHub, et
une détection qui ne dépend de rien.

## 9. Ce qu'il reste à décider

1. Accepte-t-on une dépendance externe (option C) ou reste-t-on strictement dans
   GitHub, en assumant qu'aucune exécution n'est garantie ?
2. Le bandeau sur le site est retenu et mis en œuvre. Reste à choisir, si
   souhaité, un canal de notification proactive (e-mail ou autre) porté par le
   watchdog externe.
3. Que fait-on pour l'intersaison (P2) ? Échéance : avant décembre 2026.
4. Quel seuil de retard déclenche une alerte ? 48 h est un point de départ
   raisonnable (FastF1 publie sous 24 h en pratique), pas une valeur étudiée.

## 10. Comment vérifier / reproduire

Rejouer les mesures du §3 :

```bash
# historique des runs planifiés et de leurs retards
gh api --paginate "repos/:owner/:repo/actions/workflows/refresh-after-gp.yml/runs?per_page=100"

# état du workflow (active / disabled_inactivity)
gh api repos/:owner/:repo/actions/workflows

# décision de refresh, en local
python projects/dashboard/check_should_refresh.py
```

Constater l'absence d'un run est le point délicat : il n'y a rien à trouver dans
les logs, seulement un trou dans la liste des dates. C'est précisément ce qui
rend ce problème invisible sans un mécanisme dédié.

## 11. Références

- GitHub Actions — `schedule` : exécution best-effort, retards en période de
  forte charge, recommandation de ne pas planifier en début d'heure.
- GitHub Actions — désactivation automatique des workflows planifiés après
  60 jours d'inactivité du dépôt.
- `doc/incident-2026-09-14-refresh-madrid.md` — panne silencieuse n° 1 (données
  fausses).
- `doc/incident-2026-09-28-refresh-baku.md` — panne silencieuse n° 2 (données
  figées).
