# Data Trust Confidence (DTC) — Formalisation

**Version :** v1.0 — base pour rédaction d'un article scientifique
**Objet :** modèle formel d'évaluation dynamique de la confiance d'une donnée
dans une architecture de gouvernance centrée sur la donnée

Documents associés :
- `dtc-reference/PROPRIETES.md` — démonstrations formelles
- `dtc-reference/README.md` — résultats expérimentaux et limites
- `dtc-reference/` — implémentation exécutable

---

## 0. Avertissement méthodologique

Ce document distingue explicitement :

| Marqueur | Signification |
|---|---|
| **[EXISTANT]** | Repris de la littérature — doit être cité, ne constitue pas une contribution |
| **[ADAPTÉ]** | Formalisme existant appliqué à un contexte nouveau — contribution faible mais légitime |
| **[CONTRIBUTION]** | Mécanisme original — c'est ce qui doit porter le papier |

La crédibilité d'un article tient autant à ce qu'il revendique qu'à ce qu'il
reconnaît devoir aux autres.

---

## 1. Notations et objets de base

Soit `D` l'ensemble des données gouvernées, chacune identifiée par un
identifiant persistant, et `G = (D, R)` le graphe de lignage, orienté et
possiblement cyclique, dont les arêtes portent un type de relation
`ρ ∈ {copie, dérivation, transformation, agrégation, référence}`.

### 1.1 État de confiance — l'opinion **[EXISTANT — Jøsang, Subjective Logic]**

```
ω_x(t) = ( b_x(t), d_x(t), u_x(t), a_x )        avec  b + d + u = 1
```

- `b` — croyance : masse de preuve soutenant la fiabilité
- `d` — méfiance : masse de preuve soutenant la non-fiabilité
- `u` — incertitude : masse de preuve manquante
- `a` — taux de base, fixé par politique de gouvernance

**Justification.** Un score scalaire confond deux situations opérationnellement
opposées : une donnée jamais observée (incertitude maximale) et une donnée
abondamment observée au bilan mitigé. Toutes deux produiraient ≈ 0.5. La
séparation `u` vs `(b,d)` permet de distinguer *« refuser car douteux »* de
*« refuser car inconnu »* — deux décisions appelant des remédiations
différentes.

---

## 2. Modèle de preuve

### 2.1 Élément de preuve **[ADAPTÉ]**

```
e = ( τ , σ , w , t_e , κ )
```

| Champ | Description |
|---|---|
| `τ` | type d'événement |
| `σ ∈ {+1,−1}` | polarité |
| `w` | poids brut |
| `t_e` | horodatage |
| `κ ∈ [0,1]` | crédibilité de la **source de la preuve** |

Le facteur `κ` applique le principe *Zero Trust* au flux de preuves lui-même :
une preuve issue d'un système faiblement attesté ne pèse pas autant qu'une
preuve issue d'une autorité co-attestée.

### 2.2 Décroissance temporelle typée **[ADAPTÉ]**

```
r_x(t) = Σ_{σ=+1}  w·κ·exp( −λ_τ · (t − t_e) )
s_x(t) = Σ_{σ=−1}  w·κ·exp( −λ_τ · (t − t_e) )
```

`λ` est **typé par preuve**, pas global :

- `λ` faible pour l'attestation d'origine — elle ne se périme pas vite
- `λ` élevé pour un contrôle d'intégrité — celui d'il y a deux ans ne dit rien
  de l'état actuel
- **`λ = 0` pour une compromission avérée** — décision de sécurité forte : elle
  ferme l'attaque consistant à attendre l'expiration de la mauvaise
  réputation. Seule une remédiation attestée peut la contrebalancer.

*Validation :* scénario de révélation tardive, la défiance ne s'érode pas
jusqu'à t = 50 000.

### 2.3 Passage aux opinions **[EXISTANT — Beta reputation]**

```
b = r/(r+s+W)      d = s/(r+s+W)      u = W/(r+s+W)        (W = 2)
```

### 2.4 Taux de base gouverné **[ADAPTÉ]**

`a_x = a_base( classification, niveau d'attestation, juridiction )`. Ce
paramètre porte toute la sémantique du *« que croire en l'absence de preuve »*.
Le rendre explicite, versionné et gouverné — plutôt que caché dans une
heuristique — est une exigence d'auditabilité.

---

## 3. Projection décisionnelle

```
P_x(t) = b_x(t) + a_x · u_x(t)                              [EXISTANT]
```

**Règle architecturale.** `P_x` est toujours fournie *accompagnée* de l'opinion
complète et des preuves déterminantes, ce qui autorise des politiques
inexprimables avec un scalaire seul :

```
SI  P ≥ 0.7  ET  u ≤ 0.3   → autoriser
SI  P ≥ 0.7  ET  u >  0.3   → autoriser avec validation supplémentaire
SI  d ≥ 0.4                 → refuser et déclencher investigation
```

