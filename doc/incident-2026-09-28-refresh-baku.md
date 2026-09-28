# Incident du 28/09/2026 — le GP de Bakou n'a pas été publié

**Statut :** résolu le 28/09/2026 (rattrapage manuel + correctif de déclenchement)
**Portée :** l'intégralité du dashboard est restée figée au 15/09, classement post-Madrid (14 GP)
**Détecté par :** l'utilisateur, à l'œil, deux jours après la course

---

## 1. Ce qui s'est passé, en une phrase

Le GP d'Azerbaïdjan s'est couru le **samedi** 26/09 ; le cron du lundi qui devait
le publier n'a jamais été déclenché par GitHub, et le filet de sécurité du mardi
ne pouvait de toute façon plus le voir — sa fenêtre de rattrapage de 2 jours
n'atteignait pas le samedi.

## 2. Symptômes observés

| Élément | Attendu le 28/09 | Constaté le 28/09 |
|--|--|--|
| `generatedAt` | 2026-09-28 | **2026-09-15** |
| GP comptabilisés | 15 | **14** |
| `lastGp` | Azerbaijan (26/09) | **Spain - Madrid (13/09)** |
| Leader | Antonelli, 302 pts | **Antonelli, 292 pts** |
| Run CI du 28/09 | 1 run `schedule` | **aucun run** |

Aucune alarme, aucun run en échec, aucune trace : le dashboard affichait
simplement un classement vieux d'une course. C'est une panne **silencieuse**,
pas un plantage.

## 3. Cause racine

Deux défauts indépendants qui, combinés, garantissent la perte de la donnée.

### 3.1 Le cron du lundi n'a pas été déclenché

`.github/workflows/refresh-after-gp.yml` reposait sur deux crons hebdomadaires :

```yaml
schedule:
  - cron: "0 14 * * 1"   # lundi
  - cron: "0 14 * * 2"   # mardi, filet de sécurité
```

Le lundi 28/09, aucun run n'existe — ni réussi, ni échoué, ni annulé. Le dernier
run du workflow date du 22/09. Le workflow est pourtant bien à l'état `active`
côté API.

Un `schedule` GitHub Actions est **best-effort** : la documentation prévient
qu'il peut être retardé ou abandonné en période de forte charge. L'historique du
repo le montrait déjà sans qu'on y prête attention — les runs censés partir à
14:00 UTC démarraient en réalité à 17:36, 17:46, 18:38, 19:05, 19:07. Un retard
de 3 à 5 h était devenu la norme ; l'abandon pur et simple n'en est que le cas
extrême.

**La faute n'est pas dans le code — elle est dans le fait de traiter un
déclencheur non fiable comme s'il était fiable.**

### 3.2 La fenêtre de rattrapage ne couvrait pas un GP du samedi

`projects/dashboard/check_should_refresh.py` décidait ainsi :

```python
LOOKBACK_DAYS = 2  # accepte les GP de J-1 et J-2 (lundi + mardi en filet)
...
window = {today - timedelta(days=d) for d in range(1, LOOKBACK_DAYS + 1)}
...
if gp_date in window:
    return True, ...
```

La logique supposait implicitement « un GP = un dimanche ». Or le calendrier 2026
contient **deux GP le samedi** :

| Round | Date | Jour | GP |
|--|--|--|--|
| 15 | 2026-09-26 | **samedi** | Azerbaijan (Bakou) |
| 21 | 2026-11-21 | **samedi** | United States - Las Vegas |

Pour Bakou :

| Jour du cron | Fenêtre `{J-1, J-2}` | 26/09 dedans ? |
|--|--|--|
| lundi 28/09 | 27, 26 | oui — mais le cron n'a pas tourné |
| mardi 29/09 | 28, 27 | **non** |

Le filet de sécurité du mardi était donc structurellement incapable de rattraper
ce GP. Même si le cron du mardi partait normalement, il aurait répondu
`should-refresh=false — aucun GP dans les 2 derniers jours` et le dashboard
serait resté figé jusqu'au GP suivant.

Autrement dit : **un seul cron sauté = un GP perdu définitivement, en silence.**

## 4. Ce qui a été fait

### 4.1 Rattrapage immédiat

`workflow_dispatch` manuel (run `36467444050`, 3 min 46 s, succès). Le pipeline a
repris Bakou normalement, `validate_outputs.py` (ajouté après l'incident du
14/09) est passé sans rien signaler, et le bot a poussé les données.

