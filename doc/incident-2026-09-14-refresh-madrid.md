# Incident du 14/09/2026 — classement faux après le GP de Madrid

**Statut :** résolu le 15/09/2026 (commit `fe1fe93`, correctifs complémentaires dans le commit suivant)
**Portée :** classement pilotes, classement constructeurs, duels coéquipiers, couleurs d'écuries
**Non touché :** heatmap des leaders (seule visualisation restée juste)

---

## 1. Ce qui s'est passé, en une phrase

Le refresh automatique post-Madrid n'a pas réussi à charger la session de Spa
depuis FastF1, a conclu que ce Grand Prix n'avait jamais eu lieu, et a republié
un classement complet amputé de ses points — sans qu'aucune alarme ne se
déclenche.

## 2. Symptômes observés

| Élément | Attendu | Publié le 14/09 |
|--|--|--|
| GP comptabilisés | 14 | **13** (Belgique absente) |
| Antonelli | 292 pts | **267 pts** |
| Hamilton | 191 pts (3ᵉ) | **179 pts (4ᵉ)** |
| Écuries dans les duels | 11 | **15**, dont 3 avec trois pilotes |
| Couleurs d'écuries | par `teams.json` | **gris de fallback** pour Red Bull, RB, Alpine, Cadillac |
| Heatmap | 14 GP | 14 GP ✅ |

L'écart entre la heatmap (juste) et le reste du dashboard (faux) est ce qui a
rendu l'incident visible à l'œil nu.

## 3. Cause racine — quel code a cassé

### 3.1 Le déclencheur

`projects/race_chart_builder/race_chart_builder_fastf1.py`, dans
`build_results_table()` :

```python
try:
    race = fastf1.get_session(self.season, round_no, "Race")
    race.load()
    if race.results is None or len(race.results) == 0:
        continue
except Exception:
    continue          # <-- ici
```

Ce `continue` ne distingue pas deux situations radicalement différentes :

- **« ce GP n'a pas encore été couru »** → il faut effectivement l'ignorer ;
- **« ce GP a été couru mais je n'arrive pas à lire ses données »** → il ne faut
  surtout pas l'ignorer.

Le 14/09, le chargement du round 10 (Spa) a échoué côté runner GitHub — cause
externe, vraisemblablement un incident passager de l'API FastF1. Le builder l'a
traité comme le premier cas.

### 3.2 Pourquoi ça a contaminé tout le classement

Le CSV n'est pas incrémental : il est **reconstruit intégralement à chaque
run**, et chaque colonne contient un cumul. Perdre la colonne « Belgium » ne
retire donc pas une colonne d'affichage, cela **retire les points de Spa du
cumul de tous les pilotes pour tous les GP suivants**. Un échec ponctuel sur une
seule session réécrit ainsi toute la saison.

### 3.3 Pourquoi les duels coéquipiers ont sauté aussi

`projects/dashboard/build_qualifying_data.py` détermine les GP à traiter en
lisant les colonnes du CSV race chart :

```python
def load_played_gp_names() -> list[str]:
    df = pd.read_csv(RACE_CHART_CSV, encoding="utf-8-sig")
    return [c for c in df.columns if c not in META]
```

Le round 10 ayant disparu du CSV, il est sorti du périmètre. Or ce builder
possédait déjà un mécanisme de préservation des sessions (ajouté en juillet,
commit `6519b4e`) : **il n'a jamais été sollicité**, puisqu'il ne s'active que
pour un GP dont le chargement échoue — pas pour un GP qu'on ne lui demande même
plus de charger. Une protection correcte, neutralisée par une dépendance en
amont.

### 3.4 Trois défauts préexistants révélés au passage

Ceux-là n'ont pas été causés par le run #35 ; ils étaient là depuis plus
longtemps et l'incident les a mis en lumière.

1. **Noms d'écuries instables.** FastF1 renvoie « Red Bull » en course et
   « Red Bull Racing » en sprint qualif, « RB F1 Team » ou « Racing Bulls »,
   « Alpine F1 Team » ou « Alpine ». Le front résout les couleurs via
   `web/assets/teams.json`, keyé par le nom canonique : toute variante tombait
   sur le gris de fallback, et les duels comptaient l'écurie deux fois.

2. **Noms de pilotes instables.** Les qualifs renvoyaient « Andrea Kimi
   Antonelli », les sprint qualifs « Kimi Antonelli » ; idem
   « Nico Hülkenberg » / « Nico Hulkenberg ». Mercedes affichait **trois
   pilotes**.

