"""
Data Trust Confidence — implémentation de référence.

Modèle d'évaluation dynamique de la confiance des données avec propagation
non transitive sur un graphe de lignage.

Modules :
    evidence    modèle de preuve, types, décroissance temporelle typée
    opinion     opinion (b,d,u,a), mapping Beta, opérateur de discounting
    graph       graphe de relations et paramètres de politique
    engine      moteur DTC — propagation non transitive
    baselines   modèles de comparaison
    scenarios   générateurs de scénarios reproductibles
    experiment  harnais et métriques
"""

__version__ = "1.0.0"
