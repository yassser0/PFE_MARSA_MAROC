"""
simulation/simulator.py
=======================
Moteur de simulation pour évaluer l'heuristique d'optimisation.

Ce module permet de :
1. Générer un flux intensif de N conteneurs
2. Placer chaque conteneur en utilisant l'optimiseur
3. Mesurer les KPIs critiques pour le PFE :
    - Nombre total de rehandles (coûts opérationnels)
    - Taux d'occupation du yard (utilisation de l'espace)
    - Hauteur moyenne des piles (stabilité)
    - Temps moyen de décision (performance)

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List

from data_generator.generator import generate_containers, generate_yard
from models.container import Container
from models.yard import Yard
from services.optimizer import find_best_slot
from services.scoring import score_breakdown


@dataclass
class SimulationResult:
    """Résultats et KPIs de la simulation."""
    containers_processed: int
    containers_placed: int
    total_rehandles_estimated: int
    occupancy_rate: float
    average_stack_height: float
    average_decision_time_ms: float
    failed_placements: int
    yard: Yard


def simulate(
    n_containers: int = 100,
    blocks: int = 4,
    rows: int = 10,
    max_height: int = 4,
) -> SimulationResult:
    """
    Exécute une simulation complète de remplissage du yard.

    Processus :
    1. Génère un yard vide
    2. Génère le flux de conteneurs
    3. Place chaque conteneur au meilleur slot évalué
    4. Enregistre les métriques
    5. Calcule les KPIs globaux

    Parameters
    ----------
    n_containers : nombre de conteneurs à simuler
    blocks       : configuration du yard (blocs)
    rows         : configuration du yard (rangées)
    max_height   : configuration du yard (hauteur max)

    Returns
    -------
    SimulationResult : l'objet contenant tous les KPIs
    """
    print(f"🔄 Initialisation de la simulation pour {n_containers} conteneurs...")
    yard: Yard = generate_yard(blocks=blocks, rows=rows, max_height=max_height)
    containers: List[Container] = generate_containers(n_containers)

    total_time_ms = 0.0
    total_rehandles = 0
    placed_count = 0
    failed_count = 0

    print("🚀 Début du placement itératif...")
    for i, container in enumerate(containers, 1):
        # Mesurer le temps de décision
        start_time = time.perf_counter()

        # Phase 1: Moteur d'optimisation
        best_result = find_best_slot(container, yard)

        end_time = time.perf_counter()
        decision_time_ms = (end_time - start_time) * 1000
        total_time_ms += decision_time_ms

        if best_result is None:
            failed_count += 1
            continue

        best_slot, _ = best_result

        # Extraire le nombre de rehandles estimés pour ce placement
        bd = score_breakdown(best_slot, container, yard)
        # La composante rehandle_score = poids(3) * rehandles
        # donc rehandles = rehandle_score / 3
        rehandles_pour_ce_slot = int(round(bd["rehandle_score"] / 3.0))
        total_rehandles += rehandles_pour_ce_slot

        # Phase 2: Exécuter le placement
        success = yard.place_container(best_slot, container)
        if success:
            placed_count += 1
        else:
            failed_count += 1

        # Affichage d'avancement tous les 10%
        if i % max(1, n_containers // 10) == 0:
            print(f"   ↳ {i}/{n_containers} conteneurs traités "
                  f"(Occupation : {yard.occupancy_rate:.1%})")

    avg_decision_time = total_time_ms / n_containers if n_containers > 0 else 0.0

    print("✅ Simulation terminée.")

    return SimulationResult(
        containers_processed=n_containers,
        containers_placed=placed_count,
        total_rehandles_estimated=total_rehandles,
        occupancy_rate=yard.occupancy_rate,
        average_stack_height=yard.average_stack_height,
        average_decision_time_ms=avg_decision_time,
        failed_placements=failed_count,
        yard=yard,
    )

