import sys
import os
import random
import time
from copy import deepcopy

# Ajout du chemin racine au python path
sys.path.append(os.getcwd())

from models.yard import Yard
from models.container import Container
from data_generator.generator import generate_containers, generate_yard
from services.optimizer import find_best_slot, get_valid_slots
from services.scoring import calculate_score
from services.housekeeping import _count_yard_violations

def run_benchmark(n_containers=50):
    print("="*60)
    print(f"BENCHMARK : SYSTÈME D'OPTIMISATION (N={n_containers})")
    print("="*60)

    # 1. Préparation des données
    containers = generate_containers(n_containers)
    
    # 2. TEST A : Placement Aléatoire (Baseline)
    yard_random = generate_yard(blocks=4, bays=10, rows=3, max_height=4)
    start_random = time.time()
    rehandles_random_at_placement = 0
    total_score_random = 0
    
    for c in containers:
        valid_slots = get_valid_slots(c, yard_random, strict_edd=False)
        if not valid_slots:
            print(f"Yard Random plein après {containers.index(c)} conteneurs")
            break
        
        # Choix purement aléatoire
        slot = random.choice(valid_slots)
        
        score = calculate_score(slot, c, yard_random)
        total_score_random += score
        
        # On place physiquement
        yard_random.place_container(slot, c)
    
    end_random = time.time()
    final_rehandles_random = _count_yard_violations(yard_random)

    # 3. TEST B : Placement avec Optimisation (Simulated Annealing)
    yard_opt = generate_yard(blocks=4, bays=10, rows=3, max_height=4)
    start_opt = time.time()
    total_score_opt = 0
    
    for c in containers:
        result = find_best_slot(c, yard_opt)
        if not result:
            print(f"Yard Opt plein après {containers.index(c)} conteneurs")
            break
        
        slot, score = result
        total_score_opt += score
        
        # On place physiquement
        yard_opt.place_container(slot, c)
    
    end_opt = time.time()
    final_rehandles_opt = _count_yard_violations(yard_opt)

    # 4. RÉSULTATS
    print("\nRÉSULTATS COMPARATIFS :")
    print("-" * 30)
    print(f"{'Métrique':<25} | {'Aléatoire':<12} | {'Optimisé':<12}")
    print("-" * 60)
    print(f"{'Rehandles (conflits EDD)':<25} | {final_rehandles_random:<12} | {final_rehandles_opt:<12}")
    print(f"{'Score Total (bas=mieux)':<25} | {total_score_random:<12.2f} | {total_score_opt:<12.2f}")
    print(f"{'Score Moyen':<25} | {total_score_random/n_containers:<12.2f} | {total_score_opt/n_containers:<12.2f}")
    print(f"{'Temps d\'exécution (s)':<25} | {end_random-start_random:<12.4f} | {end_opt-start_opt:<12.4f}")
    print("-" * 60)

    reduction = ((final_rehandles_random - final_rehandles_opt) / final_rehandles_random * 100) if final_rehandles_random > 0 else 0
    print(f"\nRÉDUCTION DES REHANDLES : {reduction:.1f}%")
    
    if final_rehandles_opt < final_rehandles_random:
        print("L'optimisation est EFFICACE.")
    else:
        print("L'optimisation n'a pas montré d'amélioration significative sur ce lot.")

if __name__ == "__main__":
    run_benchmark(50)
