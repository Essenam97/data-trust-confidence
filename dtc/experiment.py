"""
Harnais expérimental : exécute un scénario sur les quatre modèles et calcule
les métriques comparatives.
"""

from __future__ import annotations

from dataclasses import dataclass

from .baselines import StaticTrust, DiscountingTrust, EigenTrustLike
from .engine import DTCEngine
from .scenarios import Scenario


@dataclass
class Result:
    model: str
    coverage: float          # rappel sur les données réellement affectées
    false_positive: float    # taux de fausse alerte
    mean_p_affected: float
    mean_p_clean: float
    separation: float        # écart moyen entre les deux populations


def build_models(scn: Scenario) -> dict:
    return {
        "static":      StaticTrust(graph=scn.graph),
        "discounting": DiscountingTrust(graph=scn.graph),
        "eigentrust":  EigenTrustLike(graph=scn.graph),
        "dtc":         DTCEngine(graph=scn.graph),
    }


def run(scn: Scenario, t_eval: float, threshold: float = 0.45) -> list[Result]:
    """Rejoue la timeline sur chaque modèle et mesure."""
    results: list[Result] = []

    for name, model in build_models(scn).items():
        for t, dio, ev in scn.timeline:
            model.add_evidence(dio, ev)

        affected, clean = [], []
        for dio, node in scn.graph.nodes.items():
            p = model.projected(dio, t_eval)
            (affected if node.truly_affected else clean).append(p)

        if not affected:
            results.append(Result(name, float("nan"), float("nan"),
                                  float("nan"), float("nan"), float("nan")))
            continue

        cov = sum(1 for p in affected if p < threshold) / len(affected)
        fp = (sum(1 for p in clean if p < threshold) / len(clean)) if clean else 0.0
        mpa = sum(affected) / len(affected)
        mpc = (sum(clean) / len(clean)) if clean else float("nan")

        results.append(Result(model=name, coverage=cov, false_positive=fp,
                              mean_p_affected=mpa, mean_p_clean=mpc,
                              separation=mpc - mpa))
    return results


def run_injection(scn: Scenario, t_eval: float) -> dict[str, dict[str, float]]:
    """Mesure la confiance accordée à une donnée fabriquée sans preuve propre."""
    out: dict[str, dict[str, float]] = {}
    for name, model in build_models(scn).items():
        for t, dio, ev in scn.timeline:
            model.add_evidence(dio, ev)
        out[name] = {
            "trusted_source": model.projected("trusted_source", t_eval),
            "fabricated": model.projected("fabricated", t_eval),
            "orphan": model.projected("orphan", t_eval),
        }
        out[name]["uplift"] = out[name]["fabricated"] - out[name]["orphan"]
    return out


def format_table(results: list[Result]) -> str:
    hdr = (f"{'modèle':<14}{'couverture':>12}{'faux pos.':>12}"
           f"{'P̄ affectées':>14}{'P̄ saines':>12}{'séparation':>12}")
    lines = [hdr, "-" * len(hdr)]
    for r in results:
        lines.append(f"{r.model:<14}{r.coverage:>11.1%}{r.false_positive:>12.1%}"
                     f"{r.mean_p_affected:>14.3f}{r.mean_p_clean:>12.3f}"
                     f"{r.separation:>12.3f}")
    return "\n".join(lines)
