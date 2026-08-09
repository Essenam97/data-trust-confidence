# Propriétés formelles du DTC

Démonstrations des propriétés annoncées au §5.3 de la formalisation.
Vérifications empiriques correspondantes : `proofs_check.py`.

---

## Notations

| Symbole | Signification |
|---|---|
| `W` | poids d'ignorance a priori (`W = 2`) |
| `a_x` | taux de base de la donnée `x`, fixé par politique |
| `r_x, s_x` | masses de preuve positive / négative après décroissance |
| `γ⁺_ρ, γ⁻_ρ` | facteurs d'atténuation positif / négatif du type de relation `ρ` |
| `γ⁺_max` | `max_ρ γ⁺_ρ` |
| `δ_max` | profondeur maximale de propagation |
| `Δ` | degré sortant maximal du graphe |
| `λ_u` | taux de décroissance des preuves `upstream_change` |

---

## Proposition 1 — Non-suffisance de l'ascendance

> **Énoncé.** Soit `x` une donnée ne possédant **aucune preuve locale**, dont
> toutes les preuves sont de type `upstream_change` de polarité positive.
> Alors sa confiance projetée est bornée par
>
> ```
> P_x  ≤  (r_x + a_x · W) / (r_x + W)
> ```
>
> et en particulier, pour tout seuil `τ > a_x`, on a `P_x < τ` dès que
>
> ```
> r_x  <  W · (τ − a_x) / (1 − τ)
> ```

### Démonstration

Par hypothèse `s_x = 0`. Le mapping Beta donne

```
b_x = r_x / (r_x + W)      d_x = 0      u_x = W / (r_x + W)
```

La projection vaut

```
P_x = b_x + a_x · u_x
    = r_x/(r_x + W) + a_x · W/(r_x + W)
    = (r_x + a_x·W) / (r_x + W)                                    (1)
```

ce qui établit la borne. Résolvons `P_x < τ` :

```
(r_x + a_x·W) / (r_x + W) < τ
⟺  r_x + a_x·W  <  τ·r_x + τ·W
⟺  r_x(1 − τ)   <  W(τ − a_x)
⟺  r_x          <  W(τ − a_x)/(1 − τ)          pour τ < 1          (2)
```

∎

### Conséquence opérationnelle

La quantité `r_x` est entièrement contrôlée par la politique. Chaque événement
de propagation positive injecte une masse

```
w = γ⁺_ρ · |ΔP_y| · ρ^depth  ≤  γ⁺_max          car |ΔP_y| ≤ 1, ρ ≤ 1
```

**Cas d'un événement unique.** Avec les valeurs de référence
`γ⁺_max = 0.30`, `W = 2`, `a_x = 0.15` :

```
r_x ≤ 0.30   ⟹   P_x ≤ (0.30 + 0.30)/2.30 = 0.261
```

