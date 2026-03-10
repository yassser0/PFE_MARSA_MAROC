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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application.
    Initialise le Yard au démarrage.
    """
    print("🚀 Démarrage de l'API Marsa Maroc Yard Optimization")
    
    # Création du yard initial (4 blocs, 10 bays, 3 rows, max 4 conteneurs de haut)
    app.state.yard = generate_yard(blocks=4, bays=10, rows=3, max_height=4)
    
    # Registre des conteneurs pour garder la trace de ce qui est dans le yard
    # (En production, ce serait une base de données)
    app.state.container_registry = {}
    
    print(f"📦 Yard initialisé : capacité totale de {app.state.yard.total_capacity} slots")
    
    yield
    
    # Nettoyage à l'arrêt si nécessaire
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
