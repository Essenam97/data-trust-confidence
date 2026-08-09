"""
Data Relationship Graph et paramètres de politique de propagation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RelationPolicy:
    """Paramètres de propagation associés à un type de relation.

    theta   : seuil de déclenchement |ΔP| en dessous duquel rien n'est propagé
    gamma_m : facteur d'atténuation pour une DÉGRADATION amont (Δ < 0)
    gamma_p : facteur d'atténuation pour une AMÉLIORATION amont (Δ > 0)

    Choix de conception : gamma_m > gamma_p (asymétrie de précaution).
    Une mauvaise nouvelle se propage plus fort qu'une bonne.
    """

    name: str
    theta: float
    gamma_m: float
    gamma_p: float


# Barème calibré sur jeu de calibration disjoint (cf. validate.py).
# Facteur retenu : gamma_m = base × 48, avec plafonnement cap_ratio = 1.0.
#
# RÉSULTAT CENTRAL : gamma_p et gamma_m gouvernent deux propriétés DISJOINTES.
#
#   gamma_p (propagation positive) DOIT rester petit devant W_PRIOR = 2.0.
#       C'est la condition de non-suffisance (P1) : une donnée sans preuve
#       propre ne peut pas devenir fiable par simple ascendance.
#
#   gamma_m (propagation négative) PEUT être grand sans affecter P1.
#       Une mauvaise nouvelle qui se propage fort n'ouvre aucun vecteur
#       d'attaque : personne ne cherche à faire hériter de la défiance.
#
# L'asymétrie n'est donc pas une simple heuristique de précaution : c'est le
# mécanisme qui rend les deux objectifs simultanément atteignables.
RELATION_POLICIES: dict[str, RelationPolicy] = {
    "copy":           RelationPolicy("copy",           theta=0.05, gamma_m=43.2, gamma_p=0.30),
    "derivation":     RelationPolicy("derivation",     theta=0.05, gamma_m=33.6, gamma_p=0.20),
    "transformation": RelationPolicy("transformation", theta=0.05, gamma_m=28.8, gamma_p=0.18),
    "aggregation":    RelationPolicy("aggregation",    theta=0.08, gamma_m=19.2, gamma_p=0.10),
    "reference":      RelationPolicy("reference",      theta=0.10, gamma_m=12.0, gamma_p=0.05),
}


@dataclass
class Node:
    """Un DIO dans le graphe."""

    dio: str
    base_rate: float = 0.40
    label: str = ""
    # Vérité terrain pour l'évaluation expérimentale uniquement.
    # N'est JAMAIS lue par les moteurs de confiance.
    truly_affected: bool = False


@dataclass
class Edge:
    src: str          # donnée amont
    dst: str          # donnée aval
    rel: str          # type de relation

    @property
    def policy(self) -> RelationPolicy:
        return RELATION_POLICIES[self.rel]


@dataclass
class DRG:
    """Data Relationship Graph."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    # index d'adjacence (évite de rescanner toutes les arêtes à chaque appel)
    _succ: dict[str, list] = field(default_factory=dict, repr=False)
    _pred: dict[str, list] = field(default_factory=dict, repr=False)

    def add_node(self, dio: str, base_rate: float = 0.40, label: str = "",
                 truly_affected: bool = False) -> Node:
        n = Node(dio=dio, base_rate=base_rate, label=label,
                 truly_affected=truly_affected)
        self.nodes[dio] = n
        return n

    def add_edge(self, src: str, dst: str, rel: str) -> Edge:
        if src not in self.nodes or dst not in self.nodes:
            raise KeyError("noeud inconnu")
        if rel not in RELATION_POLICIES:
            raise KeyError(f"type de relation inconnu : {rel}")
        e = Edge(src=src, dst=dst, rel=rel)
        self.edges.append(e)
        self._succ.setdefault(src, []).append(e)
        self._pred.setdefault(dst, []).append(e)
        return e

    def successors(self, dio: str) -> list[Edge]:
        return self._succ.get(dio, [])

    def predecessors(self, dio: str) -> list[Edge]:
        return self._pred.get(dio, [])

    def __len__(self) -> int:
        return len(self.nodes)
