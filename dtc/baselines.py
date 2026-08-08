"""
Modèles de comparaison.

Ces trois baselines consomment EXACTEMENT le même flux de preuves que le DTC.
La seule différence entre les modèles est la manière dont l'information de
confiance circule (ou non) le long du graphe de relations.

  - StaticTrust        : aucune circulation
  - DiscountingTrust   : héritage par l'opérateur de discounting (Jøsang)
  - EigenTrustLike     : héritage par point fixe global (Kamvar et al., adapté)

Note d'honnêteté : EigenTrust a été conçu pour des réseaux pair-à-pair, pas
pour des graphes de lignage de données. L'adaptation ci-dessous en conserve le
mécanisme central (propagation transitive jusqu'au point fixe) mais ne prétend
pas être une réimplémentation fidèle du papier original.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .evidence import Evidence
from .graph import DRG
from .opinion import Opinion, opinion_from_evidence, discount


@dataclass
class _BaseModel:
    graph: DRG
    evidence: dict[str, list[Evidence]] = field(
        default_factory=lambda: defaultdict(list))
    # Cache du calcul global, invalidé à chaque nouvelle preuve.
    # Sans lui, projected() recalcule tout le graphe pour CHAQUE noeud
    # interrogé, ce qui rend les baselines quadratiques.
    _cache: dict[float, dict[str, float]] = field(
        default_factory=dict, repr=False)

    def add_evidence(self, dio: str, ev: Evidence) -> None:
        self.evidence[dio].append(ev)
        self._cache.clear()

    def _all_cached(self, t: float) -> dict[str, float]:
        if t not in self._cache:
            self._cache[t] = self._all(t)
        return self._cache[t]

    def _local_opinion(self, dio: str, t: float) -> Opinion:
        node = self.graph.nodes[dio]
        return opinion_from_evidence(self.evidence[dio], t,
                                     base_rate=node.base_rate)


# ---------------------------------------------------------------------------


class StaticTrust(_BaseModel):
    """Confiance purement locale : aucune propagation.

    Représente la pratique courante des plateformes de gouvernance où le score
    d'une donnée ne dépend que de ses propres attributs.
    """

    name = "static"

    def projected(self, dio: str, t: float) -> float:
        return self._local_opinion(dio, t).projected


# ---------------------------------------------------------------------------


class DiscountingTrust(_BaseModel):
    """Héritage transitif par l'opérateur de discounting de la logique subjective.

    L'opinion d'une donnée est dérivée de celle de ses parents :
        ω_x = ⊕_parents  discount(ω_parent, ω_x_local)

    C'est le comportement que la Décision 12 de l'architecture rejette.
    """

    name = "discounting"

    def _topological_order(self) -> list[str]:
        indeg = {d: 0 for d in self.graph.nodes}
        for e in self.graph.edges:
            indeg[e.dst] += 1
        queue = [d for d, k in indeg.items() if k == 0]
        order: list[str] = []
        seen = set(queue)
        while queue:
            d = queue.pop(0)
            order.append(d)
            for e in self.graph.successors(d):
                indeg[e.dst] -= 1
                if indeg[e.dst] == 0 and e.dst not in seen:
                    queue.append(e.dst)
                    seen.add(e.dst)
        # noeuds restants (cycles) ajoutés en fin
        order += [d for d in self.graph.nodes if d not in seen]
        return order

    def projected(self, dio: str, t: float) -> float:
        return self._all_cached(t)[dio]

    def _all(self, t: float) -> dict[str, float]:
        op: dict[str, Opinion] = {}
        for d in self._topological_order():
            local = self._local_opinion(d, t)
            preds = self.graph.predecessors(d)
            if not preds:
                op[d] = local
                continue
            # moyenne des opinions héritées de chaque parent
            bs, ds_ = [], []
            for e in preds:
                parent = op.get(e.src, self._local_opinion(e.src, t))
                inherited = discount(parent, local)
                bs.append(inherited.b)
                ds_.append(inherited.d)
            b = sum(bs) / len(bs)
            dd = sum(ds_) / len(ds_)
            op[d] = Opinion(b=b, d=dd, u=1.0 - b - dd, a=local.a)
        return {d: o.projected for d, o in op.items()}


# ---------------------------------------------------------------------------


class EigenTrustLike(_BaseModel):
    """Propagation transitive globale par itération jusqu'au point fixe.

        t_x  =  (1-α) · Σ_{y→x} w_yx · t_y  +  α · local_x

    Les poids w sont normalisés sur les prédécesseurs. α est le poids accordé
    à la preuve locale face à la confiance héritée.
    """

    name = "eigentrust"
    alpha = 0.30
    iterations = 60

    def projected(self, dio: str, t: float) -> float:
        return self._all_cached(t)[dio]

    def _all(self, t: float) -> dict[str, float]:
        nodes = list(self.graph.nodes)
        local = {d: self._local_opinion(d, t).projected for d in nodes}
        trust = dict(local)

        for _ in range(self.iterations):
            new: dict[str, float] = {}
            for d in nodes:
                preds = self.graph.predecessors(d)
                if preds:
                    inherited = sum(trust[e.src] for e in preds) / len(preds)
                else:
                    inherited = local[d]
                new[d] = (1 - self.alpha) * inherited + self.alpha * local[d]
            if max(abs(new[d] - trust[d]) for d in nodes) < 1e-9:
                trust = new
                break
            trust = new
        return trust
