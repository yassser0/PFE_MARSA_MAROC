"""
data_generator/generator.py
============================
Génération de données synthétiques réalistes pour le terminal à conteneurs.

Ce module simule des données de yard et de conteneurs qui seraient
normalement extraitee d'un TOS (Terminal Operating System) réel.

Fonctions principales
---------------------
- generate_containers(n)  : génère n conteneurs maritimes aléatoires
- generate_yard(...)      : crée un yard 3D vide configuré

Les données générées respectent les proportions observées dans un
terminal portuaire réel (cf. statistiques Marsa Maroc).

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from typing import List

from models.container import Container, ContainerType
from models.yard import Yard


# ---------------------------------------------------------------------------
# Constantes de simulation — basées sur des statistiques réelles de port
# ---------------------------------------------------------------------------

# Répartition typique des types de conteneurs dans un terminal marocain
CONTAINER_TYPE_WEIGHTS = {
    ContainerType.IMPORT: 0.50,        # 50% import (prédominant)
    ContainerType.EXPORT: 0.35,        # 35% export
    ContainerType.TRANSSHIPMENT: 0.15, # 15% transbordement
}

# Répartition tailles : les 40ft représentent ~60% du trafic mondial
CONTAINER_SIZE_WEIGHTS = {
    20: 0.40,
    40: 0.60,
}

# Plage de poids par type en tonnes (min, max)
WEIGHT_RANGES_BY_TYPE = {
    ContainerType.IMPORT: (8.0, 28.0),        # imports souvent lourds (marchandises)
    ContainerType.EXPORT: (5.0, 25.0),        # exports variés
    ContainerType.TRANSSHIPMENT: (6.0, 30.0), # transbordement : tout type
}

# Fenêtre de départ : entre min_days et max_days à partir d'aujourd'hui
DEPARTURE_WINDOW_DAYS = (1, 21)

# Référence temporelle fixe pour la simulation
_SIMULATION_REFERENCE = datetime(2026, 3, 4, 14, 0, 0)


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def _weighted_choice(weights_dict: dict) -> any:
    """
    Sélectionne une clé aléatoire depuis un dictionnaire pondéré.
    """
    keys = list(weights_dict.keys())
    weights = list(weights_dict.values())
    return random.choices(keys, weights=weights, k=1)[0]


def _generate_container_id() -> str:
    """
    Génère un identifiant de conteneur conforme au standard ISO 6346.
    """
    prefix = random.choice(["MSCU", "CMAU", "MRKU", "TCKU", "TLLU"])
    digits = "".join(random.choices(string.digits, k=7))
    return f"{prefix}{digits}"


def _generate_departure_time(
    reference: datetime = _SIMULATION_REFERENCE,
    min_days: int = DEPARTURE_WINDOW_DAYS[0],
    max_days: int = DEPARTURE_WINDOW_DAYS[1],
) -> datetime:
    """
    Génère une date de départ aléatoire dans la fenêtre de simulation.
    """
    days_offset = random.uniform(min_days, max_days)
    hour = random.choice(range(6, 23, 2))  # 6h, 8h, 10h, ... 22h
    departure = reference + timedelta(days=days_offset)
    return departure.replace(hour=hour, minute=0, second=0, microsecond=0)


# ---------------------------------------------------------------------------
# Générateur de conteneurs
# ---------------------------------------------------------------------------

def generate_containers(n: int) -> List[Container]:
    """
    Génère une liste de n conteneurs synthétiques réalistes.
    """
    if n <= 0:
        raise ValueError(f"Le nombre de conteneurs doit être > 0, reçu : {n}")

    containers: List[Container] = []
    used_ids: set = set()

    for _ in range(n):
        container_id = _generate_container_id()
        while container_id in used_ids:
            container_id = _generate_container_id()
        used_ids.add(container_id)

        c_type: ContainerType = _weighted_choice(CONTAINER_TYPE_WEIGHTS)
        c_size: int = _weighted_choice(CONTAINER_SIZE_WEIGHTS)

        w_min, w_max = WEIGHT_RANGES_BY_TYPE[c_type]
        if c_size == 40:
            w_min = min(w_min * 1.1, w_max - 1)
        weight = round(random.uniform(w_min, w_max), 2)

        departure = _generate_departure_time()

        containers.append(
            Container(
                id=container_id,
                size=c_size,
                weight=weight,
                departure_time=departure,
                type=c_type,
            )
        )

    return containers


# ---------------------------------------------------------------------------
# Générateur de yard
# ---------------------------------------------------------------------------

def generate_yard(
    blocks: int = 4,  # Nombre de blocs standards (A, B, C, D...)
    bays: int = 24,
    rows: int = 6,
    max_height: int = 5,
) -> Yard:
    """
    Génère un yard avec les blocs demandés par l'utilisateur (A...)
    ET ajoute systématiquement des blocs de secours (S1, S2).
    """
    if blocks <= 0 or rows <= 0 or max_height <= 0:
        raise ValueError("Les dimensions du yard doivent être toutes positives.")

    # Blocs standards (A, B, C, D...)
    block_ids = [chr(ord('A') + i) for i in range(blocks)]
    
    # AJOUT AUTOMATIQUE DES BLOCS DE SECOURS
    if "S1" not in block_ids: block_ids.append("S1")
    if "S2" not in block_ids: block_ids.append("S2")

    total_blocks = len(block_ids)

    yard = Yard(
        n_blocks=total_blocks,
        n_bays=bays,
        n_rows=rows,
        max_height=max_height,
        block_ids=block_ids
    )
    
    # Configuration spatiale TC3 Digital Twin
    slot_width = 2.8    # Largeur pour laisser passer les jambes du RTG
    slot_length = 6.4   # Longueur standard conteneur + marges
    
    block_width = rows * slot_width
    block_length = bays * slot_length
    
    # Zones de circulation (Digital Twin standard)
    truck_main_road = 30.0  # Espacement horizontal réduit pour centrage
    internal_service_lane = 20.0 # Espacement vertical réduit pour centrage
    
    # Calcul des offsets pour centrer parfaitement les 4 zones (2x2) autour de (0,0)
    total_grid_width = 2 * block_width + truck_main_road
    total_grid_length = 2 * block_length + internal_service_lane
    
    base_x = -total_grid_width / 2.0 + block_width / 2.0
    base_y = -total_grid_length / 2.0 + block_length / 2.0

    for i, (block_id, block) in enumerate(yard.blocks.items()):
        # Layout intelligent : 
        # A-D selon leurs positions TC3 habituelles
        # S1, S2 toujours en extension (ligne 3)
        # Autres blocs (E, F...) remplissent par défaut les lignes suivantes
        
        if block_id == 'A':
            col, row_in_col = 1, 0
        elif block_id == 'B':
            col, row_in_col = 1, 1
        elif block_id == 'C':
            col, row_in_col = 0, 0
        elif block_id == 'D':
            col, row_in_col = 0, 1
        elif block_id == 'S1':
            col, row_in_col = 0, 2
        elif block_id == 'S2':
            col, row_in_col = 1, 2
        else:
            # Pour les autres blocs (E, F...) on évite les lignes 0, 1, 2 si possible
            col, row_in_col = i % 2, (i // 2) + 1 # Décalage pour éviter A-D
        
        # Positionnement centré
        block.x = base_x + col * (block_width + truck_main_road)
        block.y = base_y + row_in_col * (block_length + internal_service_lane)
        block.width = block_width
        block.length = block_length
        block.rotation = 0.0
        
    return yard
