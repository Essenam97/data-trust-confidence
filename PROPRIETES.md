"""
Vérification empirique des propositions démontrées dans PROPRIETES.md.

  Prop. 1 — non-suffisance : la borne analytique est-elle respectée ?
  Prop. 2 — terminaison sur graphe cyclique
  Prop. 3 — découplage : γ⁻ n'affecte pas la confiance d'une donnée fabriquée

Exécution : python3 proofs_check.py
"""

from __future__ import annotations

import random
import time

from dtc.engine import DTCEngine
from dtc.evidence import make_evidence, POSITIVE, NEGATIVE
from dtc.graph import DRG, RELATION_POLICIES, RelationPolicy
from dtc.opinion import W_PRIOR
from dtc.scenarios import injection_resistance
from dtc.experiment import run_injection

OK, KO = "  OK", "  ÉCHEC"


# ---------------------------------------------------------------------------
# Proposition 1 — non-suffisance de l'ascendance
# ---------------------------------------------------------------------------

def check_p1() -> bool:
    print("=" * 72)
    print("PROPOSITION 1 — Non-suffisance de l'ascendance")
    print("=" * 72)
    print("\n  Une donnée sans preuve propre reste bornée par")
    print("      P_x ≤ (r_x + a_x·W) / (r_x + W)\n")

    scn = injection_resistance()
    m = DTCEngine(graph=scn.graph)
    for t, dio, ev in scn.timeline:
        m.add_evidence(dio, ev)

    a_x = scn.graph.nodes["fabricated"].base_rate
    evs = m.evidence["fabricated"]
    r_x = sum(e.mass_at(10.0) for e in evs if e.polarity == POSITIVE)
    s_x = sum(e.mass_at(10.0) for e in evs if e.polarity == NEGATIVE)
    p_measured = m.projected("fabricated", 10.0)
    p_bound = (r_x + a_x * W_PRIOR) / (r_x + W_PRIOR)

    gamma_max = max(p.gamma_p for p in RELATION_POLICIES.values())
    p_worst = (gamma_max + a_x * W_PRIOR) / (gamma_max + W_PRIOR)

    print(f"  confiance du parent          : {m.projected('trusted_source', 10.0):.3f}")
    print(f"  preuves locales de la donnée : {len(m.local_evidence_only('fabricated'))}")
    print(f"  masses (r, s)                : ({r_x:.4f}, {s_x:.4f})")
    print(f"  taux de base a_x             : {a_x:.2f}")
    print()
    print(f"  P mesuré                     : {p_measured:.4f}")
    print(f"  borne analytique             : {p_bound:.4f}")
    print(f"  pire cas (|ΔP|=1, un saut)   : {p_worst:.4f}")

    ok = p_measured <= p_bound + 1e-9 and p_measured <= p_worst + 1e-9
    print(f"\n{OK if ok else KO} : la borne est respectée.")

    tau = 0.5
    r_limit = W_PRIOR * (tau - a_x) / (1 - tau)
    print(f"\n  Seuil τ={tau} franchi seulement si r_x ≥ {r_limit:.2f}")
    print(f"  (r_x observé = {r_x:.4f}, soit {r_limit / max(r_x, 1e-9):.0f}× moins)")
    return ok


# ---------------------------------------------------------------------------
# Proposition 2 — terminaison sur graphe cyclique
# ---------------------------------------------------------------------------

def check_p2() -> bool:
    print("\n" + "=" * 72)
    print("PROPOSITION 2 — Terminaison sur graphe cyclique")
    print("=" * 72)
    print("\n  Graphes entièrement cycliques (cycle hamiltonien + arêtes aléatoires)\n")
    print(f"  {'n':>5}{'arêtes':>9}{'durée':>11}{'propagations':>15}{'prof. max':>11}")
    print("  " + "-" * 51)

    ok = True
    for n, extra in [(5, 3), (20, 15), (60, 50), (200, 180), (500, 400)]:
        g = DRG()
        for i in range(n):
            g.add_node(f"n{i}", base_rate=0.5)
        for i in range(n):
            g.add_edge(f"n{i}", f"n{(i + 1) % n}", "copy")
        rng = random.Random(0)
        for _ in range(extra):
            a, b = rng.randrange(n), rng.randrange(n)
            if a != b:
                g.add_edge(f"n{a}", f"n{b}", "derivation")

        m = DTCEngine(graph=g)
        for i in range(n):
            m.add_evidence(f"n{i}", make_evidence("creation_attested", POSITIVE, 1.0))

        t0 = time.time()
        m.add_evidence("n0", make_evidence("origin_compromise", NEGATIVE, 50.0))
        dt = (time.time() - t0) * 1000

        depths = [r.depth for r in m.audit]
        dmax = max(depths) if depths else 0
        if dmax > m.max_depth:
            ok = False
        print(f"  {n:>5}{len(g.edges):>9}{dt:>9.2f} ms{len(m.audit):>15}{dmax:>11}")

    print(f"\n{OK if ok else KO} : terminaison, profondeur ≤ δ_max = 4.")
    return ok


