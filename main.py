"""
main.py
=======
Point d'entrée principal pour le projet PFE Marsa Maroc.

Permet de lancer au choix :
- L'API FastAPI (serveur web accessible via /docs)
- La simulation CLI (test de charge et calculs des KPIs)

Auteur  : PFE Marsa Maroc
Version : 1.0
"""

import argparse
import sys
import os

# Ajout du chemin racine pour permettre les imports de modules (api, services, simulation...)
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import uvicorn

from simulation.simulator import simulate


def run_api(host: str, port: int, reload: bool):
    """Lance le serveur FastAPI avec Uvicorn."""
    print(f"🚀 Lancement de l'API Marsa Maroc sur http://{host}:{port}/")
    print(f"📚 Documentation Swagger accessible sur http://{host}:{port}/docs")
    if reload:
        print("🔄 Mode rechargement automatique (Hot Reloading) activé")
    
    # Pour que uvicorn trouve 'api.main:app'
    uvicorn.run("api.main:app", host=host, port=port, reload=reload)


def run_simulation(n: int, blocks: int, rows: int, height: int):
    """Lance le moteur de simulation avec les paramètres du yard."""
    print("=" * 60)
    print(" PFE Marsa Maroc — Simulation d'Optimisation du Container Yard")
    print("=" * 60)
    print(f"Paramètres du Yard : {blocks} blocs, {rows} rangées, {height} niveaux")
    print(f"Conteneurs à placer: {n}")
    print("-" * 60)

    try:
        from time import perf_counter
        t0 = perf_counter()
        
        result = simulate(
            n_containers=n,
            blocks=blocks,
            rows=rows,
            max_height=height,
        )
        
        t1 = perf_counter()
    except KeyboardInterrupt:
        print("\nSimulation annulée par l'utilisateur.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" RÉSULTATS — KPIs ACADÉMIQUES")
    print("=" * 60)
    print(f"Temps total d'exécution : {t1 - t0:.2f} secondes")
    print(f"Conteneurs placés       : {result.containers_placed} / {result.containers_processed}")
    print(f"Objectifs échoués       : {result.failed_placements} (Yard plein ou incohérence)")
    print("-" * 60)
    print(f"1. Total Rehandles (estimé) : {result.total_rehandles_estimated}")
    print(f"2. Taux d'occupation        : {result.occupancy_rate:.1%}")
    print(f"3. Hauteur moyenne          : {result.average_stack_height:.2f} conteneurs")
    print(f"4. Temps de décision moyen  : {result.average_decision_time_ms:.3f} ms/conteneur")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Marsa Maroc PFE — Optimisation Yard 3D"
    )
    
    subparsers = parser.add_subparsers(dest="mode", help="Mode d'exécution")
    
    # --- Mode API ---
    api_parser = subparsers.add_parser("api", help="Lancer l'API REST FastAPI")
    api_parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Hôte d'écoute (défaut: 127.0.0.1)"
    )
    api_parser.add_argument(
        "--port", type=int, default=8000, help="Port d'écoute (défaut: 8000)"
    )
    api_parser.add_argument(
        "--reload", action="store_true", help="Activer le rechargement automatique du code"
    )

    # --- Mode Simulation ---
    sim_parser = subparsers.add_parser("simulate", help="Lancer la simulation par lots")
    sim_parser.add_argument(
        "-n", "--containers", type=int, default=100, 
        help="Nombre de conteneurs à simuler (défaut: 100)"
    )
    sim_parser.add_argument(
        "--blocks", type=int, default=4, help="Nombre de blocs dans le yard (défaut: 4)"
    )
    sim_parser.add_argument(
        "--rows", type=int, default=10, help="Nombre de rangées par bloc (défaut: 10)"
    )
    sim_parser.add_argument(
        "--height", type=int, default=4, help="Hauteur maximale des piles (défaut: 4)"
    )

    args = parser.parse_args()

    if args.mode == "api":
        run_api(host=args.host, port=args.port, reload=args.reload)
    elif args.mode == "simulate":
        run_simulation(
            n=args.containers,
            blocks=args.blocks,
            rows=args.rows,
            height=args.height,
        )
    else:
        parser.print_help()
