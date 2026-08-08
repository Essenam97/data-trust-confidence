"""
Représentation de l'état de confiance.

Formalisme repris de la logique subjective (Jøsang). Ce module ne contient
aucune contribution originale : il est là pour être cité, pas revendiqué.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .evidence import Evidence, POSITIVE, NEGATIVE

# Poids d'ignorance a priori (distribution Beta non informative)
W_PRIOR = 2.0


@dataclass(frozen=True)
class Opinion:
    """Opinion (b, d, u, a) avec b + d + u = 1."""

    b: float
    d: float
    u: float
    a: float

    def __post_init__(self) -> None:
        s = self.b + self.d + self.u
        if abs(s - 1.0) > 1e-9:
            raise ValueError(f"additivité violée : b+d+u = {s}")

    @property
    def projected(self) -> float:
        """Probabilité projetée P = b + a·u, exploitable par le PIE."""
        return self.b + self.a * self.u

    def __repr__(self) -> str:
        return (f"Opinion(b={self.b:.3f}, d={self.d:.3f}, "
                f"u={self.u:.3f}, a={self.a:.2f}, P={self.projected:.3f})")


def masses(evidences: Iterable[Evidence], t: float,
           dedup: bool = True) -> tuple[float, float]:
    """Masses cumulées (r, s) de preuve positive et négative à l'instant t.

    Si dedup=True, les preuves partageant le même source_ref sont fusionnées
    en prenant le max plutôt que la somme, afin d'éviter le double comptage
    d'une même observation primaire rapportée par plusieurs systèmes.

    NOTE : cela traite la duplication exacte, PAS la corrélation partielle
    entre sources partageant une infrastructure commune. Limite assumée.
    """
    evidences = list(evidences)

    if dedup:
        by_ref: dict[str, Evidence] = {}
        standalone: list[Evidence] = []
        for e in evidences:
            if e.source_ref is None:
                standalone.append(e)
            else:
                key = f"{e.source_ref}|{e.polarity}"
                prev = by_ref.get(key)
                if prev is None or e.mass_at(t) > prev.mass_at(t):
                    by_ref[key] = e
        evidences = standalone + list(by_ref.values())

    r = sum(e.mass_at(t) for e in evidences if e.polarity == POSITIVE)
    s = sum(e.mass_at(t) for e in evidences if e.polarity == NEGATIVE)
    return r, s


def opinion_from_evidence(evidences: Iterable[Evidence], t: float,
                          base_rate: float, dedup: bool = True) -> Opinion:
    """Convertit un ensemble de preuves en opinion (mapping Beta standard)."""
    r, s = masses(evidences, t, dedup=dedup)
    denom = r + s + W_PRIOR
    return Opinion(b=r / denom, d=s / denom, u=W_PRIOR / denom, a=base_rate)


def discount(trust: Opinion, target: Opinion) -> Opinion:
    """Opérateur de discounting de la logique subjective.

    ω_A:B ⊗ ω_B:x — c'est le mécanisme d'HÉRITAGE de confiance utilisé comme
    baseline de comparaison. Il n'est PAS utilisé par le DTC.
    """
    p = trust.projected
    b = p * target.b
    d = p * target.d
    u = 1.0 - b - d
    return Opinion(b=b, d=d, u=u, a=target.a)
