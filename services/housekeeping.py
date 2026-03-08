"""
services/housekeeping.py
========================
Optimisation hors-pic (off-peak) du yard par Recherche Tabou (Tabu Search).

Objectif : réorganiser les piles existantes pour éliminer :
    1. Les violations EDD (Earliest Departure Date) — c'est-à-dire les situations 
       où un conteneur qui part plus tôt est bloqué par un conteneur plus tard au-dessus.
    2. Les violations de Stabilité (Poids) — situations où un conteneur lourd 
       est posé sur un conteneur plus léger.

Stratégie :
    1. Calculer le coût global du yard (nb de violations existantes).
    2. Générer des mouvements candidats : déplacer un conteneur d'une pile
       vers le sommet d'une autre pile compatible.
    3. Sélectionner le meilleur mouvement non-tabou qui améliore le coût.
    4. Mettre à jour la liste tabou (paire source→dest récemment utilisée).
    5. Répéter jusqu'à épuisement des itérations ou coût nul.

Auteur  : PFE Marsa Maroc
Version : 1.0 (Tabu Search Housekeeping)
"""

from __future__ import annotations

import math
import random
import threading
from dataclasses import dataclass, field
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

def _count_yard_violations(yard: Yard) -> int:
    """
    Compte le nombre total de violations (cost function).
    Gère gracieusement les IDs manquants dans le registre.
    """
    total = 0
    registry = yard.containers_registry
    for block in yard.blocks.values():
        for stack in block.stacks.values():
            occupied = [s for s in stack.slots if s.container_id]
            
            for i in range(len(occupied)):
                cid_low = occupied[i].container_id
                if cid_low not in registry: continue
                c_low = registry[cid_low]
                
                for j in range(i + 1, len(occupied)):
                    cid_high = occupied[j].container_id
                    if cid_high not in registry: continue
                    c_high = registry[cid_high]
                    
                    if c_high.departure_time > c_low.departure_time:
                        total += 1
                    if j == i + 1 and c_high.weight > c_low.weight:
                        total += 1
            
            # Pénalité énorme pour les gaps (floating containers)
            # Tier N occupé alors que Tier N-1 est vide
            for i in range(1, len(stack.slots)):
                if stack.slots[i].container_id and not stack.slots[i-1].container_id:
                    total += 500 # Coût dissuasif
    return total

def _compact_stack(stack: Stack) -> int:
    """Élimine les gaps dans une pile en faisant descendre les conteneurs."""
    moves = 0
    while True:
        gap_found = False
        for i in range(1, len(stack.slots)):
            if stack.slots[i].container_id and not stack.slots[i-1].container_id:
                stack.slots[i-1].container_id = stack.slots[i].container_id
                stack.slots[i].container_id = None
                gap_found = True
                moves += 1
        if not gap_found:
            break
    return moves

def _compact_yard(yard: Yard) -> int:
    """Élimine tous les gaps du yard."""
    total_moves = 0
    for block in yard.blocks.values():
        for stack in block.stacks.values():
            total_moves += _compact_stack(stack)
    if total_moves > 0:
        print(f"🧹 Compaction : {total_moves} conteneurs descendus pour boucher les vides.")
    return total_moves


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

    # 1. Retirer de la destination (le plus haut occupé correspondant à l'ID)
    for s in reversed(dst_stack.slots):
        if s.container_id == container_id:
            s.container_id = None
            break

    # 2. Remettre en source (le plus bas libre pour éviter les "floating containers")
    # top_free_slot renvoie le premier slot libre en partant du bas (tier 1).
    target_slot = src_stack.top_free_slot
    if target_slot:
        target_slot.container_id = container_id


# ---------------------------------------------------------------------------
# Algorithme principal : Recherche Tabou
# ---------------------------------------------------------------------------

@dataclass
class HousekeepingResult:
    """Résultat de l'exécution du housekeeping."""
    initial_violations: int
    final_violations: int
    violations_reduced: int
    moves_made: int
    iterations: int
    improvement_pct: float
    gaps_fixed: int = 0


# Global lock for yard operations during metaheuristics
YARD_LOCK = threading.Lock()

def run_tabu_search_housekeeping(
    yard: Yard,
    max_iterations: int = 200,
    tabu_tenure: int = 15,
    max_no_improve: int = 50,
) -> HousekeepingResult:
    """
    Exécute la Recherche Tabou avec protection thread-safe et auto-compaction.
    """
    with YARD_LOCK:
        # 0. Compactage initial pour boucher les trous (sécurité visualization)
        gaps_fixed = _compact_yard(yard)
        
        initial_cost = _count_yard_violations(yard)
        current_cost = initial_cost
        best_cost    = initial_cost
        moves_made   = 0
        no_improve   = 0

        # Liste tabou : dict {move → iteration de libération}
        tabu_dict: Dict[Move, int] = {}

        for iteration in range(max_iterations):
            if current_cost == 0:
                break
            if no_improve >= max_no_improve:
                break

            candidates = _generate_candidate_moves(yard)
            if not candidates:
                break

            best_move: Optional[Move] = None
            best_move_cost = float('inf')
            best_move_container_id: Optional[str] = None

            sample = random.sample(candidates, min(50, len(candidates)))

            for move in sample:
                src_stack = yard.get_stack(move[0], move[1])
                if not src_stack: continue
                
                # Trouver l'ID du conteneur top
                container_id = None
                for s in reversed(src_stack.slots):
                    if s.container_id:
                        container_id = s.container_id
                        break
                
                if not container_id: continue

                # Appliquer temporairement avec sécurité
                try:
                    ok = _apply_move(yard, move)
                    if not ok: continue
                    
                    candidate_cost = _count_yard_violations(yard)
                    
                    # Critère tabou et aspiration
                    is_tabu = tabu_dict.get(move, 0) > iteration
                    if (not is_tabu or candidate_cost < best_cost):
                        if candidate_cost < best_move_cost:
                            best_move = move
                            best_move_cost = candidate_cost
                            best_move_container_id = container_id
                finally:
                    _undo_move(yard, move, container_id)

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

        violations_reduced = initial_cost - best_cost
        improvement_pct = (violations_reduced / initial_cost * 100) if initial_cost > 0 else 100.0

        return HousekeepingResult(
            initial_violations=initial_cost,
            final_violations=best_cost,
            violations_reduced=violations_reduced,
            moves_made=moves_made,
            iterations=min(max_iterations, iteration + 1),
            improvement_pct=round(improvement_pct, 1),
            gaps_fixed=gaps_fixed
        )