---

## 4. Fusion et dépendance des sources **[EXISTANT]**

L'accumulation au niveau de `r` et `s` équivaut à la fusion cumulative de la
logique subjective. Elle suppose l'indépendance des observations.

*Traitement retenu :* déduplication par identifiant d'observation primaire,
les preuves partageant la même référence étant fusionnées par `max` plutôt que
`somme`.

> **Limite assumée.** Correct pour la duplication exacte, insuffisant pour la
> corrélation partielle entre sources partageant une infrastructure commune.

---

## 5. Propagation non transitive **[CONTRIBUTION — cœur du papier]**

### 5.1 Le problème

L'architecture exige que la confiance ne se propage jamais automatiquement,
tout en admettant qu'une modification d'une donnée source doive entraîner une
réévaluation des données dépendantes. Ces exigences paraissent contradictoires.

Les modèles existants tranchent dans l'autre sens :

- **Logique subjective avec discounting** : `ω_x^{A:B} = ω_A^B ⊗ ω_B^x` —
  héritage direct.
- **EigenTrust, PageRank** : la propagation transitive est le mécanisme
  *constitutif*.

Adopter l'un d'eux rouvre la faille visée : une donnée fabriquée à partir d'une
source réputée fiable hérite de cette réputation.

### 5.2 Le mécanisme

Un changement amont **n'altère jamais l'opinion aval**. Il **injecte une
preuve** dans le flux d'évidence aval, ensuite fusionnée avec les preuves
locales par le processus normal.

```
ALGORITHME PropagationNonTransitive

  1.  Δ ← P_y(t) − P_y(t⁻)
  2.  SI |Δ| < θ_ρ ALORS ARRÊT
  3.  σ ← −signe(Δ)
  4.  w ← γ_ρ · |Δ| · ρ^depth
  5.  w ← min( w , cap · (r_dst + s_dst + W) )      ← plafonnement
  6.  SI depth > δ_max OU dst ∈ visited ALORS ARRÊT
  7.  E_dst ← E_dst ∪ { (upstream_change, σ, w, t) }
  8.  recalculer ω_dst  puis  propager récursivement
```

### 5.3 Propriétés démontrées

Démonstrations complètes dans `PROPRIETES.md`.

**Proposition 1 — Non-suffisance.** Une donnée sans preuve locale vérifie

```
P_x ≤ (r_x + a_x·W)/(r_x + W)     et    P_x < τ   dès que   r_x < W(τ−a_x)/(1−τ)
```

Avec `γ⁺_max = 0.30`, `W = 2`, `a_x = 0.15` : `P_x ≤ 0.261` au pire cas.
*Mesure : 0.159.* Une donnée ne devient pas fiable parce que son parent l'est.

**Proposition 2 — Terminaison.** L'algorithme termine sur tout graphe, **y
compris cyclique**, en `O(Δ^δmax)` appels. Vérifié jusqu'à n = 500 nœuds
entièrement cycliques. Les modèles à point fixe requièrent au contraire une
convergence itérative globale, difficile à auditer localement.

**Proposition 3 — Découplage.** La borne de P1 ne dépend que de `γ⁺` ; `γ⁻`
n'intervient que dans `s_x`. *Vérification : `γ⁻ ×256` laisse la confiance de
la donnée fabriquée strictement inchangée (variation `0.00e+00`).*

### 5.4 Ce que P3 change

C'est le résultat central, et il n'était pas anticipé.

`γ⁺` gouverne la résistance à l'injection et **doit** rester petit. `γ⁻`
gouverne le pouvoir de détection et **peut** être grand sans aucun effet sur
l'injection — amplifier la propagation des mauvaises nouvelles n'ouvre aucun
vecteur d'attaque, puisque personne ne cherche à faire hériter de la défiance.

> L'asymétrie `γ⁻ ≫ γ⁺` n'est pas une heuristique de précaution : c'est le
> mécanisme structurel qui rend les deux objectifs simultanément atteignables.
> Les modèles transitifs ne peuvent pas l'exploiter, leur opérateur étant
> symétrique en polarité.

### 5.5 Plafonnement de la masse propagée

Découvert par les scénarios adverses. En compromission *partielle*, la masse
propagée (3–5.4) écrasait le signal local réel (0.25), et sa variation selon le
type de relation devenait la source dominante du classement — du bruit. L'AUC
tombait à 0.555, *sous* un modèle sans aucune propagation (0.788).

Correction : borner la masse injectée relativement à la masse locale déjà
présente sur la cible. Avec `cap = 1.0`, l'AUC en compromission partielle
remonte à 0.771 (parité avec 0.779) au prix de 0.006 d'AUC en compromission
totale.

---

## 6. Positionnement par rapport à l'existant

