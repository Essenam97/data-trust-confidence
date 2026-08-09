"""
Moteur Data Trust Confidence.

CONTRIBUTION CENTRALE : la propagation non transitive (§5).

Un changement de confiance amont ne modifie jamais l'opinion aval.
Il injecte une PREUVE bornée dans le flux d'évidence aval, laquelle est
ensuite fusionnée avec les preuves locales par le processus normal.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .evidence import Evidence, POSITIVE, NEGATIVE, make_evidence
from .graph import DRG
from .opinion import Opinion, opinion_from_evidence


@dataclass
class PropagationRecord:
    """Trace d'audit d'un événement de propagation."""
    t: float
    src: str
    dst: str
    rel: str
    delta: float
    weight: float
    depth: int


@dataclass
class DTCEngine:
    """Moteur d'évaluation dynamique de la confiance."""

    graph: DRG
    max_depth: int = 4
    dedup: bool = True

    # Atténuation par distance au foyer.
    #
    # Sans elle, gamma_m s'applique identiquement à chaque saut : une donnée
    # à trois sauts d'une source compromise est dégradée aussi fortement
    # qu'une copie directe. C'est la cause principale des faux positifs.
    #
    # Le poids injecté est multiplié par rho^depth (rho < 1), de sorte que
    # l'onde de défiance perd en intensité à mesure qu'elle s'éloigne.
    # rho = 1.0 restaure le comportement sans modulation.
    rho: float = 1.0

    # Plafonnement de la masse propagée, relatif à la masse de preuve LOCALE
    # déjà présente sur la donnée cible.
    #
    # Sans plafond, une propagation amplifiée (gamma_m eleve) écrase le signal
    # local : la variation de gamma_m selon le type de relation devient alors
    # la source dominante du classement, c'est-à-dire du bruit. Le plafond
    # borne la masse injectée à cap_ratio × (r + s + W) de la cible.
    #
    # cap_ratio = None désactive le plafonnement.
    cap_ratio: float | None = 1.0

    # Mode de tenue des preuves de propagation.
    #
    #   "accumulate" : une preuve est AJOUTÉE à chaque événement amont.
    #                  Vulnérable à la diffamation : un adversaire qui oscille
    #                  (dégrader / rétablir / dégrader) accumule une masse
    #                  négative non bornée sur les données aval.
    #
    #   "standing"   : une SEULE preuve est maintenue par arête, remplacée en
    #                  place. L'aval reflète l'ÉTAT courant de l'amont, non
    #                  l'historique de ses variations. La masse injectée est
    #                  alors bornée indépendamment du nombre d'événements.
    #
    # "standing" est le mode par défaut (cf. Proposition 4).
    propagation_mode: str = "standing"

    evidence: dict[str, list[Evidence]] = field(default_factory=lambda: defaultdict(list))
    audit: list[PropagationRecord] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    def opinion(self, dio: str, t: float) -> Opinion:
        node = self.graph.nodes[dio]
        return opinion_from_evidence(self.evidence[dio], t,
                                     base_rate=node.base_rate,
                                     dedup=self.dedup)

    def projected(self, dio: str, t: float) -> float:
        return self.opinion(dio, t).projected

    # ------------------------------------------------------------------
    # Écriture
    # ------------------------------------------------------------------

    def add_evidence(self, dio: str, ev: Evidence, propagate: bool = True) -> None:
        """Ajoute une preuve locale et déclenche éventuellement la propagation."""
        t = ev.timestamp
        before = self.projected(dio, t)
        self.evidence[dio].append(ev)
        after = self.projected(dio, t)

        if propagate:
            self._propagate(dio, before, after, t, depth=0, visited={dio})

    # ------------------------------------------------------------------
    # Propagation non transitive — coeur du modèle
    # ------------------------------------------------------------------

    def _propagate(self, src: str, p_before: float, p_after: float,
                   t: float, depth: int, visited: set[str]) -> None:
        """Convertit un changement amont en preuves locales aval bornées.

        Trois garde-fous garantissent la terminaison et la non-suffisance :
          - seuil theta : les micro-variations ne propagent pas
          - facteur gamma borné : le poids injecté reste petit devant W_PRIOR
          - max_depth + visited : terminaison sur graphe cyclique
        """
        delta = p_after - p_before
        if delta == 0.0 or depth >= self.max_depth:
            return

        for edge in self.graph.successors(src):
            dst = edge.dst
            if dst in visited:
                continue                      # anti-cycle

            pol = edge.policy
            if abs(delta) < pol.theta:
                continue                      # sous le seuil de déclenchement

            # Asymétrie de précaution : dégradation > amélioration.
            # Atténuation supplémentaire par distance au foyer (rho^depth).
            gamma = pol.gamma_m if delta < 0 else pol.gamma_p
            weight = gamma * abs(delta) * (self.rho ** depth)
            polarity = NEGATIVE if delta < 0 else POSITIVE

            if self.cap_ratio is not None:
                from .opinion import masses, W_PRIOR
                r_l, s_l = masses(self.evidence[dst], t, dedup=self.dedup)
                weight = min(weight, self.cap_ratio * (r_l + s_l + W_PRIOR))

            ev = Evidence(
                etype="upstream_change",
                polarity=polarity,
                weight=weight,
                timestamp=t,
                kappa=1.0,
                origin=src,
                depth=depth + 1,
            )

            before = self.projected(dst, t)

            if self.propagation_mode == "standing":
                # Une seule preuve de propagation par arête (src → dst) :
                # on remplace la précédente au lieu de l'accumuler.
                self.evidence[dst] = [
                    e for e in self.evidence[dst]
                    if not (e.etype == "upstream_change" and e.origin == src)
                ]
            self.evidence[dst].append(ev)
            after = self.projected(dst, t)

            self.audit.append(PropagationRecord(
                t=t, src=src, dst=dst, rel=edge.rel,
                delta=delta, weight=weight, depth=depth + 1))

            # Récursion : le changement AVAL peut à son tour propager,
            # mais chaque étape ré-atténue depuis la variation LOCALE réelle.
            self._propagate(dst, before, after, t,
                            depth=depth + 1, visited=visited | {dst})

    # ------------------------------------------------------------------
    # Introspection / audit
    # ------------------------------------------------------------------

    def explain(self, dio: str, t: float) -> dict:
        """Décomposition auditable d'une évaluation."""
        evs = self.evidence[dio]
        op = self.opinion(dio, t)
        contribs = sorted(
            ({"type": e.etype,
              "polarity": e.polarity,
              "mass": round(e.mass_at(t), 4),
              "origin": e.origin,
              "depth": e.depth} for e in evs),
            key=lambda c: -c["mass"])
        return {
            "dio": dio,
            "opinion": {"b": round(op.b, 4), "d": round(op.d, 4),
                        "u": round(op.u, 4), "a": op.a},
            "P": round(op.projected, 4),
            "n_evidence": len(evs),
            "top_contributions": contribs[:8],
        }

    def local_evidence_only(self, dio: str) -> list[Evidence]:
        """Preuves propres (hors propagation) — utile pour tester P1."""
        return [e for e in self.evidence[dio] if e.etype != "upstream_change"]
