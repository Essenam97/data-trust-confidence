============================================================================
PROTOCOLE — séparation calibration / évaluation
============================================================================

graphes de calibration : 10  seeds=[310, 655, 1133, 2471, 2474, 3492, 3674, 4838, 5058, 6201]
graphes d'évaluation   : 20  seeds=[153, 448, 2413, 2857, 2982, 5092, 5302, 5416, 5910, 6152, 6448, 7264, 7642, 7885, 9391, 9392, 9673, 9741, 9844, 9851]
partition disjointe, figée avant tout calcul.

============================================================================
PHASE 1 — calibration de γ⁻ (jeu de calibration UNIQUEMENT)
============================================================================

Critère retenu : maximiser l'AUC sous contrainte de faux positifs
≤ 15 % au seuil 0.45. Le critère est fixé avant le balayage.

   γ⁻ ×   AUC calib.   faux pos.   admissible
---------------------------------------------
      1        0.669        9.1%          oui
      2        0.698        9.1%          oui
      4        0.762        9.1%          oui
      8        0.882        9.3%          oui
     12        0.940        9.7%          oui
     16        0.963       10.1%          oui
     24        0.983       10.3%          oui
     32        0.988       10.4%          oui
     48        0.989       10.5%          oui

→ γ⁻ retenu : ×48  (AUC calib. 0.989, FP 10.5%)
→ valeur GELÉE. Le jeu d'évaluation n'a influencé aucun choix.

============================================================================
PHASE 2 — évaluation sur 20 graphes jamais vus
============================================================================

modèle            AUC moy.        σ     min     max   FP moy.
-------------------------------------------------------------
static               0.610    0.070   0.518   0.772      9.8%
discounting          0.702    0.111   0.548   0.884      9.8%
eigentrust           1.000    0.001   0.997   1.000      0.0%
dtc                  0.957    0.082   0.663   1.000     13.1%

AUC calibration : 0.989
AUC évaluation  : 0.957
écart           : +0.032  → écart faible, acceptable

============================================================================
Résistance à l'injection (indépendante du jeu de graphes)
============================================================================

modèle             fabriquée    témoin    uplift
------------------------------------------------
static                 0.150     0.150     0.000
discounting            0.150     0.150     0.000
eigentrust             0.728     0.150     0.578
dtc                    0.159     0.150     0.009

============================================================================
SYNTHÈSE — résultats sur jeu d'évaluation tenu à l'écart
============================================================================

modèle             détection (AUC ↑)  injection (uplift ↓)
----------------------------------------------------------
static                         0.610                 0.000
discounting                    0.702                 0.000
eigentrust                     1.000                 0.578
dtc                            0.957                 0.009
