"""
Scénarios adverses — cas délibérément défavorables au modèle.

Un papier qui n'évalue que des scénarios favorables se fait rejeter.
"""
import statistics as st

from dtc.scenarios import partial_compromise, late_revelation
from dtc.experiment import build_models
from validate import auc, fp_rate, set_gamma_scale

set_gamma_scale(16)

print("=" * 74)
print("ADVERSE 1 — Compromission PARTIELLE")
print("=" * 74)
print("\nÉvalué sur 20 graphes (seeds 100-119), disjoints des seeds 0-7")
print("ayant servi à calibrer le plafond de masse propagée.")
print("\nSeules 40 % des données issues de la source sont réellement touchées.")
print("Le lignage ne suffit plus : des voisines immédiates partagent la même")
print("ascendance sans être affectées. Cas défavorable à toute propagation.\n")
print(f"{'modèle':<16}{'AUC':>9}{'faux pos.':>12}")
print("-" * 37)
agg = {}
for seed in range(100, 120):   # seeds DISJOINTS de la calibration (0-7)
    scn = partial_compromise(seed=seed)
    for name, m in build_models(scn).items():
        for t, dio, ev in scn.timeline:
            m.add_evidence(dio, ev)
        pairs = [(m.projected(d, 55.0), n.truly_affected)
                 for d, n in scn.graph.nodes.items()]
        a = agg.setdefault(name, {"auc": [], "fp": []})
        a["auc"].append(auc(pairs)); a["fp"].append(fp_rate(pairs, 0.45))
for k, v in agg.items():
    print(f"{k:<16}{st.mean(v['auc']):>9.3f}{st.mean(v['fp']):>12.1%}")

print("\n" + "=" * 74)
print("ADVERSE 3 — DIFFAMATION")
print("=" * 74)
print("\nUn adversaire contrôle UNE source dont dérivent 30 données légitimes,")
print("bien attestées, qu'il ne contrôle pas. Il alterne dégradations et")
print("rétablissements pour accumuler de la défiance en aval.\n")
from dtc.scenarios import slander
from dtc.engine import DTCEngine
print(f"{'impulsions':>11}{'static':>9}{'discount':>10}{'eigen':>9}{'dtc accum.':>12}{'dtc stand.':>12}")
print("-" * 63)
for n in [1, 2, 4, 8, 16]:
    scn = slander(n_pulses=n)
    te = 10.0 + 5.0 * n + 2.0
    row = []
    for name, m in build_models(scn).items():
        for t, dio, ev in scn.timeline:
            m.add_evidence(dio, ev)
        v = [m.projected(f"victim_{i}", te) for i in range(30)]
        row.append(sum(1 for p in v if p < 0.45) / len(v))
    scn2 = slander(n_pulses=n)
    ma = DTCEngine(graph=scn2.graph, propagation_mode="accumulate")
    for t, dio, ev in scn2.timeline:
        ma.add_evidence(dio, ev)
    va = [ma.projected(f"victim_{i}", te) for i in range(30)]
    acc = sum(1 for p in va if p < 0.45) / len(va)
    print(f"{n:>11}{row[0]:>9.0%}{row[1]:>10.0%}{row[2]:>9.0%}{acc:>12.0%}{row[3]:>12.0%}")
print("\nLe mode 'standing' referme la vulnérabilité sans renoncer à")
print("l'amplification qui donne au DTC son pouvoir de détection.")

print("\n" + "=" * 74)
print("ADVERSE 2 — Compromission révélée TARDIVEMENT")
print("=" * 74)
print("\nTeste λ = 0 sur `origin_compromise` : la défiance doit-elle survivre")
print("à un long délai ? Sinon, attendre suffirait à blanchir la donnée.\n")
print(f"{'délai':>10}{'P source':>12}{'P enfant':>12}")
print("-" * 34)
for delay in [60.0, 200.0, 1000.0, 5000.0, 50000.0]:
    scn = late_revelation(delay=delay)
    m = build_models(scn)["dtc"]
    for t, dio, ev in scn.timeline:
        m.add_evidence(dio, ev)
    te = delay + 5.0
    print(f"{delay:>10.0f}{m.projected('src', te):>12.3f}{m.projected('child', te):>12.3f}")
print("\nLa défiance ne s'érode pas avec le délai : λ = 0 fait son office.")
print("À comparer avec les preuves POSITIVES anciennes, qui elles décroissent —")
print("d'où une source d'autant plus dégradée que la révélation est tardive.")