| Critère | Beta Reputation | Subjective Logic | EigenTrust | Scores industriels | **DTC** |
|---|---|---|---|---|---|
| Représentation | scalaire + variance | opinion (b,d,u,a) | scalaire | scalaire | opinion (b,d,u,a) |
| Distingue ignorance / défiance | partiellement | **oui** | non | non | **oui** |
| Décroissance temporelle | oui | possible | non | variable | **oui, typée** |
| Propagation transitive | non traitée | **constitutive** | **constitutive** | rare | **non — par conception** |
| Réaction aux changements amont | non | recalcul transitif | recalcul global | rare | **injection de preuve** |
| Terminaison sur graphe cyclique | n/a | dépend de l'opérateur | itérative | n/a | **bornée, démontrée** |
| Explicabilité | moyenne | bonne | **faible** | faible | **traçable aux preuves** |
| Résistance à l'héritage de réputation | n/a | **faible** | **faible** | faible | **objectif démontré** |

**Formulation honnête de la contribution :**

> Le DTC ne propose pas un nouveau calcul de confiance. Il propose une
> *discipline de propagation* : un mécanisme par lequel l'information de
> confiance amont influence l'aval sans être héritée, en étant convertie en
> preuve locale bornée plutôt qu'en opinion transmise. La contribution porte
> sur la propagation, pas sur la mesure.

Revendication étroite — c'est ce qui la rend défendable.

---

## 7. Résultats expérimentaux

Protocole : 30 graphes à topologies variées, partition stricte figée avant tout
calcul (10 calibration / 20 évaluation), paramètres gelés après calibration.

```
modèle             détection (AUC ↑)   injection (uplift ↓)   faux positifs
static                       0.610                  0.000           9.8 %
discounting                  0.702                  0.000           9.8 %
eigentrust                   1.000                  0.578           0.0 %
dtc                          0.970                  0.009          14.7 %
```

Contrôle de surajustement : écart calibration/évaluation de +0.017.

Le DTC atteint 97 % du pouvoir de détection du modèle transitif tout en
conservant une résistance à l'injection comparable aux modèles non
propagatifs. Aucune baseline n'occupe ce point du front de Pareto.

**Mise en garde essentielle.** Le 0 % de faux positifs d'EigenTrust n'est pas
un mérite indépendant : il porte les données saines à 0.696 alors que leurs
preuves propres n'en justifient que 0.611 — il les *gonfle* par héritage,
exactement le mécanisme qui lui donne 0.578 d'uplift d'injection. Son avantage
apparent sur les faux positifs et sa vulnérabilité à l'injection sont le même
phénomène vu sous deux angles.

---

## 8. Limites à reconnaître explicitement

1. **L'AUC de 1.000 d'EigenTrust est un artefact du scénario principal** — une
   racine compromise dont toute la descendance est affectée est exactement ce
   que la propagation transitive est conçue pour trouver.
2. **Données entièrement synthétiques.** Aucune validation sur lignage réel.
3. **P1 n'est pas inconditionnelle** — établie par événement et en régime
   permanent, pas face à un adversaire contrôlant la fréquence des événements
   amont.
4. **Corrélation partielle entre sources non traitée.**
5. **Faux positifs à 100 %** en compromission partielle : toutes les données de
   la source passent sous le seuil, même si leur *classement* reste correct.
6. **Nombreux paramètres**, dont seuls `γ⁻`, `ρ` et `cap` ont été balayés.
7. **Le modèle ne détecte rien** — il agrège des preuves produites par
   d'autres mécanismes. Sa qualité est bornée par celle de ses capteurs.

---

## 9. Structure d'article proposée

Cadrage recommandé : **ne pas** présenter le papier comme « voici une nouvelle
architecture ». Le présenter comme « voici un mécanisme de propagation de
confiance qui résout un problème précis ». L'architecture devient le contexte,
pas la revendication. Un papier à contribution étroite et démontrée passe ; un
papier annonçant une architecture entière se fait rejeter pour manque de focus.

1. Introduction — l'héritage de réputation dans le lignage de données
2. Related Work — Jøsang ; Ismail & Jøsang ; Kamvar et al. ; W3C PROV ;
   XACML / OPA
3. Modèle formel
4. Propagation non transitive
5. Propriétés démontrées (P1, P2, P3)
6. Évaluation — protocole, front de Pareto, scénarios adverses
7. Résultats négatifs et limites
8. Conclusion

Cible réaliste : workshop ou conférence de niveau intermédiaire en sécurité /
gouvernance des données, doublé d'un preprint arXiv (cs.CR).

---

## 10. Prochaines étapes

- [ ] Borne inconditionnelle sur `r_x` (plafonnement absolu `r_cap`)
- [ ] Réduire les faux positifs en compromission partielle
- [ ] Sensibilité à `θ_ρ` et `λ_τ`
- [ ] Validation sur un lignage réel (Apache Atlas, OpenLineage)
- [ ] Rédaction de la section *Related Work*
- [ ] Preprint arXiv, puis démarchage de co-auteur