3. **Transferts en cours de saison ignorés.** Lawson est passé de Racing Bulls à
   Red Bull à Zandvoort. Le classement constructeurs sommait les totaux par
   écurie *actuelle* du pilote : Red Bull était créditée de 45 points marqués
   chez Racing Bulls. Côté duels, l'écurie listait `[Hadjar, Lawson,
   Verstappen]` et le front affichait les deux premiers par ordre alphabétique —
   soit un duel Hadjar/Lawson qui n'a jamais existé.

## 4. Est-ce un problème de CI/CD ?

**Non, et c'est important de le dire clairement.** Le pipeline a fonctionné
exactement comme programmé :

- `.github/workflows/refresh-after-gp.yml` s'est déclenché au bon moment ;
- les tests unitaires sont passés (ils ne couvraient pas ce cas) ;
- `build_all.py` a retourné 0, puisque aucun builder n'avait signalé d'erreur ;
- le commit et le push ont eu lieu normalement ;
- GitHub Pages a déployé sans faute.

**Le défaut est dans le code des builders, pas dans la CI.** La CI a simplement
publié fidèlement ce qu'on lui a donné. Le vrai manque était l'absence de tout
contrôle entre « les builders ont terminé sans exception » et « les données sont
correctes » — un job vert ne garantissait rien sur le fond.

Un point mérite toutefois d'être noté : le job aurait dû échouer. Il ne l'a pas
fait parce que **rien n'était conçu pour échouer**. C'est précisément ce que les
correctifs ci-dessous changent.

## 5. Délai de détection

L'incident a été publié le 14/09 à 19h05 UTC et repéré le 15/09 au matin, **par
observation visuelle du site**. Sans cette relecture humaine, les données
fausses seraient restées en ligne jusqu'au refresh suivant — qui, lui, aurait pu
réussir et corriger l'erreur silencieusement, ou la reproduire.

## 6. Correctifs appliqués

### Empêcher la disparition d'un GP

`race_chart_builder_fastf1.py` :

- `_load_race_with_retry()` — trois tentatives avec backoff exponentiel, et
  journalisation de chaque échec sur `stderr` (fini le `except` muet).
- `_assert_no_regression()` — avant d'écrire, le builder relit le CSV existant
  et **refuse de publier** si un GP déjà présent a disparu. Il sort en code 1
  avec le détail des GP manquants et des sessions non chargées. Le fichier
  précédent, sain, reste en place.

### Filet de sécurité transversal

`projects/dashboard/validate_outputs.py` (nouveau), appelé par `build_all.py`
en étape 5c, **avant** toute propagation vers `docs/` :

- le CSV race chart et celui de la heatmap doivent couvrir le même nombre de GP ;
- les totaux de points doivent concorder pilote par pilote entre les deux ;
- le `raceCount` du dashboard doit égaler le nombre de GP de la progression ;
- le total pilotes doit égaler le total constructeurs ;
- tout GP dont la date est passée doit être comptabilisé.

Ce contrôle est le plus important des correctifs, car il ne dépend d'aucune
hypothèse sur *quel* builder est fautif. Le builder de la heatmap
(`exporter_lead.py`, ligne 128) contient **exactement le même `except
Exception: continue`** que celui du race chart — il a seulement eu de la chance
le 14/09. Confronter deux sources indépendantes détecte l'anomalie quel que soit
le coupable.

Vérifié en rejouant le CSV cassé du run #35 : la validation le rejette avec le
détail des 10 pilotes dont le total diverge.

### Nommage canonique

- `projects/team_naming.py` (nouveau) — `canonical_team()`, source de vérité
  alignée sur `teams.json`, appliquée dans les trois builders. Une écurie
  inconnue est laissée telle quelle (elle doit apparaître, pas disparaître) ;
  c'est la couleur de fallback qui signalera qu'il faut l'ajouter.
- `build_qualifying_data.py` — noms de pilotes normalisés par **abréviation
  FIA**, seul identifiant stable d'une session à l'autre.

### Transferts en cours de saison

- `build_dashboard_data.py` — constructeurs agrégés **GP par GP** depuis la
  heatmap, qui historise l'écurie de l'époque. Repli sur l'ancienne méthode si
  les deux sources divergent.
- `build_qualifying_data.py` — `current_pair()` retient le duo du dernier GP où
  l'écurie a aligné deux pilotes, au lieu de l'union de tous les pilotes vus.
- `race_chart_builder_fastf1.py` — l'écurie d'un pilote suit désormais ses
  transferts (dernier GP couru faisant foi).

## 7. Tests ajoutés

| Fichier | Couvre |
|--|--|
| `tests/test_race_chart_regression.py` | le garde-fou anti-perte de GP (4 cas) |
| `tests/test_validate_outputs.py` | le contrôle croisé, dont le scénario exact du run #35 (6 cas) |
| `tests/test_team_naming.py` | variantes d'écuries, alignement avec `teams.json` (4 cas) |
| `tests/test_qualifying.py` | transfert en cours de saison, normalisation des noms (3 cas ajoutés) |

Ces tests tournent dans `refresh-after-gp.yml` **avant** le pipeline : une
régression sur ces garde-fous bloque le refresh.

## 8. Ce qui reste ouvert

- **Le `except Exception: continue` de `exporter_lead.py:128` n'a pas été
  corrigé à la source.** Il est désormais couvert par `validate_outputs.py`,
  mais la correction propre (retry + échec explicite, comme pour le race chart)
  reste à faire.
- **Les noms de pilotes du CSV race chart ne sont pas normalisés** — seules les
  qualifs le sont. Si FastF1 bascule un jour sur « Kimi Antonelli » côté CI, le
  libellé changera dans le classement. Sans gravité, mais le jour où ça arrive,
  la piste est ici.
- **Aucune notification active en cas d'échec du refresh.** Le job échouera
  désormais bruyamment, mais il faut ouvrir l'onglet Actions (ou compter sur
  l'e-mail GitHub) pour le voir.

## 9. Leçons

1. **Un `except: continue` dans un builder qui reconstruit tout est une bombe à
   retardement.** Il transforme une panne réseau d'une seconde en réécriture
   silencieuse de l'historique. Un échec doit être bruyant par défaut.
2. **Une protection qui dépend d'une donnée en amont n'en est pas une.** Le
   fallback des qualifs était correct mais inatteignable, parce que son
   périmètre venait du fichier justement corrompu.
3. **Deux sources indépendantes valent mieux qu'une source vérifiée.** La
   heatmap était juste ; personne ne la comparait au reste. Ce croisement est
   maintenant automatique et bloquant.
4. **Un job vert ne dit rien de la justesse des données.** Il dit seulement
   qu'aucune exception n'a été levée.
