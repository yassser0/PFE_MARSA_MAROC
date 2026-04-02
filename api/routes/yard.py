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
Version : 1.1
"""

from __future__ import annotations
from typing import Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from data_generator.generator import generate_yard
from datetime import datetime

router = APIRouter(prefix="/yard", tags=["Yard"])

# ---------------------------------------------------------------------------
# Schémas de réponse
# ---------------------------------------------------------------------------

class SlotInfo(BaseModel):
    """État d'un slot individuel."""
    tier: int
    is_free: bool
    container_id: Optional[str]
    container_details: Optional[dict] = None


class StackInfo(BaseModel):
    """État d'une pile (stack)."""
    bay: int
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
    x: float
    y: float
    width: float
    length: float
    rotation: float


class YardStateResponse(BaseModel):
    """État complet du yard."""
    n_blocks: int
    n_bays: int
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
    bays: int
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
)
async def get_yard_state():
    """Retourne l'état complet du yard en temps réel."""
    from api.main import app as _app
    from api.database import db as _db
    from models.container import Container, ContainerType
    from models.yard import Slot
    
    yard = _app.state.yard
    registry = _app.state.container_registry
    last_reset = _app.state.last_reset_time

    # --- Synchronisation Dynamique avec MongoDB ---
    mongo_containers = await _db.get_all_containers()
    
    for doc in mongo_containers:
        cntr_id = doc["id"]
        
        # Filtre 1: Ignorer les conteneurs créés avant le dernier "Clear All"
        imported_at = doc.get("imported_at")
        if imported_at:
            if isinstance(imported_at, str):
                imported_at = datetime.fromisoformat(imported_at)
        else:
            imported_at = datetime.min
            
        if imported_at < last_reset:
            continue

        # Si le conteneur n'est pas encore dans le yard en mémoire
        if cntr_id not in registry:
            try:
                # 1. Créer l'objet Container
                dep_dt = doc["departure_time"]
                if isinstance(dep_dt, str):
                    dep_dt = datetime.fromisoformat(dep_dt)
                
                container = Container(
                    id=cntr_id,
                    size=doc["size"],
                    weight=doc["weight"],
                    departure_time=dep_dt,
                    type=ContainerType(doc["type"])
                )
                
                # 2. Convertir le slot string en objet Slot
                slot_info = Slot.from_localization(doc["slot"])
                target_slot = Slot(**slot_info)
                
                # 3. Placer dans le yard mémoire
                if yard.place_container(target_slot, container):
                    registry[cntr_id] = container
            except Exception:
                pass

    # --- Construction de la réponse ---
    blocks_info: List[BlockInfo] = []
    for block_id, block in yard.blocks.items():
        stacks_info: List[StackInfo] = []
        for (bay, row), stack in block.stacks.items():
            slots_info = []
            for s in stack.slots:
                details = None
                # Si le slot est occupé et qu'on a le conteneur dans le registre
                if s.container_id and s.container_id in registry:
                    c = registry[s.container_id]
                    details = {
                        "size": c.size,
                        "weight": c.weight,
                        "type": c.type.value,
                        "departure_time": c.departure_time.strftime("%Y-%m-%d %H:%M"),
                        "location": s.localization
                    }
                
                slots_info.append(
                    SlotInfo(
                        tier=s.tier,
                        is_free=s.is_free,
                        container_id=s.container_id,
                        container_details=details
                    )
                )
            
            stacks_info.append(
                StackInfo(
                    bay=bay,
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
                x=block.x,
                y=block.y,
                width=block.width,
                length=block.length,
                rotation=block.rotation
            )
        )

    return YardStateResponse(
        n_blocks=yard.n_blocks,
        n_bays=yard.n_bays,
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
)
async def init_yard(request: YardInitRequest):
    """Initialise le yard en mémoire avec de nouvelles dimensions."""
    from api.main import app as _app

    nouveau_yard = generate_yard(
        blocks=request.blocks, 
        bays=request.bays,
        rows=request.rows, 
        max_height=request.max_height
    )
    
    _app.state.yard = nouveau_yard
    _app.state.container_registry = {}
    _app.state.last_reset_time = datetime.now()
    
    from api.database import db as _db
    await _db.db.containers.update_many({"slot": {"$exists": True}}, {"$unset": {"slot": ""}})
    
    print(f"🧹 Yard réinitialisé à {_app.state.last_reset_time}")

    return YardInitResponse(
        message="Yard initialisé avec succès (Filtre temporel activé).",
        total_capacity=nouveau_yard.total_capacity
    )
