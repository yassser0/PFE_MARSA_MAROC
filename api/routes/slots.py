"""
api/routes/slots.py
====================
Route FastAPI pour les slots disponibles.

Endpoint :
    GET /slots/available
    → Retourne la liste des slots libres dans le yard.
    → Accepte un paramètre optionnel `container_size` pour filtrer
      les slots compatibles avec un type de conteneur (20 ou 40 ft).

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/slots", tags=["Slots"])


# ---------------------------------------------------------------------------
# Schémas de réponse
# ---------------------------------------------------------------------------

class AvailableSlotResponse(BaseModel):
    """Représentation d'un slot disponible."""
    block_id: str
    bay: int
    row: int
    tier: int
    position_key: str
    stack_current_height: int
    stack_max_height: int


class AvailableSlotsListResponse(BaseModel):
    """Liste paginée des slots disponibles."""
    total_available: int
    container_size_filter: Optional[int]
    slots: List[AvailableSlotResponse]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/available",
    response_model=AvailableSlotsListResponse,
    summary="Liste des slots disponibles",
    description="""
Retourne tous les slots libres et accessibles dans le yard.

Un slot est **valide** si :
- Il est libre
- Il est au sommet de sa pile (aucun "trou" dans la pile)
- La pile n'est pas pleine

Si `container_size=40` est passé, seuls les slots avec une rangée adjacente
libre sont retournés (pour les conteneurs 40ft).
    """,
)
async def get_available_slots(
    container_size: Optional[int] = Query(
        None,
        description="Filtrer par taille de conteneur (20 ou 40 EVP)",
        examples=[20, 40],
    ),
):
    """Retourne les slots disponibles, avec filtrage optionnel par taille."""
    from api.main import app as _app
    from models.container import Container, ContainerType
    from services.optimizer import get_valid_slots
    from datetime import datetime

    yard = _app.state.yard

    # Si un filtre de taille est demandé, utiliser get_valid_slots
    if container_size in (20, 40):
        # Créer un conteneur fictif pour filtrer les slots valides
        dummy_container = Container(
            id="FILTER-DUMMY",
            size=container_size,
            weight=10.0,
            departure_time=datetime(2026, 3, 20),
            type=ContainerType.IMPORT,
        )
        valid_slots = get_valid_slots(dummy_container, yard)
    else:
        # Retourner tous les slots libres au sommet de leur pile
        valid_slots = []
        for block in yard.blocks.values():
            for stack in block.stacks.values():
                top_slot = stack.top_free_slot
                if top_slot is not None:
                    valid_slots.append(top_slot)

    # Construire la réponse
    slots_response: List[AvailableSlotResponse] = []
    for slot in valid_slots:
        block = yard.blocks.get(slot.block_id)
        stack = block.stacks.get((slot.bay, slot.row)) if block else None
        slots_response.append(
            AvailableSlotResponse(
                block_id=slot.block_id,
                bay=slot.bay,
                row=slot.row,
                tier=slot.tier,
                position_key=slot.position_key,
                stack_current_height=stack.current_height if stack else 0,
                stack_max_height=stack.max_height if stack else 0,
            )
        )

    return AvailableSlotsListResponse(
        total_available=len(slots_response),
        container_size_filter=container_size,
        slots=slots_response,
    )
