"""
services/optimizer.py
=====================
Moteur d'optimisation pour le placement des conteneurs dans le yard.

Ce module implémente une approche par Recuit Simulé (Simulated Annealing) pour 
trouver l'emplacement optimal d'un conteneur entrant.

L'algorithme :
1. Représente l'état du yard par l'assignation d'un slot.
2. Utilise la fonction de coût (scoring) qui pénalise :
   - Les risques de remutention (rehandling).
   - Les longues distances.
   - Les déséquilibres de piles (stack imbalance).
3. Génère des solutions voisines en déplaçant le conteneur évalué vers 
   d'autres piles disponibles.
4. Améliore itérativement la solution selon le refroidissement simulé.

Auteur  : PFE Marsa Maroc
Version : 2.0 (Metaheuristic Optimization)
"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from models.container import Container
from models.yard import Slot, Stack, Yard
from services.scoring import calculate_score, score_breakdown

# Seuil au-delà duquel un emplacement n'est pas considéré optimal
OPTIMALITY_THRESHOLD: float = 1.0


# ---------------------------------------------------------------------------
# Filtrage des slots valides
# ---------------------------------------------------------------------------

def get_valid_slots(
    container: Container,
    yard: Yard,
    allowed_blocks: Optional[List[str]] = None,
    strict_edd: bool = True,
) -> List[Slot]:
    """
    Retourne la liste des slots physiquement valides pour ce conteneur.

    Parameters
    ----------
    strict_edd : bool
        Si True (défaut), applique la règle EDD stricte : refuse tout slot
        où le conteneur entrant partirait APRÈS un conteneur déjà en dessous.
        Si False, désactive ce filtre et laisse le scorer pénaliser les rehandles.
    """
    valid_slots: List[Slot] = []

    # --- Dedicated Zones Logic ---
    # Example policy: Blocks A and B are for 20ft only.
    #                 Blocks C and D are for 40ft only.
    if allowed_blocks is None:
        allowed_blocks = []
        if container.size == 20:
            allowed_blocks = ['A', 'B']  # Adjust based on your actual block IDs if they differ
        elif container.size == 40:
            allowed_blocks = ['C', 'D']

    for block_id, block in yard.blocks.items():
        # Only check blocks dedicated to this container size
        if allowed_blocks and block_id not in allowed_blocks:
            continue
            
        for stack in block.stacks.values():

            next_slot = stack.top_free_slot
            if next_slot is None:
                continue  # pile pleine

            if next_slot.tier != stack.current_height + 1:
                continue

            # --- Règle d'homogénéité de taille ---
            # Une pile ne doit contenir que des conteneurs de la même taille.
            # Si la pile n'est pas vide, vérifier que la taille correspond.
            if stack.current_height > 0:
                existing_sizes = stack.get_container_sizes(yard.containers_registry)
                if existing_sizes and container.size not in existing_sizes:
                    continue  # La pile contient déjà une autre taille

            # Règle spécifique 40ft
            if container.size == 40:
                adjacent_row = stack.row + 1
                if adjacent_row > yard.n_rows:
                    continue
                adjacent_stack = block.stacks.get(adjacent_row)
                if adjacent_stack is None or adjacent_stack.is_full:
                    continue
                if adjacent_stack.current_height != stack.current_height:
                    continue

            # --- Règle EDD (Earliest Departure Date) ---
            # Appliquée uniquement en mode strict pour éviter les rehandles.
            # En mode dégradé (strict_edd=False), le scorer pénalise à la place.
            if strict_edd:
                edd_violation = False
                for below_slot in stack.slots:
                    if below_slot.tier >= next_slot.tier:
                        break
                    if not below_slot.container_id:
                        continue
                    below_container = yard.containers_registry.get(below_slot.container_id)
                    if below_container and container.departure_time > below_container.departure_time:
                        edd_violation = True
                        break
                if edd_violation:
                    continue  # Rejeté en mode strict

            valid_slots.append(next_slot)

    return valid_slots


# ---------------------------------------------------------------------------
# Recherche du meilleur slot (Simulated Annealing)
# ---------------------------------------------------------------------------

def simulated_annealing_optimization(
    container: Container,
    yard: Yard,
    valid_slots: List[Slot],
    initial_temp: float = 100.0,
    cooling_rate: float = 0.90,
    min_temp: float = 0.1,
    max_iter_per_temp: int = 20
) -> Tuple[Slot, float]:
    """
    Métaheuristique : Algorithme de Recuit Simulé (Simulated Annealing)
    """
    # 1. État initial (placement aléatoire)
    current_slot = random.choice(valid_slots)
    try:
        current_cost = calculate_score(current_slot, container, yard)
    except ValueError:
        current_cost = float('inf')
        
    best_slot = current_slot
    best_cost = current_cost
    
    temp = initial_temp
    
    while temp > min_temp:
        for _ in range(max_iter_per_temp):
            # 3. Génération d'une solution voisine en choisissant une nouvelle pile valide
            neighbor_slot = random.choice(valid_slots)
            
            if neighbor_slot.position_key == current_slot.position_key:
                continue
                
            try:
                # 2. Fonction de coût pénalisant le rehandling, la distance, etc.
                neighbor_cost = calculate_score(neighbor_slot, container, yard)
            except ValueError:
                continue
                
            cost_diff = neighbor_cost - current_cost
            
            # Paramètres et critères d'acceptation 
            if cost_diff < 0:
                # 4. Amélioration itérative : La solution est meilleure, on l'accepte toujours.
                current_slot = neighbor_slot
                current_cost = neighbor_cost
                
                # Mise à jour de la meilleure solution globale trouvée
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_slot = current_slot
            else:
                # La solution est pire, mais on peut l'accepter probabilistement
                probability = math.exp(-cost_diff / temp)
                if random.random() < probability:
                    current_slot = neighbor_slot
                    current_cost = neighbor_cost
                    
        # Refroidissement du système
        temp *= cooling_rate
        
    return best_slot, best_cost


def find_best_slot(
    container: Container,
    yard: Yard,
    top_k: int = 10,
    allowed_blocks: Optional[List[str]] = None
) -> Optional[Tuple[Slot, float]]:
    """
    Trouve le slot optimal via une approche Hybride à 2 passes :

    Passe 1 — EDD strict :
        Ne considère que les slots sans rehandle (conteneur entrant repart
        avant tous ceux déjà en dessous). Priorité absolue.

    Passe 2 — Dégradé (si aucun slot EDD trouvé) :
        Active tous les slots physiquement disponibles et laisse le scorer
        pénaliser les rehandles — évite les faux « yard plein ».

    Dans les deux cas : Filtrage Top-K (Greedy) + Recuit Simulé (SA).
    """
    # --- Passe 1 : EDD strict ---
    valid_slots = get_valid_slots(container, yard, allowed_blocks, strict_edd=True)

    if not valid_slots:
        # --- Passe 2 : EDD relaxé (fallback) ---
        valid_slots = get_valid_slots(container, yard, allowed_blocks, strict_edd=False)
        if not valid_slots:
            return None  # Yard vraiment plein (physiquement)

    if len(valid_slots) == 1:
        try:
            return valid_slots[0], calculate_score(valid_slots[0], container, yard)
        except ValueError:
            return None

    # 1. Évaluation Heuristique Rapide (Greedy)
    scored_slots = []
    for slot in valid_slots:
        try:
            score = calculate_score(slot, container, yard)
            scored_slots.append((score, slot))
        except ValueError:
            continue
            
    if not scored_slots:
        return None
        
    # Tri par score croissant (faible score = meilleur) et sélection des K meilleurs
    scored_slots.sort(key=lambda x: x[0])
    top_candidates = [slot for score, slot in scored_slots[:top_k]]

    # 2. Application de l'approche métaheuristique (SA) sur les candidats filtrés.
    return simulated_annealing_optimization(container, yard, top_candidates)


# ---------------------------------------------------------------------------
# Évaluation de l'optimalité d'un placement proposé
# ---------------------------------------------------------------------------

def is_placement_optimal(
    proposed_slot: Slot,
    container: Container,
    yard: Yard,
    threshold: float = OPTIMALITY_THRESHOLD,
    allowed_blocks: Optional[List[str]] = None
) -> Tuple[bool, str, float]:
    """
    Évalue si un emplacement proposé est proche de l'optimisation maximale trouvée.
    """
    valid_slots = get_valid_slots(container, yard, allowed_blocks)
    valid_keys = {s.position_key for s in valid_slots}

    if proposed_slot.position_key not in valid_keys:
        return False, "Le slot proposé n'est pas valide (plein, inaccessible ou incompatible).", float('inf')

    try:
        proposed_score = calculate_score(proposed_slot, container, yard)
    except ValueError:
        return False, "Placement physiquement impossible (poids instable).", float('inf')

    # Exécuter l'heuristique pour trouver le "meilleur" score estimé
    best_result = find_best_slot(container, yard, allowed_blocks=allowed_blocks)
    if best_result is None:
        return False, "Aucun slot disponible dans le yard.", float('inf')

    best_slot, best_score = best_result
    score_gap = proposed_score - best_score

    if score_gap <= threshold:
        reason = (
            f"Placement optimal ✓ — Score: {proposed_score:.2f} "
            f"(meilleur trouvé par SA: {best_score:.2f}, écart: {score_gap:.2f})"
        )
        return True, reason, score_gap
    else:
        reason = (
            f"Placement sous-optimal — Score: {proposed_score:.2f} "
            f"(meilleur trouvé: {best_score:.2f} en {best_slot.position_key}, "
            f"écart: {score_gap:.2f} > seuil {threshold})"
        )
        return False, reason, score_gap


# ---------------------------------------------------------------------------
# Rapport complet d'un placement
# ---------------------------------------------------------------------------

def placement_report(
    container: Container,
    yard: Yard,
    proposed_slot: Optional[Slot] = None,
    allowed_blocks: Optional[List[str]] = None
) -> dict:
    """
    Génère un rapport de l'assignation du nouveau conteneur.
    """
    best_result = find_best_slot(container, yard, allowed_blocks=allowed_blocks)
    valid_slots = get_valid_slots(container, yard, allowed_blocks=allowed_blocks)

    report = {
        "container_id": container.id,
        "container_size": container.size,
        "container_type": container.type.value,
        "yard_occupancy": f"{yard.occupancy_rate:.1%}",
        "available_slots_count": len(valid_slots),
    }

    if best_result:
        best_slot, best_score = best_result
        report["best_slot"] = {
            "block": best_slot.block_id,
            "row": best_slot.row,
            "tier": best_slot.tier,
            "position_key": best_slot.position_key,
        }
        report["best_score"] = best_score
        report["score_breakdown"] = score_breakdown(best_slot, container, yard)
    else:
        report["best_slot"] = None
        report["best_score"] = None
        report["score_breakdown"] = None
        report["error"] = "Aucun slot disponible dans le yard."

    if proposed_slot is not None:
        is_opt, reason, gap = is_placement_optimal(proposed_slot, container, yard, allowed_blocks=allowed_blocks)
        report["proposed_evaluation"] = {
            "slot": proposed_slot.position_key,
            "is_optimal": is_opt,
            "reason": reason,
            "score_gap": gap if not math.isinf(gap) else None,
        }

    return report
