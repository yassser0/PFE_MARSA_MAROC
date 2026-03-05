"""
services/housekeeping.py
========================
Optimisation hors-pic (off-peak) du yard par Recherche Tabou (Tabu Search).

Objectif : réorganiser les piles existantes pour éliminer les violations EDD
(Earliest Departure Date) — c'est-à-dire les situations où un conteneur
qui part plus tôt est bloqué par un conteneur qui part plus tard au-dessus de lui.

Stratégie :
    1. Calculer le coût global du yard (nb de paires rehandle existantes).
    2. Générer des mouvements candidats : déplacer un conteneur d'une pile
       vers le sommet d'une autre pile compatible.
    3. Sélectionner le meilleur mouvement non-tabou qui améliore le coût.
    4. Mettre à jour la liste tabou (paire source→dest récemment utilisée).
    5. Répéter jusqu'à épuisement des itérations ou coût nul.

Auteur  : PFE Marsa Maroc
Version : 1.0 (Tabu Search Housekeeping)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from models.container import Container
from models.yard import Slot, Stack, Yard


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Move = Tuple[str, int, str, int]   # (src_block, src_row, dst_block, dst_row)


# ---------------------------------------------------------------------------
# Calcul du coût global (nombre de paires rehandle dans tout le yard)
# ---------------------------------------------------------------------------

def _count_rehandle_pairs(yard: Yard) -> int:
    """
    Compte le nombre total de paires (container_bas, container_dessus) où
    container_bas part AVANT container_dessus → rehandle inévitable.
    
    Un coût de 0 signifie que le yard est parfaitement ordonné (EDD).
    """
    total = 0
    for block in yard.blocks.values():
        for stack in block.stacks.values():
            occupied = [
                s for s in stack.slots
                if s.container_id and s.container_id in yard.containers_registry
            ]
            # Comparer chaque paire (bas, haut)
            for i in range(len(occupied)):
                for j in range(i + 1, len(occupied)):
                    c_low  = yard.containers_registry[occupied[i].container_id]
                    c_high = yard.containers_registry[occupied[j].container_id]
                    # Le conteneur du haut part après celui du bas → rehandle
                    if c_high.departure_time > c_low.departure_time:
                        total += 1
    return total


def _get_stack_container_sizes(stack: Stack, registry: dict) -> set:
    """Retourne l'ensemble des tailles de conteneurs dans la pile."""
    sizes = set()
    for s in stack.slots:
        if s.container_id and s.container_id in registry:
            c = registry[s.container_id]
            if hasattr(c, 'size'):
                sizes.add(c.size)
    return sizes


# ---------------------------------------------------------------------------
# Génération des mouvements candidats
# ---------------------------------------------------------------------------

def _generate_candidate_moves(yard: Yard) -> List[Move]:
    """
    Génère tous les mouvements valides : déplacer le conteneur au sommet
    d'une pile (source) vers le sommet d'une autre pile compatible (destination).

    Contraintes respectées :
    - On ne déplace que le conteneur du SOMMET de la pile source (accessible).
    - La pile destination ne doit pas être pleine.
    - La pile destination doit contenir uniquement la même taille de conteneur
      (homogénéité de taille).
    - La pile destination doit appartenir au même groupe de blocs (20ft→A/B, 40ft→C/D).
    """
    moves: List[Move] = []

    for src_block_id, src_block in yard.blocks.items():
        for src_row, src_stack in src_block.stacks.items():
            if src_stack.current_height == 0:
                continue  # pile vide, rien à déplacer

            # Récupérer le conteneur au sommet (tier le plus haut occupé)
            top_slot = None
            for s in reversed(src_stack.slots):
                if s.container_id:
                    top_slot = s
                    break
            if top_slot is None:
                continue

            top_container = yard.containers_registry.get(top_slot.container_id)
            if top_container is None:
                continue

            container_size = getattr(top_container, 'size', None)

            # Chercher des piles destination valides
            for dst_block_id, dst_block in yard.blocks.items():
                # Respect homogénéité des blocs (20ft → A/B, 40ft → C/D)
                if container_size == 20 and dst_block_id not in ('A', 'B'):
                    continue
                if container_size == 40 and dst_block_id not in ('C', 'D'):
                    continue

                for dst_row, dst_stack in dst_block.stacks.items():
                    # Pas la même pile
                    if dst_block_id == src_block_id and dst_row == src_row:
                        continue
                    # Pas pleine
                    if dst_stack.is_full:
                        continue
                    # Homogénéité de taille dans la pile destination
                    dst_sizes = _get_stack_container_sizes(dst_stack, yard.containers_registry)
                    if dst_sizes and container_size not in dst_sizes:
                        continue

                    moves.append((src_block_id, src_row, dst_block_id, dst_row))

    return moves


# ---------------------------------------------------------------------------
# Application d'un mouvement
# ---------------------------------------------------------------------------

