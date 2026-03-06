"""
data_generator/generator.py
============================
Génération de données synthétiques réalistes pour le terminal à conteneurs.

Ce module simule des données de yard et de conteneurs qui seraient
normalement extraitees d'un TOS (Terminal Operating System) réel.

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
import uuid
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

    Parameters
    ----------
    weights_dict : {valeur: poids_relatif}

    Returns
    -------
    La clé sélectionnée selon la distribution de probabilité.
    """
    keys = list(weights_dict.keys())
    weights = list(weights_dict.values())
    return random.choices(keys, weights=weights, k=1)[0]


def _generate_container_id() -> str:
    """
    Génère un identifiant de conteneur conforme au standard ISO 6346.
    Format simplifié : MSCU + 7 chiffres (ex. MSCU1234567)

    En production, cet ID serait lu depuis le BL (Bill of Lading).
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

    Les heures sont réalistes (6h–22h, aux heures rondes).
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

    Chaque conteneur possède :
    - Un ID unique au format opérateur + 7 chiffres
    - Une taille 20 ou 40 EVP (selon distribution réelle)
    - Un poids cohérent avec son type
    - Une date de départ dans les 1–21 jours
    - Un type opérationnel (import/export/transshipment)

    Parameters
    ----------
    n : int
        Nombre de conteneurs à générer

    Returns
    -------
    List[Container]
        Liste de n conteneurs uniques

    Example
    -------
    >>> containers = generate_containers(10)
    >>> len(containers)
    10
    >>> all(c.size in (20, 40) for c in containers)
    True
    """
    if n <= 0:
        raise ValueError(f"Le nombre de conteneurs doit être > 0, reçu : {n}")

    containers: List[Container] = []
    used_ids: set = set()

    for _ in range(n):
        # 1. Générer un ID unique
        container_id = _generate_container_id()
        while container_id in used_ids:
            container_id = _generate_container_id()
        used_ids.add(container_id)

        # 2. Choisir le type
        c_type: ContainerType = _weighted_choice(CONTAINER_TYPE_WEIGHTS)

        # 3. Choisir la taille (20ft ou 40ft)
        c_size: int = _weighted_choice(CONTAINER_SIZE_WEIGHTS)

        # 4. Générer le poids (cohérent avec le type)
        w_min, w_max = WEIGHT_RANGES_BY_TYPE[c_type]
        # Légèrement plus lourd pour les 40ft (plus grand volume)
        if c_size == 40:
            w_min = min(w_min * 1.1, w_max - 1)
        weight = round(random.uniform(w_min, w_max), 2)

        # 5. Date de départ
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
    blocks: int = 4,
    rows: int = 10,
    max_height: int = 4,
) -> Yard:
    """
    Génère un yard vide avec la structure 3D spécifiée.

    Le yard est organisé en blocs (zones physiques délimitées par des
    voies de circulation), chaque bloc contenant des rangées de piles.

    Paramètres par défaut inspirés d'un terminal de taille moyenne
    (ex. TC2 de Marsa Maroc — Casablanca) :
    - 4 blocs   : A, B, C, D
    - 10 rangées par bloc
    - 4 niveaux de hauteur maximum

    Parameters
    ----------
    blocks     : int, nombre de blocs (default: 4)
    rows       : int, rangées par bloc (default: 10)
    max_height : int, hauteur max des piles (default: 4)

    Returns
    -------
    Yard
        Instance vide prête à accueillir des conteneurs

    Example
    -------
    >>> yard = generate_yard()
    >>> yard.total_capacity
    160
    >>> yard.occupancy_rate
    0.0
    """
    if blocks <= 0 or rows <= 0 or max_height <= 0:
        raise ValueError("Les dimensions du yard doivent être toutes positives.")
    if blocks > 26:
        raise ValueError("Maximum 26 blocs supportés (A–Z).")

    yard = Yard(
        n_blocks=blocks,
        n_rows=rows,
        max_height=max_height,
    )
    
    # Configuration spatiale réaliste (Layout inspiré de TC3 Casablanca)
    block_width = 15.0     # Largeur d'un bloc (mètres)
    block_length = rows * 1.1 # Longueur basée sur le nombre de conteneurs (~1.1m par slot)
    spacing_x = 25.0       # Espace horizontal entre colonnes (voies de circulation)
    spacing_y = 10.0       # Espace vertical entre blocs
    
    for i, (block_id, block) in enumerate(yard.blocks.items()):
        # Layout en 2 colonnes principales
        col = i % 2
        row_in_col = i // 2
        
        block.x = col * spacing_x
        block.y = row_in_col * (block_length + spacing_y)
        block.width = block_width
        block.length = block_length
        block.rotation = 0.0
        
    return yard
