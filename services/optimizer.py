"""
services/optimizer.py
=====================
Moteur d'optimisation pour le placement des conteneurs dans le yard.

Ce module implémente l'heuristique de placement qui :
1. Filtre les slots physiquement valides
2. Calcule un score pour chaque slot valide
3. Retourne le meilleur slot (score minimum)
4. Évalue si un placement proposé est optimal

Heuristique utilisée : Greedy Best-First (glouton optimisé)
→ Garantit un bon placement en temps constant, adapté aux flux temps-réel.

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from models.container import Container
from models.yard import Slot, Stack, Yard
from services.scoring import calculate_score, score_breakdown

# Seuil au-delà duquel un emplacement n'est pas considéré optimal
# (différence de score entre le slot proposé et le meilleur slot)
OPTIMALITY_THRESHOLD: float = 1.0


# ---------------------------------------------------------------------------
# Filtrage des slots valides
# ---------------------------------------------------------------------------

def get_valid_slots(container: Container, yard: Yard) -> List[Slot]:
    """
    Retourne la liste des slots physiquement valides pour ce conteneur.

    Règles de validité :
    1. Le slot doit être libre
    2. Le slot doit être le prochain disponible dans sa pile (pas de "trou")
       → On ne peut poser un conteneur qu'au sommet de la pile
    3. Pour un conteneur 40ft, deux rangées adjacentes suffisantes
       (la vérification est simplifiée ici — on traite le 40ft comme un
       slot simple pour la démonstration, mais on note cette contrainte)
    4. Le slot doit être au niveau accessible (tier = current_height + 1)

    Parameters
    ----------
    container : Container
        Conteneur à placer
    yard : Yard
        État actuel du yard

    Returns
    -------
    List[Slot]
        Liste des slots utilisables pour ce conteneur
    """
    valid_slots: List[Slot] = []

    for block in yard.blocks.values():
        for stack in block.stacks.values():

            # Règle : on ne pose qu'au sommet de la pile
            next_slot = stack.top_free_slot
            if next_slot is None:
                continue  # pile pleine

            # Règle : le tier doit correspondre exactement à current_height + 1
            # (pas de "flottement" dans la pile)
            if next_slot.tier != stack.current_height + 1:
                continue

            # Règle spécifique 40ft : vérifier la rangée adjacente
            if container.size == 40:
                adjacent_row = stack.row + 1
                if adjacent_row > yard.n_rows:
                    continue  # pas de place pour un 40ft en bout de bloc
                adjacent_stack = block.stacks.get(adjacent_row)
                if adjacent_stack is None or adjacent_stack.is_full:
                    continue
                # La rangée adjacente doit être à la même hauteur
                if adjacent_stack.current_height != stack.current_height:
                    continue  # hauteurs différentes → instable

            valid_slots.append(next_slot)

    return valid_slots


# ---------------------------------------------------------------------------
# Recherche du meilleur slot
# ---------------------------------------------------------------------------

def find_best_slot(
    container: Container,
    yard: Yard,
) -> Optional[Tuple[Slot, float]]:
    """
    Trouve le slot optimal pour placer le conteneur dans le yard.

    Algorithme (Greedy Best-First) :
    1. Obtenir tous les slots valides
    2. Calculer le score de chaque slot
    3. Retourner le slot avec le score minimum

    Parameters
    ----------
    container : Container
        Conteneur à placer
    yard : Yard
        État actuel du yard

    Returns
    -------
    Optional[Tuple[Slot, float]]
        (meilleur_slot, score) ou None si aucun slot disponible

    Example
    -------
    >>> result = find_best_slot(container, yard)
    >>> if result:
    ...     best_slot, score = result
    ...     yard.place_container(best_slot, container.id)
    """
    valid_slots = get_valid_slots(container, yard)

    if not valid_slots:
        return None  # yard plein ou aucun slot compatible

    # Calculer le score de chaque slot et garder le minimum
    best_slot: Optional[Slot] = None
    best_score: float = math.inf

    for slot in valid_slots:
        try:
            score = calculate_score(slot, container, yard)
            if score < best_score:
                best_score = score
                best_slot = slot
        except ValueError:
            continue  # slot invalide, on l'ignore

    if best_slot is None:
        return None

    return best_slot, best_score


# ---------------------------------------------------------------------------
# Évaluation de l'optimalité d'un placement proposé
# ---------------------------------------------------------------------------

def is_placement_optimal(
    proposed_slot: Slot,
    container: Container,
    yard: Yard,
    threshold: float = OPTIMALITY_THRESHOLD,
) -> Tuple[bool, str, float]:
    """
    Évalue si un emplacement proposé est optimal pour ce conteneur.

    Compare le score du slot proposé avec le meilleur slot disponible.
    Si la différence de score est inférieure au seuil, le placement est
    considéré optimal.

    Parameters
    ----------
    proposed_slot : Slot
        Emplacement proposé à évaluer
    container     : Container
        Conteneur à placer
    yard          : Yard
        État actuel du yard
    threshold     : float
        Écart de score toléré pour considérer le placement optimal (default: 1.0)

    Returns
    -------
    Tuple[bool, str, float]
        (is_optimal, reason, score_gap)
        - is_optimal : True si l'emplacement est optimal
        - reason     : explication lisible de la décision
        - score_gap  : différence de score avec le slot optimal

    Example
    -------
    >>> ok, reason, gap = is_placement_optimal(slot, container, yard)
    >>> print(f"Optimal: {ok} — {reason}")
    """
    # Vérifier que le slot proposé est valide
    valid_slots = get_valid_slots(container, yard)
    valid_keys = {s.position_key for s in valid_slots}

    if proposed_slot.position_key not in valid_keys:
        return False, "Le slot proposé n'est pas valide (plein, inaccessible ou incompatible).", math.inf

    # Score du slot proposé
    proposed_score = calculate_score(proposed_slot, container, yard)

    # Meilleur slot disponible
    best_result = find_best_slot(container, yard)
    if best_result is None:
        return False, "Aucun slot disponible dans le yard.", math.inf

    best_slot, best_score = best_result
    score_gap = proposed_score - best_score

    if score_gap <= threshold:
        reason = (
            f"Placement optimal ✓ — Score: {proposed_score:.2f} "
            f"(meilleur possible: {best_score:.2f}, écart: {score_gap:.2f})"
        )
        return True, reason, score_gap
    else:
        reason = (
            f"Placement sous-optimal — Score: {proposed_score:.2f} "
            f"(meilleur disponible: {best_score:.2f} en {best_slot.position_key}, "
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
) -> dict:
    """
    Génère un rapport complet sur le placement optimal d'un conteneur.

    Parameters
    ----------
    container     : conteneur à placer
    yard          : état actuel du yard
    proposed_slot : slot proposé (optionnel) pour évaluation comparative

    Returns
    -------
    dict avec les champs :
        - container_id
        - best_slot : coordonnées du meilleur slot
        - best_score : score du meilleur slot
        - score_breakdown : détail du score
        - proposed_evaluation : évaluation du slot proposé (si fourni)
        - yard_occupancy : taux d'occupation actuel
        - available_slots_count : nombre de slots valides
    """
    best_result = find_best_slot(container, yard)
    valid_slots = get_valid_slots(container, yard)

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
        is_opt, reason, gap = is_placement_optimal(proposed_slot, container, yard)
        report["proposed_evaluation"] = {
            "slot": proposed_slot.position_key,
            "is_optimal": is_opt,
            "reason": reason,
            "score_gap": gap if not math.isinf(gap) else None,
        }

    return report