def _apply_move(yard: Yard, move: Move) -> bool:
    """
    Déplace le conteneur au sommet de la pile source vers la pile destination.
    
    Returns True si le mouvement a été effectué, False sinon.
    """
    src_block_id, src_row, dst_block_id, dst_row = move

    src_stack = yard.get_stack(src_block_id, src_row)
    dst_stack = yard.get_stack(dst_block_id, dst_row)
    if src_stack is None or dst_stack is None:
        return False

    # Trouver le slot sommet source (le plus haut occupé)
    src_slot = None
    for s in reversed(src_stack.slots):
        if s.container_id:
            src_slot = s
            break
    if src_slot is None:
        return False

    # Trouver le prochain slot libre en destination
    dst_slot = dst_stack.top_free_slot
    if dst_slot is None:
        return False

    # Effectuer le déplacement
    container_id = src_slot.container_id
    src_slot.container_id = None
    dst_slot.container_id = container_id
    return True


def _undo_move(yard: Yard, move: Move, container_id: str) -> None:
    """Annule un mouvement précédent (utilisé pour évaluation sans commit)."""
    src_block_id, src_row, dst_block_id, dst_row = move

    dst_stack = yard.get_stack(dst_block_id, dst_row)
    src_stack = yard.get_stack(src_block_id, src_row)
    if dst_stack is None or src_stack is None:
        return

    # Retirer de la destination (dernier occupé)
    for s in reversed(dst_stack.slots):
        if s.container_id == container_id:
            s.container_id = None
            break

    # Remettre en source (prochain libre)
    for s in reversed(src_stack.slots):
        if not s.container_id:
            s.container_id = container_id
            break


# ---------------------------------------------------------------------------
# Algorithme principal : Recherche Tabou
# ---------------------------------------------------------------------------

@dataclass
class HousekeepingResult:
    """Résultat de l'exécution du housekeeping."""
    initial_rehandles: int
    final_rehandles: int
    rehandles_reduced: int
    moves_made: int
    iterations: int
    improvement_pct: float


def run_tabu_search_housekeeping(
    yard: Yard,
    max_iterations: int = 200,
    tabu_tenure: int = 15,
    max_no_improve: int = 50,
) -> HousekeepingResult:
    """
    Exécute la Recherche Tabou pour reorganiser le yard et éliminer
    les violations EDD existantes.

    Parameters
    ----------
    yard            : état actuel du yard
    max_iterations  : nombre maximal d'itérations de la boucle
    tabu_tenure     : durée pendant laquelle un mouvement reste dans la liste tabou
    max_no_improve  : arrête si aucune amélioration après N itérations

    Returns
    -------
    HousekeepingResult : statistiques de l'optimisation
    """
    initial_cost = _count_rehandle_pairs(yard)
    current_cost = initial_cost
    best_cost    = initial_cost
    moves_made   = 0
    no_improve   = 0

    # Liste tabou : dict {move → iteration de libération}
    tabu_dict: Dict[Move, int] = {}

    for iteration in range(max_iterations):
        if current_cost == 0:
            break  # Yard parfaitement ordonné, on s'arrête
        if no_improve >= max_no_improve:
            break  # Aucune amélioration depuis longtemps

        candidates = _generate_candidate_moves(yard)
        if not candidates:
            break  # Plus de mouvements possibles

        # Évaluer les candidats non-tabous (ou qui battent le meilleur global)
        best_move: Optional[Move] = None
        best_move_cost = float('inf')
        best_move_container_id: Optional[str] = None

        # Limiter l'évaluation pour les performances (max 50 candidats aléatoires)
        sample = random.sample(candidates, min(50, len(candidates)))

        for move in sample:
            # Récupérer l'ID du conteneur qui sera déplacé
            src_stack = yard.get_stack(move[0], move[1])
            if src_stack is None:
                continue
            container_id = None
            for s in reversed(src_stack.slots):
                if s.container_id:
                    container_id = s.container_id
                    break
            if container_id is None:
                continue

            # Appliquer temporairement
            ok = _apply_move(yard, move)
            if not ok:
                continue
            candidate_cost = _count_rehandle_pairs(yard)
            _undo_move(yard, move, container_id)

            is_tabu = tabu_dict.get(move, 0) > iteration
            # Critère d'aspiration : accepte même si tabou si c'est le meilleur global
            if (not is_tabu or candidate_cost < best_cost):
                if candidate_cost < best_move_cost:
                    best_move = move
                    best_move_cost = candidate_cost
                    best_move_container_id = container_id

        if best_move is None:
            no_improve += 1
            continue

        # Appliquer le meilleur mouvement
        _apply_move(yard, best_move)
        tabu_dict[best_move] = iteration + tabu_tenure
        current_cost = best_move_cost
        moves_made += 1

        if current_cost < best_cost:
            best_cost = current_cost
            no_improve = 0
        else:
            no_improve += 1

    rehandles_reduced = initial_cost - best_cost
    improvement_pct = (rehandles_reduced / initial_cost * 100) if initial_cost > 0 else 100.0

    return HousekeepingResult(
        initial_rehandles=initial_cost,
        final_rehandles=best_cost,
        rehandles_reduced=rehandles_reduced,
        moves_made=moves_made,
        iterations=min(max_iterations, iteration + 1),
        improvement_pct=round(improvement_pct, 1),
    )
