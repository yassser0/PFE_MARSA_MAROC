"""
api/routes/containers.py
=========================
Route FastAPI pour le placement des conteneurs.

Endpoint :
    POST /containers/place
    → Accepte les données d'un conteneur et retourne le slot optimal.

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from models.container import Container, ContainerType
from models.yard import Slot
from services.optimizer import find_best_slot, is_placement_optimal, placement_report
from services.scoring import score_breakdown

router = APIRouter(prefix="/containers", tags=["Conteneurs"])


# ---------------------------------------------------------------------------
# Schémas Pydantic (Request / Response)
# ---------------------------------------------------------------------------

class ContainerRequest(BaseModel):
    """Corps de la requête POST /containers/place."""

    size: int = Field(
        ...,
        description="Taille du conteneur en pieds (20 ou 40 EVP)",
        examples=[20, 40],
    )
    weight: float = Field(
        ...,
        description="Poids du conteneur en tonnes (5.0 à 30.0)",
        ge=1.0,
        le=50.0,
        examples=[12.5],
    )
    type: ContainerType = Field(
        ...,
        description="Type opérationnel du conteneur",
        examples=["import"],
    )
    departure_time: datetime = Field(
        ...,
        description="Date et heure prévues de départ (ISO 8601)",
        examples=["2026-03-20T10:00:00"],
    )
    proposed_slot: Optional[ProposedSlotSchema] = Field(
        None,
        description="Slot proposé à évaluer (optionnel). Si fourni, l'API indique s'il est optimal.",
    )
    zones_20ft: Optional[list[str]] = Field(
        None,
        description="Liste des blocs dédiés aux conteneurs 20ft (ex: ['A', 'B'])",
    )
    zones_40ft: Optional[list[str]] = Field(
        None,
        description="Liste des blocs dédiés aux conteneurs 40ft (ex: ['C', 'D'])",
    )

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        if v not in (20, 40):
            raise ValueError("La taille doit être 20 ou 40 EVP.")
        return v


class ProposedSlotSchema(BaseModel):
    """Slot proposé pour évaluation d'optimalité."""
    block_id: str = Field(..., description="Identifiant du bloc (A, B, C, D)", examples=["A"])
    bay: int = Field(..., description="Numéro de travée (commence à 1)", ge=1, examples=[5])
    row: int = Field(..., description="Numéro de rangée (commence à 1)", ge=1, examples=[2])
    tier: int = Field(..., description="Niveau de hauteur (commence à 1)", ge=1, examples=[1])


# Update forward ref
ContainerRequest.model_rebuild()


class SlotResponse(BaseModel):
    """Représentation d'un slot dans la réponse."""
    block: str
    bay: int
    row: int
    tier: int
    position_key: str


class ScoreBreakdownResponse(BaseModel):
    """Détail du calcul de score."""
    rehandle_score: float
    height_score: float
    distance_score: float
    total: float


class PlacementResponse(BaseModel):
    """Réponse complète à la requête de placement."""
    container_id: str
    container_size: int
    container_type: str
    best_slot: Optional[SlotResponse]
    best_score: Optional[float]
    score_breakdown: Optional[ScoreBreakdownResponse]
    yard_occupancy: str
    available_slots_count: int
    placed: bool
    proposed_evaluation: Optional[dict] = None
    message: str


