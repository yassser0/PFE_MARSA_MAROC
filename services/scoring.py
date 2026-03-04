"""
services/scoring.py
====================
Fonction de scoring pour évaluer la qualité d'un emplacement de conteneur.

La fonction de score combine trois critères pondérés :

1. Rehandles estimés (poids fort = 3)
   → Combien de conteneurs devront être déplacés pour accéder à ce conteneur ?
   → Estimé à partir des dates de départ des conteneurs au-dessus.

2. Hauteur actuelle de la pile (poids = 2)
   → Favorise les piles basses pour la stabilité et la sécurité.

3. Distance approximative (poids = 1)
   → Estime la distance entre le slot et la porte d'entrée principale.
   → Basée sur l'index du bloc et de la rangée.

Un score faible = meilleur placement.

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from models.container import Container
from models.yard import Slot, Stack, Yard

# ---------------------------------------------------------------------------
# Poids de la fonction de score (ajustables pour calibration)
# ---------------------------------------------------------------------------

WEIGHT_REHANDLES: float = 3.0   # impact fort — rehandle = coût opérationnel majeur
WEIGHT_HEIGHT: float = 2.0      # impact moyen — stabilité et sécurité
WEIGHT_DISTANCE: float = 1.0    # impact faible — distance relative au slot

# Reference temporelle pour les calculs de départ
_SIMULATION_REFERENCE = datetime(2026, 3, 4, 14, 0, 0)


# ---------------------------------------------------------------------------
# Estimation des rehandles
# ---------------------------------------------------------------------------

def _estimate_rehandles(
    stack: Stack,
    target_tier: int,
    container: Container,
    yard: Yard,
    reference: datetime = _SIMULATION_REFERENCE,
) -> int:
    """
    Estime le nombre de rehandles nécessaires pour récupérer le conteneur
    depuis le slot cible.

    Logique :
    - Un rehandle se produit quand un conteneur au-dessus du cible
      doit être sorti en premier alors que son départ est POSTÉRIEUR
      au conteneur cible (on doit le déplacer temporairement).

    Parameters
    ----------
    stack        : Stack contenant le slot cible
    target_tier  : niveau du slot où le conteneur sera placé
    container    : conteneur à placer
    yard         : état actuel du yard (pour récupérer les dates de départ)
    reference    : date de référence pour comparer les départs

    Returns
    -------
    int : nombre estimé de rehandles (0 à max_height)
    """
    rehandles = 0

    # Récupérer les conteneurs au-dessus du slot cible
    containers_above_ids = stack.get_containers_above(target_tier)

    for above_id in containers_above_ids:
        # Chercher le conteneur dans tous les slots du yard pour obtenir sa date
        # (dans un vrai TOS, ce serait une requête DB directe)
        above_container = _find_container_in_yard(above_id, yard)
        if above_container is None:
            # On ne peut pas évaluer → on compte comme rehandle par précaution
            rehandles += 1
            continue

        # Si le conteneur au-dessus part APRÈS le conteneur cible → rehandle
        if above_container.departure_time > container.departure_time:
            rehandles += 1

    return rehandles


def _find_container_in_yard(container_id: str, yard: Yard) -> Optional[Container]:
    """
    Recherche un conteneur dans le yard par son ID.

    Note : Dans cette simulation, le yard ne stocke que les IDs.
    Cette fonction est un placeholder — en production, on interrogerait
    directement le TOS ou une base de données.

    Pour cette version, retourne None (pas de lookup complet nécessaire
    pour la heuristique simplifiée).
    """
    # Dans la simulation, nous n'avons pas accès aux objets Container
    # depuis le yard (qui stocke uniquement les IDs).
    # Le scoring utilise une approximation basée sur la position.
    return None


# ---------------------------------------------------------------------------
# Distance approximative
# ---------------------------------------------------------------------------

def _compute_distance_score(slot: Slot, yard: Yard) -> float:
    """
    Calcule un score de distance approximatif entre le slot et la
    porte principale d'entrée du terminal.

    Convention : la porte principale est proche du bloc A, rangée 1.
    → Plus le bloc est éloigné (B, C, D) et la rangée est haute, plus la
      distance est grande.

    Parameters
    ----------
    slot  : emplacement à évaluer
    yard  : yard de référence pour normaliser les distances

    Returns
    -------
    float : score de distance normalisé entre 0 et 1
    """
    # Index du bloc (A=0, B=1, C=2, ...)
    block_index = ord(slot.block_id) - ord('A')

    # Distance normalisée : combinaison bloc + rangée
    max_block_idx = yard.n_blocks - 1
    max_row_idx = yard.n_rows - 1

    if max_block_idx == 0 and max_row_idx == 0:
        return 0.0

    block_dist = block_index / max_block_idx if max_block_idx > 0 else 0.0
    row_dist = (slot.row - 1) / max_row_idx if max_row_idx > 0 else 0.0

    # Pondération : le bloc a plus d'impact que la rangée sur la distance réelle
    return 0.6 * block_dist + 0.4 * row_dist


# ---------------------------------------------------------------------------
# Fonction principale de calcul du score
# ---------------------------------------------------------------------------

def calculate_score(slot: Slot, container: Container, yard: Yard) -> float:
    """
    Calcule le score d'un emplacement pour un conteneur donné.

    Formule :
        score = (W_rehandles × rehandles_estimés)
              + (W_height    × hauteur_actuelle)
              + (W_distance  × distance_normalisée)

    Un score plus faible indique un meilleur emplacement.

    Parameters
    ----------
    slot      : slot candidat à évaluer
    container : conteneur à placer
    yard      : état actuel du yard

    Returns
    -------
    float : score composé (plus bas = meilleur)

    Raises
    ------
    ValueError : si le slot n'existe pas dans le yard

    Example
    -------
    >>> score = calculate_score(slot, container, yard)
    >>> score >= 0
    True
    """
    block = yard.blocks.get(slot.block_id)
    if block is None:
        raise ValueError(f"Bloc inconnu : {slot.block_id!r}")

    stack = block.stacks.get(slot.row)
    if stack is None:
        raise ValueError(f"Rangée inconnue : {slot.row} dans bloc {slot.block_id!r}")

    # --- Critère 1 : Rehandles estimés ---
    rehandles = _estimate_rehandles(
        stack=stack,
        target_tier=slot.tier,
        container=container,
        yard=yard,
    )
    rehandle_score = WEIGHT_REHANDLES * rehandles

    # --- Critère 2 : Hauteur actuelle de la pile ---
    # On favorise les piles plus basses (height = tier - 1 = nb conteneurs déjà là)
    height_score = WEIGHT_HEIGHT * (slot.tier - 1)

    # --- Critère 3 : Distance approximative ---
    distance_score = WEIGHT_DISTANCE * _compute_distance_score(slot, yard)

    total_score = rehandle_score + height_score + distance_score

    return round(total_score, 4)


def score_breakdown(slot: Slot, container: Container, yard: Yard) -> dict:
    """
    Retourne le détail du score pour la transparence algorithmique.

    Utile pour l'analyse académique et le débogage.

    Returns
    -------
    dict avec les clés : rehandle_score, height_score, distance_score, total
    """
    block = yard.blocks.get(slot.block_id)
    stack = block.stacks.get(slot.row) if block else None

    rehandles = (
        _estimate_rehandles(stack, slot.tier, container, yard)
        if stack else 0
    )
    distance = _compute_distance_score(slot, yard)

    return {
        "rehandle_score": round(WEIGHT_REHANDLES * rehandles, 4),
        "height_score": round(WEIGHT_HEIGHT * (slot.tier - 1), 4),
        "distance_score": round(WEIGHT_DISTANCE * distance, 4),
        "total": round(
            WEIGHT_REHANDLES * rehandles
            + WEIGHT_HEIGHT * (slot.tier - 1)
            + WEIGHT_DISTANCE * distance,
            4,
        ),
    }
