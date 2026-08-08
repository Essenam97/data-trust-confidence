"""
Expériences de référence du Data Trust Confidence.

Reproductibilité : python3 run_experiment.py
Aucune dépendance externe (bibliothèque standard uniquement).
"""
import statistics as st

from dtc.scenarios import lineage_compromise, injection_resistance
from dtc.experiment import build_models, run, run_injection, format_table

SEEDS = [1, 7, 13, 42, 99, 123, 777, 2024]
T_EVAL = 55.0


def auc(pairs):
    """P(score d'une donnée affectée < score d'une donnée saine).
    0.5 = aucun pouvoir discriminant ; 1.0 = séparation parfaite."""
    aff = [p for p, a in pairs if a]
    cln = [p for p, a in pairs if not a]
    if not aff or not cln:
        return float("nan")
    wins = sum(1 for x in aff for y in cln if x < y)
    ties = sum(1 for x in aff for y in cln if x == y)
    return (wins + 0.5 * ties) / (len(aff) * len(cln))


def scores_for(seed):
    scn = lineage_compromise(seed=seed)
    out = {}
    for name, m in build_models(scn).items():
        for t, dio, ev in scn.timeline:
            m.add_evidence(dio, ev)
        out[name] = [(m.projected(d, T_EVAL), n.truly_affected)
                     for d, n in scn.graph.nodes.items()]
    return out


def main():
    print("=" * 74)
    print("EXPÉRIENCE 1 — Pouvoir discriminant (AUC, 8 graphes indépendants)")
    print("=" * 74)
    agg = {}
    for s in SEEDS:
        for name, pairs in scores_for(s).items():
            agg.setdefault(name, []).append(auc(pairs))
    print(f"\n{'modèle':<16}{'AUC moy.':>10}{'écart-type':>12}{'min':>8}{'max':>8}")
    print("-" * 54)
    for k, v in agg.items():
        print(f"{k:<16}{st.mean(v):>10.3f}{st.pstdev(v):>12.3f}"
              f"{min(v):>8.3f}{max(v):>8.3f}")

    print("\n" + "=" * 74)
    print("EXPÉRIENCE 2 — Résistance à l'injection")
    print("=" * 74)
    print("\nUne donnée SANS aucune preuve propre, déclarée dérivée d'une source")
    print("Co-Attestée. Uplift = confiance gagnée par la seule ascendance.\n")
    inj = run_injection(injection_resistance(), t_eval=10.0)
    print(f"{'modèle':<16}{'source':>10}{'fabriquée':>12}{'témoin':>10}{'uplift':>10}")
    print("-" * 58)
    for m, v in inj.items():
        print(f"{m:<16}{v['trusted_source']:>10.3f}{v['fabricated']:>12.3f}"
              f"{v['orphan']:>10.3f}{v['uplift']:>10.3f}")

    print("\n" + "=" * 74)
    print("SYNTHÈSE — front de Pareto")
    print("=" * 74)
    print(f"\n{'modèle':<16}{'détection (AUC)':>18}{'injection (uplift)':>20}")
    print("-" * 54)
    for k in agg:
        print(f"{k:<16}{st.mean(agg[k]):>18.3f}{inj[k]['uplift']:>20.3f}")
    print("\nObjectif : AUC élevée ET uplift faible.")
    print("Aucune baseline n'atteint les deux simultanément.")

    print("\n" + "=" * 74)
    print("DÉTAIL — seuil de décision fixé à 0.45 (graphe seed=42)")
    print("=" * 74 + "\n")
    print(format_table(run(lineage_compromise(seed=42), T_EVAL, 0.45)))


if __name__ == "__main__":
    main()
