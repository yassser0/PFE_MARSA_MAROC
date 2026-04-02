"""
api/main.py
===========
Point d'entrée de l'API FastAPI.

Initialise l'application, configure les middlewares (CORS) et monte
les différents routeurs.
Le Yard (état global du parc) est stocké dans le state de l'application
pour être partagé entre les requêtes.

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import containers, slots, yard
from data_generator.generator import generate_yard
from api.database import db
from datetime import datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application.
    Initialise le Yard au démarrage.
    """
    print("🚀 Démarrage de l'API Marsa Maroc Yard Optimization")
    
    # Initialisation de la base de données MongoDB
    await db.connect_to_storage()

    # Création du yard initial (Dynamique 4 blocs, 24 travées, 12 rangées)
    app.state.yard = generate_yard(blocks=4, bays=24, rows=12, max_height=5)
    app.state.container_registry = {}
    app.state.last_reset_time = datetime.now()
    app.state.buffer_zone = []
    
    # État global du job ETL asynchrone pour éviter les conflits
    app.state.etl_job = {
        "status": "none", # "none", "processing", "success", "error"
        "message": "Aucun traitement en cours.",
        "result": None
    }
    
    print(f"📦 Yard initialisé : capacité totale de {app.state.yard.total_capacity} slots")
    
    yield
    
    # Nettoyage à l'arrêt
    await db.close_storage_connection()
    print("🛑 Arrêt de l'API")


app = FastAPI(
    title="Marsa Maroc — Yard Optimization API",
    description="API de gestion et d'optimisation du placement des conteneurs dans le yard.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuration CORS pour permettre aux dashboards (ex. React, Vue, Streamlit) de s'y connecter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, restreindre aux domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montage des routeurs
app.include_router(containers.router)
app.include_router(yard.router)
app.include_router(slots.router)


@app.get("/", tags=["Health"])
async def root():
    """Route de vérification de l'état de l'API."""
    return {
        "status": "online",
        "service": "Yard Optimization API",
        "docs_url": "/docs",
    }
