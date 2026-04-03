"""
models/yard.py
==============
Modèle 3D du parc à conteneurs (Container Yard).

Hiérarchie du yard :
    Yard
    └── Block  (zone physique délimitée)
        └── Stack (pile = coordonnée block + row)
            └── Slot  (emplacement = block + row + tier)

Le parc est modélisé en 3 dimensions :
- Block : division horizontale principale (ex. A, B, C, D)
- Row   : rangée à l'intérieur d'un block
- Tier  : niveau de hauteur (tier 1 = sol)

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Slot — Un emplacement unitaire dans le yard
# ---------------------------------------------------------------------------

@dataclass
class Slot:
    """
    Représente un emplacement physique dans le parc.

    Coordonnées 3D : (block_id, bay, row, tier)
    - block_id  : identifiant du bloc (ex. 'A', 'B', ...)
    - bay       : numéro de travée (longitudinal)
    - row       : numéro de rangée (transversal)
    - tier      : niveau de hauteur (1 = sol, max = max_height)
    - container_id : identifiant du conteneur présent, None si libre
    """
    block_id: str
    bay: int
    row: int
    tier: int
    container_id: Optional[str] = None

    @property
    def is_free(self) -> bool:
        """True si l'emplacement est libre."""
        return self.container_id is None

    @property
    def position_key(self) -> str:
        """Clé unique représentant la position 3D."""
        return self.localization

    @property
    def localization(self) -> str:
        """
        Retourne la localisation au format [BLOC][TRAVEE][CELLULE][NIVEAU]
        Exemple : K019A04
        - BLOC    : 1-2 lettres (block_id)
        - TRAVEE  : 3 chiffres (bay)
        - CELLULE : Lettre A-F (row)
        - NIVEAU  : 2 chiffres (tier)
        """
        cellule = chr(ord('A') + self.row - 1)
        return f"{self.block_id}-{self.bay:03d}-{cellule}-{self.tier:02d}"

    @staticmethod
    def from_localization(loc: str) -> Dict[str, any]:
        """
        Parse une chaîne de localisation et retourne les composants.
        Exemple: "K-019-A-04" -> {'block_id': 'K', 'bay': 19, 'row': 1, 'tier': 4}
        """
        import re
        clean_loc = loc.upper().replace(" ", "")
        # Pattern flexible : Supporte A, B, C, D mais aussi S1, S2, K019 etc.
        # Groupes: (BLOC)-(TRAVEE)-(CELLULE)-(NIVEAU)
        pattern = r"([A-Z0-9]{1,3})[-]?(\d{3})[-]?([A-Z])[-]?(\d{2})"
        match = re.search(pattern, clean_loc)
        if not match:
            raise ValueError(f"Format de localisation invalide: {loc}")
        
        block_id, bay_str, row_str, tier_str = match.groups()
        return {
            "block_id": block_id,
            "bay": int(bay_str),
            "row": ord(row_str) - ord('A') + 1,
            "tier": int(tier_str)
        }

    def __repr__(self) -> str:
        status = "libre" if self.is_free else f"CNTR:{self.container_id}"
        return f"Slot({self.localization}, {status})"


# ---------------------------------------------------------------------------
# Stack — Colonne verticale de slots (même block + même row)
# ---------------------------------------------------------------------------

@dataclass
class Stack:
    """
    Colonne verticale d'emplacements (même block, bay et row).

    Contient max_height slots empilés verticalement.
    Le tier 1 est le sol, tier max_height est le sommet.
    """
    block_id: str
    bay: int
    row: int
    max_height: int
    slots: List[Slot] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialise les slots vides si la liste n'est pas fournie."""
        if not self.slots:
            self.slots = [
                Slot(block_id=self.block_id, bay=self.bay, row=self.row, tier=t)
                for t in range(1, self.max_height + 1)
            ]

    @property
    def current_height(self) -> int:
        """Hauteur actuelle de la pile (nombre de slots occupés)."""
        return sum(1 for s in self.slots if not s.is_free)

    @property
    def is_full(self) -> bool:
        """True si tous les niveaux sont occupés."""
        return self.current_height >= self.max_height

    @property
    def top_free_slot(self) -> Optional[Slot]:
        """Retourne le prochain slot libre en bas de la pile (LIFO)."""
        for slot in self.slots:  # slots triés tier 1 → max
            if slot.is_free:
                return slot
        return None

    def get_container_sizes(self, containers_registry: dict) -> set:
        """
        Retourne l'ensemble des tailles (en pieds) des conteneurs présents dans
        cette pile. Exemple : {20} si seuls des 20ft, {40} si seuls des 40ft.
        Utilise le registre du Yard pour retrouver les objets Container.
        """
        sizes: set = set()
        for slot in self.slots:
            if slot.container_id and slot.container_id in containers_registry:
                container = containers_registry[slot.container_id]
                if hasattr(container, 'size'):
                    sizes.add(container.size)
        return sizes

    def get_containers_above(self, tier: int) -> List[str]:
        """
        Retourne les IDs de conteneurs au-dessus d'un niveau donné.
        Utile pour estimer les rehandles nécessaires.
        """
        return [
            s.container_id
            for s in self.slots
            if s.tier > tier and s.container_id is not None
        ]

    def __repr__(self) -> str:
        return (
            f"Stack({self.block_id}, B{self.bay}, R{self.row}, "
            f"height={self.current_height}/{self.max_height})"
        )


# ---------------------------------------------------------------------------
# Block — Zone physique regroupant plusieurs stacks
# ---------------------------------------------------------------------------

