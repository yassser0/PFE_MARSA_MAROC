"""
models/container.py
===================
Définition du modèle de données pour un conteneur maritime.

Ce module fournit :
- ContainerType : énumération des types de conteneurs (import, export, transbordement)
- Container     : dataclass représentant un conteneur avec tous ses attributs

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class ContainerType(str, Enum):
    """
    Type opérationnel du conteneur.
    - IMPORT       : conteneur arrivant au port pour livraison locale
    - EXPORT       : conteneur en attente d'embarquement
    - TRANSSHIPMENT: conteneur en transit vers un autre navire
    """
    IMPORT = "import"
    EXPORT = "export"
    TRANSSHIPMENT = "transshipment"


@dataclass
class Container:
    """
    Représentation d'un conteneur maritime.

    Attributs
    ----------
    id              : identifiant unique (format CNTR-XXXXXXXX)
    size            : taille en pieds — 20 ou 40 EVP (Équivalent Vingt Pieds)
    weight          : poids en tonnes (entre 5 et 30)
    departure_time  : date/heure prévue de départ du terminal
    type            : type opérationnel (import, export, transshipment)
    """

    id: str
    size: Literal[20, 40]
    weight: float                # en tonnes
    departure_time: datetime
    type: ContainerType

    def is_heavy(self) -> bool:
        """Retourne True si le conteneur est considéré comme lourd (> 20t)."""
        return self.weight > 20.0

    def days_until_departure(self, reference: datetime | None = None) -> float:
        """
        Calcule le nombre de jours restants avant le départ.

        Parameters
        ----------
        reference : date de référence (par défaut : now)

        Returns
        -------
        float : jours restants (peut être négatif si déjà parti)
        """
        ref = reference or datetime.now()
        delta = self.departure_time - ref
        return delta.total_seconds() / 86_400

    def __repr__(self) -> str:
        return (
            f"Container(id={self.id!r}, size={self.size}ft, "
            f"weight={self.weight:.1f}t, type={self.type.value}, "
            f"departure={self.departure_time.strftime('%Y-%m-%d')})"
        )