Vérifié après coup : `generatedAt` = 2026-09-28, 15 GP, `lastGp` = Azerbaijan,
vainqueur George Russell, Antonelli leader à 302 points.

### 4.2 Correctif de fond — on ne se fie plus au calendrier du cron

`check_should_refresh.py` ne raisonne plus en fenêtre glissante. Il compare
désormais **ce qui a été couru** à **ce qui a été publié** :

- GP disputés = entrées de `calendar_2026.json` dont la date est antérieure
  d'au moins `PUBLISH_DELAY_DAYS = 1` jour (le temps que FastF1 propage) ;
- GP publiés = entrées de `web/data/dashboard_2026.json` avec `status: "played"` ;
- il manque un GP → `should-refresh=true`, avec le nom du GP en clair dans la
  raison affichée dans les logs.

Conséquence : la décision ne dépend plus ni du jour de la semaine, ni de l'heure
du cron, ni du nombre de crons sautés. **N'importe quel run ultérieur rattrape le
retard.** Un GP du samedi, du mercredi ou reporté d'une semaine est traité
identiquement.

Cas dégradés couverts : dashboard absent ou JSON illisible → régénération ;
calendrier absent ou date malformée → pas de faux déclenchement.

### 4.3 Le cron passe au quotidien

```yaml
schedule:
  - cron: "0 14 * * *"
```

Un cron quotidien ne sert plus à *décider* (c'est le rôle du script), seulement à
*donner une occasion*. Un jour sauté par GitHub est rattrapé le lendemain. Le
coût est négligeable : les jours sans retard, le job s'arrête après l'étape de
contrôle, en une quarantaine de secondes.

### 4.4 Tests

`projects/dashboard/tests/test_check_should_refresh.py` (11 tests) verrouille le
scénario exact de l'incident : GP du samedi 26/09 non publié, décision évaluée au
lundi 28, au mardi 29 **et** au mercredi 30 — les trois doivent déclencher. Plus
les bornes : pas de refresh le jour même de la course, refresh dès le lendemain,
pas de refresh quand tout est à jour, et les cas dégradés.

## 5. Ce qui reste ouvert

- **Aucune alerte en cas de retard.** L'incident a été vu par l'utilisateur, pas
  par le système. Le cron quotidien réduit fortement la fenêtre de panne, mais un
  blocage durable (FastF1 en panne, quota Actions épuisé, secret expiré) resterait
  silencieux. Une notification quand un GP est disputé depuis plus de 48 h sans
  être publié serait le vrai filet.
- **Le run `schedule` est le seul chemin automatique.** Si le workflow est
  désactivé par GitHub (ce qui arrive après 60 jours sans activité sur le repo),
  rien ne le signale. Le repo est actif aujourd'hui, mais l'intersaison
  (décembre → mars) dépasse largement ce seuil.
- **Les dates du calendrier ne sont pas contrôlées.** Aucun test ne vérifie que
  `calendar_2026.json` reste cohérent avec le calendrier FIA. Une date fausse ou
  un GP reporté passerait inaperçu — et ferait maintenant déclencher le pipeline
  au mauvais moment.

## 6. Leçons

1. **Un `schedule` GitHub Actions n'est pas une garantie d'exécution.** Il ne
   faut jamais lui confier une décision non rattrapable. Les retards de 3 à 5 h
   visibles dans l'historique étaient le signal annonciateur ; il n'a pas été lu.
2. **Une fenêtre temporelle est une hypothèse déguisée.** `LOOKBACK_DAYS = 2`
   encodait « un GP = un dimanche », une règle vraie 21 fois sur 23 en 2026 —
   donc fausse deux fois, dont une qui a coûté cet incident.
3. **Comparer un état à un autre état bat compter les jours.** « Ce GP est-il
   dans les données ? » est une question qui se répond à tout moment et se
   rattrape toute seule ; « y a-t-il eu un GP avant-hier ? » n'a qu'une seule
   chance d'être posée.
4. **Deuxième panne silencieuse en deux semaines** (cf.
   `incident-2026-09-14-refresh-madrid.md`). Les deux se sont manifestées par des
   données fausses ou figées sans aucun run en échec. Le contrôle ajouté le 15/09
   protège la *justesse* des données produites ; il ne dit rien sur le fait que la
   production ait eu lieu. C'est ce deuxième angle — la **fraîcheur** — qui reste
   à couvrir par une alerte.
