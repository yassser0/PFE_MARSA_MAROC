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
from typing import Dict, List, Optional, Tuple

from models.container import Container
from models.yard import Slot, Stack, Yard
from services.scoring import calculate_score

# Seuil au-delà duquel un emplacement n'est pas considéré optimal
OPTIMALITY_THRESHOLD: float = 1.0


# --- Configuration de la Politique de Taille ---
# Blocs A, B : 20ft uniquement
# Blocs C, D : 40ft uniquement
SIZE_POLICY = {
    20: ['A', 'B'],
    40: ['C', 'D']
}

def get_valid_slots(
    container: Container,
    yard: Yard,
    allowed_blocks: Optional[List[str]] = None,
    strict_edd: bool = True,
    strict_weight: bool = True,
) -> List[Slot]:
    """
    Retourne la liste des slots physiquement valides pour ce conteneur.
    Enforce la séparation stricte des 20ft et 40ft par blocs.
    """
    valid_slots: List[Slot] = []

    # Si allowed_blocks n'est pas fourni, on utilise la politique par défaut
    if not allowed_blocks:
        allowed_blocks = SIZE_POLICY.get(container.size, [])

    for block_id, block in yard.blocks.items():
        # Filtre de zone (SÉPARATION 20ft/40ft)
        if allowed_blocks and block_id not in allowed_blocks:
            continue
            
        for b in range(1, block.n_bays + 1):
            for r in range(1, block.n_rows + 1):
                stack = block.stacks.get((b, r))
                if stack is None:
                    continue

                next_slot = stack.top_free_slot
                if next_slot is None:
                    continue  # pile pleine

                if next_slot.tier != stack.current_height + 1:
                    continue

                # --- Règle d'homogénéité de taille ---
                if stack.current_height > 0:
                    existing_sizes = stack.get_container_sizes(yard.containers_registry)
                    if existing_sizes and container.size not in existing_sizes:
                        continue 

                # --- Règle EDD ---
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
                        continue 

                # --- Règle de Stabilité ---
                if strict_weight and next_slot.tier > 1:
                    below_slot = stack.slots[next_slot.tier - 2]
                    if below_slot.container_id:
                        below_container = yard.containers_registry.get(below_slot.container_id)
                        if below_container and container.weight > below_container.weight:
                            continue 

                valid_slots.append(next_slot)

    return valid_slots


# ---------------------------------------------------------------------------
# Recherche du meilleur slot (Simulated Annealing)
# ---------------------------------------------------------------------------

def simulated_annealing_optimization(
    container: Container,
    yard: Yard,
    valid_slots: List[Slot],
    precomputed_scores: Optional[Dict[str, float]] = None,
    initial_temp: float = 100.0,
    cooling_rate: float = 0.90,
    min_temp: float = 0.1,
    max_iter_per_temp: int = 20
) -> Tuple[Slot, float]:
    """
    Métaheuristique : Algorithme de Recuit Simulé (Simulated Annealing)
    """
    def get_cost(slot: Slot) -> float:
        if precomputed_scores is not None and slot.localization in precomputed_scores:
            return precomputed_scores[slot.localization]
        return calculate_score(slot, container, yard)

    # 1. État initial (placement aléatoire)
    current_slot = random.choice(valid_slots)
    try:
        current_cost = get_cost(current_slot)
    except ValueError:
        current_cost = float('inf')
        
    best_slot = current_slot
    best_cost = current_cost
    
    temp = initial_temp
    
    while temp > min_temp:
        for _ in range(max_iter_per_temp):
            # 3. Génération d'une solution voisine en choisissant une nouvelle pile valide
            neighbor_slot = random.choice(valid_slots)
            
            if neighbor_slot.localization == current_slot.localization:
                continue
                
            try:
                # 2. Fonction de coût pénalisant le rehandling, la distance, etc.
                neighbor_cost = get_cost(neighbor_slot)
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
    # --- Passe 1 : EDD strict, (Poids négligé selon demande de l'utilisateur) ---
    valid_slots = get_valid_slots(
        container, yard, allowed_blocks, strict_edd=True, strict_weight=False
    )

    if not valid_slots:
        # --- Passe 2 : Dégradé (si aucun slot optimal trouvé) ---
        # On relaxe d'abord l'EDD mais on garde si possible la stabilité
        valid_slots = get_valid_slots(
            container, yard, allowed_blocks, strict_edd=False, strict_weight=True
        )
        
        if not valid_slots:
            # Passe 3 : Désespoir (tout slot physique libre, même instable)
            # La stabilité sera gérée par la pénalité de 50.0 dans le scorer.
            valid_slots = get_valid_slots(
                container, yard, allowed_blocks, strict_edd=False, strict_weight=False
            )
            
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
    precomputed = {slot.localization: score for score, slot in scored_slots}

    # 2. Application de l'approche métaheuristique (SA) sur les candidats filtrés.
    return simulated_annealing_optimization(container, yard, top_candidates, precomputed_scores=precomputed)