class PlacementBatchResponse(BaseModel):
    """Réponse pour l'insertion en masse de données (Pipeline)."""
    total_received: int
    containers_placed: int
    failed_placements: int
    yard_occupancy: str
    processing_time_ms: float
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/place",
    response_model=PlacementResponse,
    summary="Placer un conteneur dans le yard",
    description="""
Calcule le slot optimal pour un conteneur et le place dans le yard.

**Logique de scoring** :
- Rehandles estimés (poids × 3)
- Hauteur actuelle de la pile (poids × 2)
- Distance approximative à la porte (poids × 1)

Si un `proposed_slot` est fourni, l'API compare aussi ce slot avec l'optimal.
    """,
)
async def place_container(
    request: ContainerRequest,
    # Le yard est injecté depuis le state de l'application
    # Voir api/main.py pour l'initialisation
):
    """Place un conteneur dans le meilleur slot disponible."""
    from api.main import app as _app  # import tardif pour éviter les imports circulaires

    yard = _app.state.yard
    container_registry = _app.state.container_registry

    # Construire l'objet Container
    import uuid
    container = Container(
        id=f"API-{uuid.uuid4().hex[:8].upper()}",
        size=request.size,
        weight=request.weight,
        departure_time=request.departure_time,
        type=request.type,
    )

    # Évaluer le slot proposé si fourni
    proposed_slot_obj: Optional[Slot] = None
    if request.proposed_slot:
        proposed_slot_obj = Slot(
            block_id=request.proposed_slot.block_id.upper(),
            bay=request.proposed_slot.bay,
            row=request.proposed_slot.row,
            tier=request.proposed_slot.tier,
        )

    # Attach dynamic zones if provided.
    # Use None (not []) so that get_valid_slots applies its default block-zone logic
    # (20ft → blocks A/B, 40ft → blocks C/D) when no override is given.
    allowed_blocks = None
    if container.size == 20 and request.zones_20ft:
        allowed_blocks = [z.upper() for z in request.zones_20ft]
    elif container.size == 40 and request.zones_40ft:
        allowed_blocks = [z.upper() for z in request.zones_40ft]

    # Générer le rapport de placement
    report = placement_report(container, yard, proposed_slot=proposed_slot_obj, allowed_blocks=allowed_blocks)

    if report.get("best_slot") is None:
        raise HTTPException(
            status_code=503,
            detail="Le yard est plein. Aucun slot disponible.",
        )

    # Effectuer le placement réel dans le yard
    best_slot = Slot(
        block_id=report["best_slot"]["block"],
        bay=report["best_slot"]["bay"],
        row=report["best_slot"]["row"],
        tier=report["best_slot"]["tier"],
    )
    # Pass the full Container object so yard.containers_registry is populated
    # (the optimizer reads this registry to enforce size-homogeneity between stacks)
    success = yard.place_container(best_slot, container)
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Impossible de placer le conteneur au slot {best_slot.position_key}.",
        )

    # Also keep the app-level registry in sync (used by the dashboard)
    container_registry[container.id] = container

    bd = report.get("score_breakdown") or {}

    return PlacementResponse(
        container_id=container.id,
        container_size=container.size,
        container_type=container.type.value,
        best_slot=SlotResponse(
            block=report["best_slot"]["block"],
            bay=report["best_slot"]["bay"],
            row=report["best_slot"]["row"],
            tier=report["best_slot"]["tier"],
            position_key=report["best_slot"]["position_key"],
        ),
        best_score=report["best_score"],
        score_breakdown=ScoreBreakdownResponse(
            rehandle_score=bd.get("rehandle_score", 0.0),
            height_score=bd.get("height_score", 0.0),
            distance_score=bd.get("distance_score", 0.0),
            total=bd.get("total", 0.0),
        ),
        yard_occupancy=report["yard_occupancy"],
        available_slots_count=report["available_slots_count"],
        placed=True,
        proposed_evaluation=report.get("proposed_evaluation"),
        message=f"Conteneur {container.id} placé avec succès en {best_slot.position_key}.",
    )


@router.post(
    "/place_batch",
    response_model=PlacementBatchResponse,
    summary="Pipeline Data : Placer un lot de conteneurs (Batch)",
    description="""
Accepte une liste entière de conteneurs entrants (ex: fichier portuaire Excel).
**Optimisation magique** : La route trie d'abord les conteneurs par `departure_time` décroissant (EDD inverse).
Les conteneurs partant le plus tard sont donc empilés au fond en premier, garantissant mathématiquement **zéro rehandle**.
    """
)
async def place_containers_batch(
    requests: List[ContainerRequest],
):
    import time
    import uuid
    from api.main import app as _app

    yard = _app.state.yard
    container_registry = _app.state.container_registry

    start_time = time.perf_counter()

    # 1. Trier la pipeline par Date de Départ Inverse (EDD)
    # Les conteneurs partant le plus tard (departure_time le plus grand) sont placés en premier.
    sorted_requests = sorted(requests, key=lambda r: r.departure_time, reverse=True)

    placed_count = 0
    failed_count = 0

    for req in sorted_requests:
        container = Container(
            id=f"B-{uuid.uuid4().hex[:8].upper()}",
            size=req.size,
            weight=req.weight,
            departure_time=req.departure_time,
            type=req.type,
        )

        allowed_blocks = None
        if container.size == 20 and req.zones_20ft:
            allowed_blocks = [z.upper() for z in req.zones_20ft]
        elif container.size == 40 and req.zones_40ft:
            allowed_blocks = [z.upper() for z in req.zones_40ft]

        best_result = find_best_slot(container, yard, allowed_blocks=allowed_blocks)
        
        if best_result is None:
            failed_count += 1
            continue

        best_slot, _ = best_result
        success = yard.place_container(best_slot, container)
        
        if success:
            container_registry[container.id] = container
            placed_count += 1
        else:
            failed_count += 1

    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000

    return PlacementBatchResponse(
        total_received=len(requests),
        containers_placed=placed_count,
        failed_placements=failed_count,
        yard_occupancy=f"{yard.occupancy_rate:.1%}",
        processing_time_ms=round(duration_ms, 2),
        message=f"{placed_count}/{len(requests)} placés avec succès en {duration_ms:.0f}ms."
    )