@dataclass
class Block:
    """
    Zone physique du parc regroupant une grille de piles (bays × rows).

    Chaque block contient n_bays * n_rows stacks.
    """
    block_id: str
    n_bays: int
    n_rows: int
    max_height: int
    stacks: Dict[Tuple[int, int], Stack] = field(default_factory=dict)
    
    # Propriétés spatiales (pour le layout dynamique)
    x: float = 0.0          # Position X dans le terminal (mètres)
    y: float = 0.0          # Position Y dans le terminal (mètres)
    width: float = 10.0     # Largeur du bloc (mètres, transversal)
    length: float = 50.0    # Longueur du bloc (mètres, longitudinal)
    rotation: float = 0.0   # Rotation en degrés

    def __post_init__(self) -> None:
        """Initialise la grille de stacks si non fournis."""
        if not self.stacks:
            for b in range(1, self.n_bays + 1):
                for r in range(1, self.n_rows + 1):
                    self.stacks[(b, r)] = Stack(
                        block_id=self.block_id, bay=b, row=r, max_height=self.max_height
                    )

    @property
    def occupancy(self) -> float:
        """Taux d'occupation du bloc (0.0 à 1.0)."""
        total = self.n_bays * self.n_rows * self.max_height
        used = sum(s.current_height for s in self.stacks.values())
        return used / total if total > 0 else 0.0

    def __repr__(self) -> str:
        return (
            f"Block({self.block_id!r}, bays={self.n_bays}, rows={self.n_rows}, "
            f"occupancy={self.occupancy:.1%})"
        )


# ---------------------------------------------------------------------------
# Yard — Le parc à conteneurs complet
# ---------------------------------------------------------------------------

@dataclass
class Yard:
    """
    Représentation complète du parc à conteneurs (Container Yard).

    Structure 3D : blocks × bays × rows × tiers

    Attributs
    ----------
    n_blocks    : nombre de blocs
    n_bays      : nombre de travées par bloc
    n_rows      : nombre de rangées par bloc
    max_height  : hauteur maximale des piles
    blocks      : dictionnaire {block_id → Block}
    """
    n_blocks: int
    n_bays: int
    n_rows: int
    max_height: int
    block_ids: Optional[List[str]] = None
    blocks: Dict[str, Block] = field(default_factory=dict)
    containers_registry: Dict[str, 'Container'] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialise les blocs. Utilise block_ids si fourni, sinon A, B, C..."""
        if not self.blocks:
            ids = self.block_ids if self.block_ids else [chr(ord('A') + i) for i in range(self.n_blocks)]
            for b_id in ids:
                self.blocks[b_id] = Block(
                    block_id=b_id,
                    n_bays=self.n_bays,
                    n_rows=self.n_rows,
                    max_height=self.max_height,
                )

    # ------------------------------------------------------------------
    # Propriétés globales
    # ------------------------------------------------------------------

    @property
    def total_capacity(self) -> int:
        """Capacité totale du yard en nombre de slots."""
        return self.n_blocks * self.n_bays * self.n_rows * self.max_height

    @property
    def used_slots(self) -> int:
        """Nombre de slots actuellement occupés."""
        count = 0
        for block in self.blocks.values():
            for stack in block.stacks.values():
                count += stack.current_height
        return count

    @property
    def occupancy_rate(self) -> float:
        """Taux d'occupation global du yard (0.0 à 1.0)."""
        return self.used_slots / self.total_capacity if self.total_capacity > 0 else 0.0

    @property
    def average_stack_height(self) -> float:
        """Hauteur moyenne de toutes les piles."""
        heights = [
            stack.current_height
            for block in self.blocks.values()
            for stack in block.stacks.values()
        ]
        return sum(heights) / len(heights) if heights else 0.0

    # ------------------------------------------------------------------
    # Opérations sur les conteneurs
    # ------------------------------------------------------------------

    def place_container(self, slot: Slot, container: 'Container') -> bool:
        """
        Place un conteneur dans un slot donné.

        Returns True si succès, False si le slot est déjà occupé.
        """
        block = self.blocks.get(slot.block_id)
        if block is None:
            return False
        stack = block.stacks.get((slot.bay, slot.row))
        if stack is None:
            return False
        target_slot = stack.slots[slot.tier - 1]  # tiers indexés à 1
        if not target_slot.is_free:
            return False
        
        target_slot.container_id = container.id
        self.containers_registry[container.id] = container
        return True

    def remove_container(self, slot: Slot) -> Optional[str]:
        """
        Retire le conteneur d'un slot.

        Returns l'ID du conteneur retiré, ou None si le slot était libre.
        """
        block = self.blocks.get(slot.block_id)
        if block is None:
            return None
        stack = block.stacks.get((slot.bay, slot.row))
        if stack is None:
            return None
        target_slot = stack.slots[slot.tier - 1]
        container_id = target_slot.container_id
        target_slot.container_id = None
        
        if container_id and container_id in self.containers_registry:
            del self.containers_registry[container_id]
            
        return container_id

    def get_all_slots(self) -> List[Slot]:
        """Retourne la liste de tous les slots du yard."""
        slots: List[Slot] = []
        for block in self.blocks.values():
            for stack in block.stacks.values():
                slots.extend(stack.slots)
        return slots

    def get_free_slots(self) -> List[Slot]:
        """Retourne la liste des slots libres."""
        return [s for s in self.get_all_slots() if s.is_free]

    def get_stack(self, block_id: str, bay: int, row: int) -> Optional[Stack]:
        """Accès direct à une pile par ses coordonnées."""
        block = self.blocks.get(block_id)
        return block.stacks.get((bay, row)) if block else None

    def __repr__(self) -> str:
        return (
            f"Yard(blocks={self.n_blocks}, bays={self.n_bays}, rows={self.n_rows}, "
            f"max_height={self.max_height}, "
            f"occupancy={self.occupancy_rate:.1%})"
        )
