"""
Protocole de validation avec séparation stricte calibration / évaluation.

Corrige la faiblesse méthodologique n°2 du README : les facteurs
d'atténuation étaient calibrés sur les graphes servant à l'évaluation.

Protocole
---------
  1. 30 graphes générés avec des structures VARIÉES (profondeur, ramification,
     nombre de sources tirés aléatoirement).
  2. Partition stricte : 10 graphes de calibration, 20 d'évaluation.
     Les seeds sont disjoints et la partition est figée avant tout calcul.
  3. Le facteur gamma_m est choisi UNIQUEMENT sur le jeu de calibration.
  4. La valeur retenue est gelée, puis appliquée telle quelle au jeu
     d'évaluation, qui n'a jamais influencé aucun choix.

Aucune dépendance externe.
"""

from __future__ import annotations

import random
import statistics as st

from dtc import graph as G
from dtc.graph import RelationPolicy
from dtc.scenarios import lineage_compromise, injection_resistance
from dtc.experiment import build_models, run_injection

T_EVAL = 55.0

# Facteurs de base, avant application du facteur d'échelle balayé.
BASE_GAMMA = {
    "copy":           (0.90, 0.30),
    "derivation":     (0.70, 0.20),
    "transformation": (0.60, 0.18),
    "aggregation":    (0.40, 0.10),
    "reference":      (0.25, 0.05),
}

# --- partition figée AVANT tout calcul -------------------------------------
_rng = random.Random(20240808)
ALL_SEEDS = _rng.sample(range(1, 10_000), 30)
CALIB_SEEDS = ALL_SEEDS[:10]
EVAL_SEEDS = ALL_SEEDS[10:]
assert not (set(CALIB_SEEDS) & set(EVAL_SEEDS)), "partition non disjointe"


def set_gamma_scale(scale_minus: float, scale_plus: float = 1.0) -> None:
    """Applique un facteur d'échelle aux atténuations de propagation."""
    for k, (gm, gp) in BASE_GAMMA.items():
        old = G.RELATION_POLICIES[k]
        G.RELATION_POLICIES[k] = RelationPolicy(
            k, old.theta, gm * scale_minus, gp * scale_plus)


def varied_scenario(seed: int):
    """Graphe à structure aléatoire — évite que le jeu d'évaluation soit
    une simple répétition de la même topologie."""
    rng = random.Random(seed)
    return lineage_compromise(
        seed=seed,
        n_clean_roots=rng.choice([3, 4, 6, 8, 10]),
        fanout=rng.choice([2, 3, 4]),
        depth=rng.choice([2, 3, 4]),
    )


def auc(pairs) -> float:
    """AUC par statistique de rangs (Mann-Whitney U), en O(n log n).

    Équivalent exact au comptage par paires, égalités comprises.
    Convention : un score BAS sur une donnée affectée est un succès.
    """
    n_aff = sum(1 for _, a in pairs if a)
    n_cln = len(pairs) - n_aff
    if n_aff == 0 or n_cln == 0:
        return float("nan")

    ordered = sorted(pairs, key=lambda x: x[0])
    ranks = [0.0] * len(ordered)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0          # rangs moyens sur les ex aequo
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1

    r_aff = sum(r for r, (_, a) in zip(ranks, ordered) if a)
    u = r_aff - n_aff * (n_aff + 1) / 2.0
    return 1.0 - u / (n_aff * n_cln)


def fp_rate(pairs, threshold: float) -> float:
    cln = [p for p, a in pairs if not a]
    return sum(1 for p in cln if p < threshold) / len(cln) if cln else 0.0


def evaluate(seeds, models=("static", "discounting", "eigentrust", "dtc")):
    """Retourne {modèle: {'auc': [...], 'fp': [...]}} sur les seeds donnés."""
    out = {m: {"auc": [], "fp": []} for m in models}
    for s in seeds:
        scn = varied_scenario(s)
        built = build_models(scn)
        for name in models:
            m = built[name]
            for t, dio, ev in scn.timeline:
                m.add_evidence(dio, ev)
            pairs = [(m.projected(d, T_EVAL), n.truly_affected)
                     for d, n in scn.graph.nodes.items()]
            out[name]["auc"].append(auc(pairs))
            out[name]["fp"].append(fp_rate(pairs, 0.45))
    return out


# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 76)
    print("PROTOCOLE — séparation calibration / évaluation")
    print("=" * 76)
    print(f"\ngraphes de calibration : {len(CALIB_SEEDS)}  seeds={sorted(CALIB_SEEDS)}")
    print(f"graphes d'évaluation   : {len(EVAL_SEEDS)}  seeds={sorted(EVAL_SEEDS)}")
    print("partition disjointe, figée avant tout calcul.\n")

    # ---- PHASE 1 : calibration ------------------------------------------
    print("=" * 76)
    print("PHASE 1 — calibration de γ⁻ (jeu de calibration UNIQUEMENT)")
    print("=" * 76)
    print("\nCritère retenu : maximiser l'AUC sous contrainte de faux positifs")
    print("≤ 15 % au seuil 0.45. Le critère est fixé avant le balayage.\n")
    print(f"{'γ⁻ ×':>7}{'AUC calib.':>13}{'faux pos.':>12}{'admissible':>13}")
    print("-" * 45)

    candidates = [1, 2, 4, 8, 12, 16, 24, 32, 48]
    calib_results = []
    for sc in candidates:
        set_gamma_scale(sc)
        r = evaluate(CALIB_SEEDS, models=("dtc",))["dtc"]
        a, f = st.mean(r["auc"]), st.mean(r["fp"])
        ok = f <= 0.15
        calib_results.append((sc, a, f, ok))
        print(f"{sc:>7}{a:>13.3f}{f:>12.1%}{'oui' if ok else 'non':>13}")

    admissible = [c for c in calib_results if c[3]]
    best = max(admissible, key=lambda c: c[1])
    CHOSEN = best[0]
    print(f"\n→ γ⁻ retenu : ×{CHOSEN}  (AUC calib. {best[1]:.3f}, FP {best[2]:.1%})")
    print("→ valeur GELÉE. Le jeu d'évaluation n'a influencé aucun choix.\n")

    # ---- PHASE 2 : évaluation sur jeu tenu à l'écart ---------------------
    set_gamma_scale(CHOSEN)
    print("=" * 76)
    print(f"PHASE 2 — évaluation sur {len(EVAL_SEEDS)} graphes jamais vus")
    print("=" * 76 + "\n")

    res = evaluate(EVAL_SEEDS)
    print(f"{'modèle':<16}{'AUC moy.':>10}{'σ':>9}{'min':>8}{'max':>8}{'FP moy.':>10}")
    print("-" * 61)
    for name, d in res.items():
        v = d["auc"]
        print(f"{name:<16}{st.mean(v):>10.3f}{st.pstdev(v):>9.3f}"
              f"{min(v):>8.3f}{max(v):>8.3f}{st.mean(d['fp']):>10.1%}")

    # ---- écart calibration / évaluation : détection de surajustement -----
    calib_dtc = st.mean(evaluate(CALIB_SEEDS, models=("dtc",))["dtc"]["auc"])
    eval_dtc = st.mean(res["dtc"]["auc"])
    gap = calib_dtc - eval_dtc
    print(f"\nAUC calibration : {calib_dtc:.3f}")
    print(f"AUC évaluation  : {eval_dtc:.3f}")
    print(f"écart           : {gap:+.3f}", end="  ")
    if abs(gap) < 0.02:
        print("→ aucun surajustement détectable")
    elif abs(gap) < 0.05:
        print("→ écart faible, acceptable")
    else:
        print("→ ⚠ surajustement probable")

    # ---- résistance à l'injection ---------------------------------------
    print("\n" + "=" * 76)
    print("Résistance à l'injection (indépendante du jeu de graphes)")
    print("=" * 76 + "\n")
    inj = run_injection(injection_resistance(), t_eval=10.0)
    print(f"{'modèle':<16}{'fabriquée':>12}{'témoin':>10}{'uplift':>10}")
    print("-" * 48)
    for m, v in inj.items():
        print(f"{m:<16}{v['fabricated']:>12.3f}{v['orphan']:>10.3f}{v['uplift']:>10.3f}")

    # ---- synthèse --------------------------------------------------------
    print("\n" + "=" * 76)
    print("SYNTHÈSE — résultats sur jeu d'évaluation tenu à l'écart")
    print("=" * 76 + "\n")
    print(f"{'modèle':<16}{'détection (AUC ↑)':>20}{'injection (uplift ↓)':>22}")
    print("-" * 58)
    for name in res:
        print(f"{name:<16}{st.mean(res[name]['auc']):>20.3f}"
              f"{inj[name]['uplift']:>22.3f}")


if __name__ == "__main__":
    main()
