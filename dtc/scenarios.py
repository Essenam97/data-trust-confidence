"""
Scénarios expérimentaux reproductibles.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .evidence import POSITIVE, NEGATIVE, make_evidence, Evidence
from .graph import DRG


@dataclass
class Scenario:
    graph: DRG
    timeline: list[tuple[float, str, Evidence]]   # (t, dio, preuve)
    compromise_time: float
    description: str


# ---------------------------------------------------------------------------
# Scénario 1 — chaîne de lignage avec compromission d'origine
# ---------------------------------------------------------------------------

def lineage_compromise(seed: int = 0,
                       n_clean_roots: int = 6,
                       fanout: int = 3,
                       depth: int = 3) -> Scenario:
    """Écosystème de données avec un ERP compromis parmi plusieurs sources.

    Structure : plusieurs racines (systèmes sources), chacune se ramifiant en
    copies / transformations / agrégats. Une seule racine est compromise à
    t = T ; toute sa descendance est marquée `truly_affected` (vérité terrain).
    """
    rng = random.Random(seed)
    g = DRG()
    timeline: list[tuple[float, str, Evidence]] = []

    rels = ["copy", "derivation", "transformation", "aggregation", "reference"]

    # --- racines -----------------------------------------------------------
    roots = []
    for i in range(n_clean_roots + 1):
        compromised = (i == 0)
        dio = f"root_{i}"
        g.add_node(dio, base_rate=0.60, label="source system",
                   truly_affected=compromised)
        roots.append((dio, compromised))
        # preuves de création normales, identiques pour toutes les racines :
        # rien ne distingue a priori la racine compromise.
        timeline.append((1.0, dio, make_evidence("creation_attested", POSITIVE, 1.0)))
        timeline.append((2.0, dio, make_evidence("schema_validation", POSITIVE, 2.0)))
        timeline.append((3.0, dio, make_evidence("integrity_check_pass", POSITIVE, 3.0)))

    # --- descendance -------------------------------------------------------
    frontier = [(d, c) for d, c in roots]
    counter = 0
    t = 5.0
    for level in range(depth):
        new_frontier = []
        for parent, parent_comp in frontier:
            for _ in range(fanout):
                counter += 1
                dio = f"data_{level}_{counter}"
                g.add_node(dio, base_rate=0.45, label=f"level{level}",
                           truly_affected=parent_comp)
                rel = rng.choice(rels)
                g.add_edge(parent, dio, rel)

                # preuves locales ordinaires
                timeline.append((t, dio, make_evidence(
                    "transformation_traced", POSITIVE, t)))
                if rng.random() < 0.35:
                    timeline.append((t + 0.3, dio, make_evidence(
                        "schema_validation", POSITIVE, t + 0.3)))
                if rng.random() < 0.15:
                    timeline.append((t + 0.5, dio, make_evidence(
                        "transformation_opaque", NEGATIVE, t + 0.5)))
                t += 0.2
                new_frontier.append((dio, parent_comp))
        frontier = new_frontier

    # --- compromission révélée --------------------------------------------
    T = 50.0
    timeline.append((T, "root_0", make_evidence(
        "origin_compromise", NEGATIVE, T, source_ref="incident-001")))

    timeline.sort(key=lambda x: x[0])
    return Scenario(graph=g, timeline=timeline, compromise_time=T,
                    description="compromission d'une source parmi plusieurs")


# ---------------------------------------------------------------------------
# Scénario 2 — résistance à l'injection
# ---------------------------------------------------------------------------

def injection_resistance() -> Scenario:
    """Une donnée fabriquée depuis une source hautement fiable.

    `fabricated` est déclarée comme dérivée d'une source Co-Attestée et
    massivement validée, mais ne possède AUCUNE preuve propre.

    Question : le modèle lui accorde-t-il une confiance élevée du seul fait de
    son ascendance ? C'est exactement le vecteur d'attaque que la Décision 12
    de l'architecture cherche à fermer.
    """
    g = DRG()
    timeline: list[tuple[float, str, Evidence]] = []

    g.add_node("trusted_source", base_rate=0.80, label="source Co-Attestée")
    for k, (ty, pol, tt) in enumerate([
        ("co_attestation", POSITIVE, 1.0),
        ("creation_attested", POSITIVE, 1.5),
        ("human_validation", POSITIVE, 2.0),
        ("integrity_check_pass", POSITIVE, 2.5),
        ("schema_validation", POSITIVE, 3.0),
        ("integrity_check_pass", POSITIVE, 3.5),
        ("human_validation", POSITIVE, 4.0),
    ]):
        timeline.append((tt, "trusted_source", make_evidence(ty, pol, tt)))

    # La donnée fabriquée : aucune preuve locale, aucune validation.
    g.add_node("fabricated", base_rate=0.15, label="donnée fabriquée")
    g.add_edge("trusted_source", "fabricated", "derivation")

    # Témoin : même absence de preuve, mais sans parent fiable.
    g.add_node("orphan", base_rate=0.15, label="témoin sans ascendance")

    timeline.sort(key=lambda x: x[0])
    return Scenario(graph=g, timeline=timeline, compromise_time=float("inf"),
                    description="donnée fabriquée depuis une source fiable")


# ---------------------------------------------------------------------------
# Scénario 3 — compromission PARTIELLE
# ---------------------------------------------------------------------------

def partial_compromise(seed: int = 0, affected_fraction: float = 0.4) -> Scenario:
    """Seule une fraction des données issues de la source est réellement touchée.

    Scénario délibérément défavorable à toute forme de propagation : le graphe
    de lignage ne suffit plus à distinguer les données affectées des saines,
    puisque des voisines immédiates partagent la même ascendance sans être
    touchées. Mesure la robustesse aux faux positifs.
    """
    rng = random.Random(seed)
    g = DRG()
    timeline: list[tuple[float, str, Evidence]] = []
    rels = ["copy", "derivation", "transformation", "aggregation"]

    g.add_node("erp", base_rate=0.60, label="ERP partiellement compromis",
               truly_affected=True)
    for tt, ty in [(1.0, "creation_attested"), (2.0, "schema_validation")]:
        timeline.append((tt, "erp", make_evidence(ty, POSITIVE, tt)))

    t = 5.0
    for i in range(40):
        dio = f"rec_{i}"
        hit = rng.random() < affected_fraction
        g.add_node(dio, base_rate=0.45, truly_affected=hit)
        g.add_edge("erp", dio, rng.choice(rels))
        timeline.append((t, dio, make_evidence("transformation_traced", POSITIVE, t)))
        # Les données réellement touchées portent un signal local faible.
        if hit and rng.random() < 0.5:
            timeline.append((t + 0.1, dio, make_evidence(
                "integrity_check_fail", NEGATIVE, t + 0.1)))
        t += 0.2

    T = 50.0
    timeline.append((T, "erp", make_evidence(
        "origin_compromise", NEGATIVE, T, source_ref="incident-partial")))
    timeline.sort(key=lambda x: x[0])
    return Scenario(graph=g, timeline=timeline, compromise_time=T,
                    description="compromission partielle d'une source")


# ---------------------------------------------------------------------------
# Scénario 4 — compromission révélée TARDIVEMENT
# ---------------------------------------------------------------------------

def late_revelation(delay: float = 400.0) -> Scenario:
    """Une compromission ancienne, révélée très longtemps après les faits.

    Teste la décision de conception lam = 0 pour `origin_compromise` :
    une preuve de compromission ne doit PAS s'affaiblir avec le temps, sans
    quoi il suffirait d'attendre l'expiration de la mauvaise réputation.
    """
    g = DRG()
    timeline: list[tuple[float, str, Evidence]] = []

    g.add_node("src", base_rate=0.60, truly_affected=True)
    g.add_node("child", base_rate=0.45, truly_affected=True)
    g.add_edge("src", "child", "copy")

    for tt, ty in [(1.0, "creation_attested"), (2.0, "schema_validation"),
                   (3.0, "integrity_check_pass")]:
        timeline.append((tt, "src", make_evidence(ty, POSITIVE, tt)))
    timeline.append((5.0, "child", make_evidence("transformation_traced", POSITIVE, 5.0)))

    timeline.append((delay, "src", make_evidence(
        "origin_compromise", NEGATIVE, delay, source_ref="incident-late")))
    timeline.sort(key=lambda x: x[0])
    return Scenario(graph=g, timeline=timeline, compromise_time=delay,
                    description=f"compromission révélée à t={delay}")
