"""
api/routes/yard.py
==================
Route FastAPI pour consulter et modifier l'état du yard.

Endpoint :
    GET /yard
    → Retourne la structure complète du yard (blocs, rangées, tiers).
    POST /yard/init
    → Initialise ou réinitialise le yard avec les dimensions spécifiées.

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from data_generator.generator import generate_yard

router = APIRouter(prefix="/yard", tags=["Yard"])


# ---------------------------------------------------------------------------
# Schémas de réponse
# ---------------------------------------------------------------------------

class SlotInfo(BaseModel):
    """État d'un slot individuel."""
    tier: int
    is_free: bool
    container_id: Optional[str]


class StackInfo(BaseModel):
    """État d'une pile (stack)."""
    row: int
    current_height: int
    max_height: int
    is_full: bool
    slots: List[SlotInfo]


class BlockInfo(BaseModel):
    """État d'un bloc."""
    block_id: str
    n_rows: int
    occupancy: float
    stacks: List[StackInfo]


class YardStateResponse(BaseModel):
    """État complet du yard."""
    n_blocks: int
    n_rows: int
    max_height: int
    total_capacity: int
    used_slots: int
    occupancy_rate: float
    average_stack_height: float
    blocks: List[BlockInfo]

class YardInitRequest(BaseModel):
    """Requête d'initialisation du yard."""
    blocks: int
    rows: int
    max_height: int

class YardInitResponse(BaseModel):
    """Réponse de l'initialisation du yard."""
    message: str
    total_capacity: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=YardStateResponse,
    summary="État actuel du yard",
    description="Retourne la structure complète du parc à conteneurs avec l'état de chaque slot.",
)
async def get_yard_state():
    """Retourne l'état complet du yard en temps réel."""
    from api.main import app as _app

    yard = _app.state.yard

    blocks_info: List[BlockInfo] = []
    for block_id, block in yard.blocks.items():
        stacks_info: List[StackInfo] = []
        for row, stack in block.stacks.items():
            slots_info = [
                SlotInfo(
                    tier=s.tier,
                    is_free=s.is_free,
                    container_id=s.container_id,
                )
                for s in stack.slots
            ]
            stacks_info.append(
                StackInfo(
                    row=row,
                    current_height=stack.current_height,
                    max_height=stack.max_height,
                    is_full=stack.is_full,
                    slots=slots_info,
                )
            )
        blocks_info.append(
            BlockInfo(
                block_id=block_id,
                n_rows=block.n_rows,
                occupancy=round(block.occupancy, 4),
                stacks=stacks_info,
            )
        )

    return YardStateResponse(
        n_blocks=yard.n_blocks,
        n_rows=yard.n_rows,
        max_height=yard.max_height,
        total_capacity=yard.total_capacity,
        used_slots=yard.used_slots,
        occupancy_rate=round(yard.occupancy_rate, 4),
        average_stack_height=round(yard.average_stack_height, 4),
        blocks=blocks_info,
    )

@router.post(
    "/init",
    response_model=YardInitResponse,
    summary="Initialiser / Réinitialiser le yard",
    description="Crée un nouveau yard vide avec les dimensions spécifiées.",
)
async def init_yard(request: YardInitRequest):
    """Initialise le yard en mémoire avec de nouvelles dimensions."""
    from api.main import app as _app

    # Générer un nouveau yard
    nouveau_yard = generate_yard(
        blocks=request.blocks, 
        rows=request.rows, 
        max_height=request.max_height
    )
    
    # Mettre à jour l'état de l'application
    _app.state.yard = nouveau_yard
    
    # Optionnel : réinitialiser le registre des conteneurs
    _app.state.container_registry = {}

    return YardInitResponse(
        message="Yard initialisé avec succès.",
        total_capacity=nouveau_yard.total_capacity
    )
