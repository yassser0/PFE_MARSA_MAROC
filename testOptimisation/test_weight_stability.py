import sys
import os
import random

# Ajout du chemin racine au python path
sys.path.append(os.getcwd())

from models.yard import Yard
from models.container import Container, ContainerType
from data_generator.generator import generate_yard
from services.optimizer import find_best_slot
from services.housekeeping import _count_yard_violations, run_tabu_search_housekeeping
from datetime import datetime

def test_weight_stability():
    print("="*60)
    print("🧪 TEST : STABILITÉ PHYSIQUE DES POIDS")
    print("="*60)

    # 1. Préparation du yard
    yard = generate_yard(blocks=1, rows=5, max_height=4)
    ref_time = datetime(2026, 3, 5, 12, 0, 0)

    # 2. Scénario : Placer un conteneur léger puis tenter un lourd
    c_light = Container(id="LIGHT01", size=20, weight=5.0, departure_time=ref_time, type=ContainerType.IMPORT)
    c_heavy = Container(id="HEAVY01", size=20, weight=30.0, departure_time=ref_time, type=ContainerType.IMPORT)

    print(f"\n1. Placement du conteneur LÉGER ({c_light.weight}t)...")
    res1 = find_best_slot(c_light, yard)
    if res1:
        slot1, _ = res1
        yard.place_container(slot1, c_light)
        print(f"✅ Placé en {slot1.position_key}")

    print(f"\n2. Tentative de placement du LOURD ({c_heavy.weight}t) au-dessus du LÉGER...")
    # Normalement l'optimiseur devrait trouver un AUTRE slot ou refuser si c'est la seule option (selon fallback)
    res2 = find_best_slot(c_heavy, yard)
    if res2:
        slot2, _ = res2
        # Vérifions si slot2 est au-dessus de slot1
        if slot2.block_id == slot1.block_id and slot2.row == slot1.row and slot2.tier > slot1.tier:
            print(f"❌ ERREUR : Le conteneur lourd a été placé au-dessus du léger ({slot2.position_key}) !")
        else:
            yard.place_container(slot2, c_heavy)
            print(f"✅ SUCCÈS : Le conteneur lourd a été placé ailleurs ({slot2.position_key}) pour préserver la stabilité.")
    else:
        print("ℹ️ Aucun slot trouvé pour le lourd (normal si yard plein ou contraintes strictes).")

    # 3. Test de Housekeeping sur une situation forcée
    print("\n3. Test Housekeeping sur une instabilité forcée...")
    # On force une instabilité manuellement
    c_light2 = Container(id="LIGHT02", size=20, weight=10.0, departure_time=ref_time, type=ContainerType.IMPORT)
    c_heavy2 = Container(id="HEAVY02", size=20, weight=25.0, departure_time=ref_time, type=ContainerType.IMPORT)
    
    # Pile vide (rangée 5)
    stack5 = yard.get_stack('A', 5)
    yard.place_container(stack5.slots[0], c_light2) # Léger en bas
    yard.place_container(stack5.slots[1], c_heavy2) # Lourd au-dessus (interdit normalement)
    
    violations_initiales = _count_yard_violations(yard)
    print(f"Violations détectées (EDD + Poids) : {violations_initiales}")
    
    if violations_initiales > 0:
        print("Lancement du Tabu Search pour corriger...")
        result = run_tabu_search_housekeeping(yard, max_iterations=50)
        print(f"Mouvements effectués : {result.moves_made}")
        print(f"Violations finales : {result.final_violations}")
        
        if result.final_violations < violations_initiales:
            print("✅ Le housekeeping a réussi à réduire/éliminer l'instabilité !")
        else:
            print("⚠️ Le housekeeping n'a pas pu corriger la situation (peut-être manque de slots libres).")

if __name__ == "__main__":
    test_weight_stability()