# ---------------------------------------------------------------------------
# Proposition 3 — découplage détection / injection
# ---------------------------------------------------------------------------

def check_p3() -> bool:
    print("\n" + "=" * 72)
    print("PROPOSITION 3 — Découplage détection / injection")
    print("=" * 72)
    print("\n  γ⁻ ne doit avoir AUCUN effet sur la confiance d'une donnée fabriquée.\n")
    print(f"  {'γ⁻ ×':>8}{'P fabriquée':>15}{'uplift':>10}")
    print("  " + "-" * 33)

    base = {k: (p.gamma_m, p.gamma_p) for k, p in RELATION_POLICIES.items()}
    values = []
    for scale in [1, 4, 16, 64, 256]:
        for k, (gm, gp) in base.items():
            old = RELATION_POLICIES[k]
            RELATION_POLICIES[k] = RelationPolicy(k, old.theta, gm * scale, gp)
        inj = run_injection(injection_resistance(), 10.0)["dtc"]
        values.append(inj["fabricated"])
        print(f"  {scale:>8}{inj['fabricated']:>15.4f}{inj['uplift']:>10.4f}")

    for k, (gm, gp) in base.items():
        RELATION_POLICIES[k] = RelationPolicy(k, RELATION_POLICIES[k].theta, gm, gp)

    ok = max(values) - min(values) < 1e-9
    print(f"\n{OK if ok else KO} : variation observée = {max(values) - min(values):.2e}")
    print("  γ⁻ multiplié par 256 : aucun effet mesurable sur l'injection.")
    return ok


# ---------------------------------------------------------------------------

def check_p4() -> bool:
    """Proposition 4 — résistance à la diffamation."""
    from dtc.scenarios import slander

    print("\n" + "=" * 72)
    print("PROPOSITION 4 — Résistance à la diffamation")
    print("=" * 72)
    print("\n  Un adversaire contrôle UNE source dont dérivent 30 données")
    print("  légitimes qu'il ne contrôle pas. Combien passe-t-il sous 0.45 ?\n")
    print(f"  {'impulsions':>11}{'accumulate':>13}{'standing':>11}{'masse prop.':>14}")
    print("  " + "-" * 49)

    ok = True
    masses = []
    for n in [1, 2, 4, 8, 16, 32]:
        row = {}
        for mode in ("accumulate", "standing"):
            scn = slander(n_pulses=n)
            m = DTCEngine(graph=scn.graph, propagation_mode=mode)
            for t, dio, ev in scn.timeline:
                m.add_evidence(dio, ev)
            te = 10.0 + 5.0 * n + 2.0
            vict = [m.projected(f"victim_{i}", te) for i in range(30)]
            row[mode] = sum(1 for p in vict if p < 0.45) / len(vict)
            if mode == "standing":
                ev_prop = [e for e in m.evidence["victim_0"]
                           if e.etype == "upstream_change"]
                masses.append(sum(e.mass_at(te) for e in ev_prop))
        if row["standing"] > 0.0:
            ok = False
        print(f"  {n:>11}{row['accumulate']:>12.0%}{row['standing']:>11.0%}"
              f"{masses[-1]:>14.4f}")

    # la masse ne doit pas croître avec le nombre d'événements
    bounded = max(masses) - min(masses) < 0.5
    print(f"\n  masse propagée : min {min(masses):.4f}, max {max(masses):.4f}")
    print(f"  bornée indépendamment de N : {'oui' if bounded else 'NON'}")
    print(f"\n{OK if ok and bounded else KO} : aucune victime bloquée, masse bornée.")
    return ok and bounded


def main() -> None:
    results = [check_p1(), check_p2(), check_p3(), check_p4()]
    print("\n" + "=" * 72)
    print(f"BILAN — {sum(results)}/{len(results)} propositions vérifiées empiriquement")
    print("=" * 72)
    print("\nRappel : ces vérifications ne remplacent pas les démonstrations")
    print("de PROPRIETES.md, elles les corroborent sur des instances concrètes.")


if __name__ == "__main__":
    main()
