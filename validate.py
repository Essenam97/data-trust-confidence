"""Balayage : la propagation négative peut-elle être forte sans casser P1 ?"""
from dtc import graph as G
from dtc.graph import RelationPolicy
from dtc.scenarios import lineage_compromise, injection_resistance
from dtc.experiment import run, run_injection

BASE = {"copy":(0.90,0.30),"derivation":(0.70,0.20),"transformation":(0.60,0.18),
        "aggregation":(0.40,0.10),"reference":(0.25,0.05)}

def set_scale(sm, sp):
    for k,(gm,gp) in BASE.items():
        old = G.RELATION_POLICIES[k]
        G.RELATION_POLICIES[k] = RelationPolicy(k, old.theta, gm*sm, gp*sp)

print(f"{'γ⁻ ×':>6}{'γ⁺ ×':>7}{'couverture':>12}{'faux pos.':>11}{'uplift inj.':>13}")
print("-"*49)
for sm in [1,2,4,8,16,32]:
    set_scale(sm, 1.0)
    r = {x.model:x for x in run(lineage_compromise(seed=42), 55.0, 0.45)}["dtc"]
    inj = run_injection(injection_resistance(), 10.0)["dtc"]
    print(f"{sm:>6}{1.0:>7}{r.coverage:>11.1%}{r.false_positive:>11.1%}{inj['uplift']:>13.3f}")
