"""
services/silver_layer.py
========================
Moteur de traitement haute performance pour le nettoyage et la validation 
des données d'entrée (Silver Layer).

Fonctionnalités :
- Déduplication par ID (pandas)
- Validation structurelle (schéma)
- Normalisation des types et formats
- Rapport de qualité des données

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Tuple

class SilverLayer:
    """
    Couche logicielle intermédiaire pour assurer l'intégrité et la rapidité
    du traitement des données massives.
    """

    @staticmethod
    def process(raw_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Nettoie et valide un lot de données brutes.
        
        Args:
            raw_data: Liste de dictionnaires (depuis un CSV).
            
        Returns:
            Tuple containing:
            - Cleaned data (list of dicts)
            - Quality report (stats)
        """
        if not raw_data:
            return [], {"total": 0, "cleaned": 0, "duplicates": 0, "invalid": 0}

        # 1. Conversion en DataFrame pour la performance
        df = pd.DataFrame(raw_data)
        total_initial = len(df)

        # 2. Déduplication (Garder la première occurrence d'un ID)
        # On s'assure que 'id' existe
        if 'id' in df.columns:
            initial_count = len(df)
            df = df.drop_duplicates(subset=['id'], keep='first')
            duplicates_removed = initial_count - len(df)
        else:
            duplicates_removed = 0

        # 3. Validation Structurelle & Nettoyage
        # On définit les colonnes requises
        required_cols = ['id', 'weight', 'size', 'departure_time']
        
        # Filtrer si des colonnes manquent
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
             return [], {"error": f"Colonnes manquantes : {', '.join(missing_cols)}"}

        # Conversion des types
        try:
            df['weight'] = pd.to_numeric(df['weight'], errors='coerce')
            df['size'] = pd.to_numeric(df['size'], errors='coerce')
            
            # Filtrage des valeurs invalides (NaN après conversion)
            invalid_rows = df[df['weight'].isna() | df['size'].isna() | df['id'].isna()]
            df = df.dropna(subset=['id', 'weight', 'size'])
            
            # Validation des domaines
            # Poids entre 1 et 50, Taille 20 ou 40
            df = df[(df['weight'] >= 1.0) & (df['weight'] <= 50.0)]
            df = df[df['size'].isin([20, 40])]
            
            # Normalisation du type (default 'import')
            allowed_types = ['import', 'export', 'transshipment']
            if 'type' not in df.columns:
                df['type'] = 'import'
            df['type'] = df['type'].fillna('import').str.lower()
            
            # Filtrer les types invalides
            df = df[df['type'].isin(allowed_types)]
            
            invalid_count = total_initial - len(df) - duplicates_removed

        except Exception as e:
            return [], {"error": f"Erreur fatale lors de la transformation : {str(e)}"}

        # 4. Conversion finale en dictionnaires pour le moteur de placement
        cleaned_data = df.to_dict(orient='records')

        report = {
            "total_raw": total_initial,
            "duplicates_removed": duplicates_removed,
            "invalid_rows_filtered": invalid_count,
            "total_cleaned": len(cleaned_data),
            "quality_score": round((len(cleaned_data) / total_initial) * 100, 1) if total_initial > 0 else 0
        }

        return cleaned_data, report
