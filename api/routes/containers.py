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
from typing import Optional

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

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int) -> int:
        if v not in (20, 40):
            raise ValueError("La taille doit être 20 ou 40 EVP.")
        return v


class ProposedSlotSchema(BaseModel):
    """Slot proposé pour évaluation d'optimalité."""
    block_id: str = Field(..., description="Identifiant du bloc (A, B, C, D)", examples=["A"])
    row: int = Field(..., description="Numéro de rangée (commence à 1)", ge=1, examples=[3])
    tier: int = Field(..., description="Niveau de hauteur (commence à 1)", ge=1, examples=[1])


# Update forward ref
ContainerRequest.model_rebuild()


class SlotResponse(BaseModel):
    """Représentation d'un slot dans la réponse."""
    block: str
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


# ---------------------------------------------------------------------------
# Endpoint principal
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
            row=request.proposed_slot.row,
            tier=request.proposed_slot.tier,
        )

    # Générer le rapport de placement
    report = placement_report(container, yard, proposed_slot=proposed_slot_obj)

    if report.get("best_slot") is None:
        raise HTTPException(
            status_code=503,
            detail="Le yard est plein. Aucun slot disponible.",
        )

    # Effectuer le placement réel dans le yard
    best_slot = Slot(
        block_id=report["best_slot"]["block"],
        row=report["best_slot"]["row"],
        tier=report["best_slot"]["tier"],
    )
    success = yard.place_container(best_slot, container.id)
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Impossible de placer le conteneur au slot {best_slot.position_key}.",
        )

    # Enregistrer le conteneur dans le registre en mémoire
    container_registry[container.id] = container

    bd = report.get("score_breakdown") or {}

    return PlacementResponse(
        container_id=container.id,
        container_size=container.size,
        container_type=container.type.value,
        best_slot=SlotResponse(
            block=report["best_slot"]["block"],
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