La donnée fabriquée ne peut pas dépasser 0.261, très en deçà de la confiance
de son parent (0.976). La mesure expérimentale donne 0.159, cohérente avec la
borne (l'écart vient de `|ΔP_y| < 1`).

**Cas de N événements — limite à assumer.** La proposition borne `r_x` à un
instant donné, pas le nombre d'événements. Un attaquant capable de déclencher
répétitivement des améliorations de confiance amont pourrait accumuler de la
masse positive. Deux garde-fous existent :

1. *Décroissance.* Les preuves `upstream_change` décroissent au taux `λ_u`.
   Pour une fréquence d'événements `f`, la masse converge vers un régime
   permanent
   ```
   r_x^∞  ≈  γ⁺_max · f / λ_u
   ```
   Avec `λ_u = 0.02` et `γ⁺_max = 0.30`, franchir `τ = 0.5` (soit
   `r_x ≥ 1.4` d'après (2)) exigerait `f ≥ 0.093` événement par unité de
   temps, **soutenu indéfiniment**, chaque événement devant en outre produire
   `|ΔP_y| ≈ 1`.

2. *Plafonnement explicite.* Imposer par politique
   `Σ masses upstream_change positives ≤ r_cap` rend la borne inconditionnelle.

**Le point 2 n'est pas implémenté dans le code de référence.** C'est une
faiblesse à signaler telle quelle : la propriété P1 est établie *par
événement* et en régime permanent, pas de façon inconditionnelle sur un
historique adverse arbitraire.

*Note.* Le plafonnement `cap_ratio` introduit au §« plafonnement de la masse
propagée » borne chaque injection à `cap_ratio × (r + s + W)` de la cible.
Il atténue le problème sans le résoudre : la borne reste relative à la masse
déjà présente, donc croissante.

---

## Proposition 2 — Terminaison

> **Énoncé.** L'algorithme de propagation termine sur tout graphe orienté,
> **y compris cyclique**, en un nombre d'appels borné par
>
> ```
> N  ≤  Σ_{k=1..δ_max} Δ^k  =  O(Δ^{δ_max})
> ```

### Démonstration

Considérons la fonction de rang `φ(appel) = δ_max − depth`.

À l'entrée de `_propagate`, la condition `depth ≥ δ_max` provoque un retour
immédiat. Tout appel récursif est effectué avec `depth + 1`, donc `φ` décroît
strictement à chaque niveau de récursion et reste entière positive. La
récursion ne peut donc pas dépasser `δ_max` niveaux.

Par ailleurs, chaque appel transmet `visited ∪ {dst}`, et tout successeur déjà
présent dans `visited` est ignoré. Le long d'une branche donnée, aucun nœud
n'est traité deux fois : les branches correspondent aux **chemins simples** du
graphe, de longueur au plus `δ_max`.

Le nombre de tels chemins issus d'un nœud est majoré par `Σ_{k=1..δ_max} Δ^k`,
d'où la borne. La terminaison ne dépend d'aucune hypothèse d'acyclicité. ∎

### Comparaison

Les modèles à point fixe (EigenTrust, PageRank) requièrent une itération
globale jusqu'à convergence — coûteuse, et dont le résultat en un nœud dépend
de l'intégralité du graphe. Le DTC borne le calcul localement, ce qui rend
chaque évaluation auditable indépendamment.

### Vérification empirique

Sur des graphes **entièrement cycliques** (cycle hamiltonien + arêtes
aléatoires) :

```
n=   5 arêtes=   7 → 0.11 ms,   13 propagations, profondeur max 4
n=  20 arêtes=  35 → 0.23 ms,   50 propagations, profondeur max 4
n=  60 arêtes= 110 → 0.08 ms,  115 propagations, profondeur max 4
n= 200 arêtes= 380 → 1.36 ms,  441 propagations, profondeur max 4
```

Aucune divergence. La profondeur plafonne à `δ_max = 4` comme prévu, et le
nombre de propagations croît linéairement avec la taille du graphe sur ces
instances (le majorant `O(Δ^{δ_max})` reste pessimiste).

---

## Proposition 3 — Découplage détection / injection

> **Énoncé.** La borne de la Proposition 1 ne dépend que de `γ⁺`. Le facteur
> `γ⁻` peut être augmenté arbitrairement sans affecter `P_x` pour une donnée
> dont les preuves de propagation sont positives.

### Démonstration

Immédiate : dans (1), `r_x` n'agrège que des preuves de polarité positive,
dont les poids sont proportionnels à `γ⁺_ρ`. Le facteur `γ⁻_ρ` n'intervient
que dans le calcul de `s_x`, absent de l'hypothèse. ∎

### Portée

C'est la justification formelle du résultat expérimental principal :
amplifier `γ⁻` d'un facteur 16 fait passer l'AUC de 0.669 à 0.971 sans que
l'uplift d'injection bouge (0.009 constant).

L'asymétrie `γ⁻ ≫ γ⁺` n'est donc pas un réglage empirique heureux, mais la
conséquence d'une propriété structurelle : **la vulnérabilité à l'injection et
le pouvoir de détection sont gouvernés par des paramètres disjoints.** Les
modèles transitifs ne peuvent pas exploiter ce découplage, leur opérateur de
propagation étant symétrique en polarité.

Vérification empirique : `γ⁻` multiplié par 256 laisse la confiance de la
donnée fabriquée strictement inchangée (variation mesurée : 0.00e+00).

---

## Plafonnement de la masse propagée

Une seconde limite, découverte par les scénarios adverses.

**Symptôme.** En compromission *partielle* — seule une fraction des données
issues de la source est réellement touchée — le DTC s'effondrait à AUC 0.555,
nettement en dessous de `static` (0.788) qui ne propage rien du tout. La
propagation *nuisait*.

**Diagnostic.** Masses de preuve mesurées sur les données enfants :

```
donnée    touchée   r local   s local   s propagé      P
rec_0       False      0.61      0.00        3.07   0.266
rec_1        True      0.61      0.25        3.07   0.255
rec_2       False      0.61      0.00        4.61   0.211
rec_4       False      0.61      0.00        5.38   0.191
```

La masse propagée (3.07 à 5.38) écrase le signal local réel (0.25). Pire, sa
variation entre données ne reflète que le **type de relation** — c'est-à-dire
du bruit — et devient la source dominante du classement.

**Correction.** Plafonner la masse injectée relativement à la masse locale
déjà présente sur la cible :

```
w  ←  min( γ_ρ · |ΔP| · ρ^depth ,  cap_ratio · (r_dst + s_dst + W) )
```

Calibration du plafond (jeu de calibration + scénario partiel seeds 0–7) :

```
   cap   AUC total   FP total   AUC partiel
 aucun       0.971      12.6%         0.555
   2.0       0.970      12.6%         0.643
   1.0       0.965      10.2%         0.791
   0.4       0.919       9.1%         0.791
  0.15       0.771       9.1%         0.791
```

`cap_ratio = 1.0` est retenu : il restaure la performance en compromission
partielle (0.555 → 0.791) au prix de 0.006 d'AUC en compromission totale, et
réduit au passage les faux positifs. Le plafond rendant l'amplification moins
risquée, la calibration sélectionne ensuite `γ⁻ ×48` au lieu de `×16`.

Vérification sur seeds disjoints (100–119) : DTC 0.771 contre `static` 0.779,
soit une quasi-parité — l'effondrement est corrigé.

---

## Proposition 4 — Résistance à la diffamation

> **Modèle d'adversaire.** Un attaquant contrôle une source `y` dont dérivent
> des données victimes qu'il ne contrôle pas. Il peut déclencher un nombre
> arbitraire `N` d'événements dégradant `P_y`, et les alterner avec des
> rétablissements. Son objectif est de faire passer les victimes sous le seuil
> de gouvernance — un déni de service sur la gouvernance.
>
> **Énoncé.** En mode `standing`, la masse de preuve de propagation portée par
> une donnée `x` est bornée par
>
> ```
> s_x^prop(t)  ≤  Σ_{y ∈ pred(x)}  γ⁻_ρ(y,x) · max_t |ΔP_y|  ≤  |pred(x)| · γ⁻_max
> ```
>
> **indépendamment de `N`.**

### Démonstration

En mode `standing`, avant toute insertion d'une preuve `upstream_change`
d'origine `y`, toute preuve existante de même type et de même origine est
retirée de `E_x`. L'invariant suivant est donc préservé :

```
∀ y ,  | { e ∈ E_x : e.type = upstream_change ∧ e.origin = y } | ≤ 1
```

Le cardinal de l'ensemble des preuves de propagation portées par `x` est ainsi
majoré par le degré entrant `|pred(x)|`, quel que soit le nombre d'événements
survenus en amont. Chaque preuve a un poids majoré par `γ⁻_ρ·|ΔP_y| ≤ γ⁻_ρ`
puisque `|ΔP| ≤ 1`. La somme est donc bornée par `|pred(x)|·γ⁻_max`. ∎

### Comparaison avec le mode `accumulate`

En mode `accumulate`, chaque événement amont **ajoute** une preuve. La masse
croît alors en `Θ(N)` et n'est bornée que par la décroissance temporelle. Un
attaquant maintenant une fréquence suffisante fait diverger la masse.

### Vérification empirique

Proportion de données **légitimes et bien attestées** poussées sous le seuil
0.45 par un adversaire ne contrôlant qu'une source dont elles dérivent :

```
impulsions    static  discounting  eigentrust   dtc accumulate   dtc standing
         2        0%           0%          0%            100%             0%
         4        0%           0%          0%            100%             0%
        16        0%           0%          0%            100%             0%
```

L'amplitude ne compense pas la répétition : une impulsion unique d'intensité
croissante (×1 à ×32) laisse la confiance des victimes à 0.876, inchangée.

### Portée

Cette vulnérabilité est **propre au DTC**. Elle n'existe ni dans le modèle de
Biba — dont les niveaux d'intégrité sont discrets et la propagation non
amplifiée — ni dans EBSL, qui interdit tout facteur supérieur à l'unité. Elle
est le prix de l'amplification `γ⁻ ≫ 1` qui donne au DTC son pouvoir de
détection.

Le mode `standing` la referme sans renoncer à l'amplification. C'est,
avec la Proposition 3, le principal résultat technique du modèle.

### Coût

| | `accumulate` | `standing` |
|---|---|---|
| détection (AUC, jeu tenu à l'écart) | 0.970 | 0.957 |
| injection (uplift) | 0.009 | 0.009 |
| diffamation (victimes bloquées) | **100 %** | **0 %** |
| compromission partielle (AUC) | 0.771 | 0.783 |

Perte de 0.013 d'AUC contre l'immunité complète à la diffamation, et une
amélioration en compromission partielle.

### Interprétation

Le changement est sémantique autant que technique. En mode `accumulate`, une
donnée aval porte l'**historique des variations** de son amont. En mode
`standing`, elle porte l'**état courant** de son amont. La seconde lecture est
la bonne : ce qui importe pour gouverner une donnée n'est pas combien de fois
sa source a vacillé, mais où elle en est.

---

## Résultat négatif — modulation par la distance au foyer

Hypothèse testée : moduler le poids injecté par `ρ^depth` (`ρ < 1`) devait
réduire les faux positifs, une donnée éloignée du foyer ne devant pas être
dégradée autant qu'une copie directe.

**Hypothèse réfutée.** Balayage conjoint sur le jeu de calibration :

```
γ⁻ ×16 :  ρ=1.0 → AUC 0.971, FP 12.6 %
          ρ=0.6 → AUC 0.893, FP 11.5 %
          ρ=0.3 → AUC 0.820, FP 11.4 %
```

(balayage antérieur au plafonnement)

`ρ` dégrade la détection bien plus vite qu'il ne réduit les faux positifs.
Le meilleur point admissible reste `ρ = 1.0`, c'est-à-dire sans modulation.

**Diagnostic.** Les faux positifs ne proviennent pas de la propagation
lointaine. Mesure des scores moyens des données saines :

```
modèle          P̄ saines   P̄ affectées   faux pos.
static             0.611         0.581       9.4 %
discounting        0.553         0.507       9.4 %
eigentrust         0.696         0.452       0.0 %
dtc                0.582         0.318      15.6 %
```

`static` ne propage rien et affiche déjà 9.4 % de faux positifs : c'est un
**plancher intrinsèque** aux preuves locales (`transformation_opaque`,
`base_rate` bas). La propagation du DTC n'ajoute qu'environ 6 points.

Surtout, le 0 % d'EigenTrust n'est pas un mérite indépendant : il porte les
données saines à 0.696 alors que leurs preuves propres n'en justifient que
0.611. Il les **gonfle** par héritage. C'est exactement le mécanisme qui lui
donne un uplift d'injection de 0.578.

> **À retenir pour la rédaction.** L'avantage apparent d'EigenTrust sur les
> faux positifs et sa vulnérabilité à l'injection sont le *même phénomène*
> observé sous deux angles. On ne peut pas obtenir l'un sans l'autre. La
> comparaison brute des taux de faux positifs est donc trompeuse et doit être
> présentée avec cette mise en garde.

Le paramètre `rho` est conservé dans le code (valeur par défaut `1.0`,
neutre) afin que le résultat négatif reste reproductible.

---

## Ce qui reste à démontrer

- [ ] Borne inconditionnelle sur `r_x` en présence d'un adversaire contrôlant
      la fréquence des événements amont (plafonnement `r_cap`)
- [ ] Comportement en régime permanent : convergence ou oscillation de `P`
      sous flux continu de preuves
- [ ] Sensibilité de l'AUC aux paramètres `θ_ρ` et `λ_τ` (seuls `γ⁻`, `ρ` et
      `cap_ratio` ont été balayés)
- [ ] Réduire les faux positifs en compromission partielle (100 % : toutes les
      données de la source passent sous le seuil, même si leur *classement*
      reste correct)
