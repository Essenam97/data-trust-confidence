"""
Modèle de preuve du Data Trust Confidence.

Une preuve est une observation datée, typée et signée, produite par un capteur
externe au DTC. Le DTC ne détecte rien : il agrège.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# --------------------------------------------------------------------------
# Types de preuve et paramètres de décroissance
# --------------------------------------------------------------------------

POSITIVE = +1
NEGATIVE = -1


@dataclass(frozen=True)
class EvidenceType:
    """Configuration d'un type de preuve.

    lam : taux de décroissance temporelle (par unité de temps).
          lam = 0.0 signifie que la preuve ne se périme JAMAIS.
    """

    name: str
    lam: float
    default_weight: float = 1.0


# Barème de référence. Les valeurs sont des paramètres de politique de
# gouvernance : elles doivent être publiées avec tout résultat expérimental.
EVIDENCE_TYPES: dict[str, EvidenceType] = {
    # --- preuves positives -------------------------------------------------
    "creation_attested":     EvidenceType("creation_attested",     lam=0.001, default_weight=2.0),
    "co_attestation":        EvidenceType("co_attestation",        lam=0.001, default_weight=4.0),
    "schema_validation":     EvidenceType("schema_validation",     lam=0.020, default_weight=1.0),
    "human_validation":      EvidenceType("human_validation",      lam=0.005, default_weight=3.0),
    "integrity_check_pass":  EvidenceType("integrity_check_pass",  lam=0.050, default_weight=1.5),
    "transformation_traced": EvidenceType("transformation_traced", lam=0.010, default_weight=1.0),
    # --- preuves négatives -------------------------------------------------
    "transformation_opaque": EvidenceType("transformation_opaque", lam=0.010, default_weight=1.5),
    "integrity_check_fail":  EvidenceType("integrity_check_fail",  lam=0.050, default_weight=3.0),
    "policy_violation":      EvidenceType("policy_violation",      lam=0.005, default_weight=3.0),
    # Décision de sécurité forte : une compromission avérée ne s'efface pas
    # par simple écoulement du temps. Seule une remédiation attestée peut la
    # contrebalancer.
    "origin_compromise":     EvidenceType("origin_compromise",     lam=0.000, default_weight=8.0),
    # --- preuve de propagation (cf. mécanisme non transitif) ---------------
    "upstream_change":       EvidenceType("upstream_change",       lam=0.020, default_weight=1.0),
}


@dataclass
class Evidence:
    """Un élément de preuve attaché à un DIO."""

    etype: str
    polarity: int              # POSITIVE ou NEGATIVE
    weight: float              # poids brut
    timestamp: float
    kappa: float = 1.0         # crédibilité de la source [0,1]

    # Traçabilité / audit
    source_ref: Optional[str] = None   # identifiant d'observation primaire
    origin: Optional[str] = None       # DIO amont, si preuve de propagation
    depth: int = 0                     # profondeur de propagation

    def __post_init__(self) -> None:
        if self.etype not in EVIDENCE_TYPES:
            raise ValueError(f"type de preuve inconnu : {self.etype}")
        if self.polarity not in (POSITIVE, NEGATIVE):
            raise ValueError("polarité invalide")
        if not 0.0 <= self.kappa <= 1.0:
            raise ValueError("kappa doit être dans [0,1]")
        if self.weight < 0:
            raise ValueError("poids négatif")

    @property
    def lam(self) -> float:
        return EVIDENCE_TYPES[self.etype].lam

    def mass_at(self, t: float) -> float:
        """Masse de preuve effective à l'instant t, après décroissance."""
        dt = max(0.0, t - self.timestamp)
        import math
        return self.weight * self.kappa * math.exp(-self.lam * dt)


def make_evidence(etype: str, polarity: int, timestamp: float,
                  weight: Optional[float] = None, **kw) -> Evidence:
    """Fabrique une preuve avec le poids par défaut de son type."""
    w = EVIDENCE_TYPES[etype].default_weight if weight is None else weight
    return Evidence(etype=etype, polarity=polarity, weight=w,
                    timestamp=timestamp, **kw)
