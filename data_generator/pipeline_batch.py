import time
import json
import random
import requests
from datetime import datetime, timedelta

# Configuration de l'API
API_URL = "http://127.0.0.1:8000"
ENDPOINT = f"{API_URL}/containers/place_batch"

# Configuration de la pipeline
TOTAL_CONTAINERS = 480 # Nombre total de conteneurs à envoyer en un seul bloc
DELAY_DAYS_MIN = 1      # Jours min avant départ
DELAY_DAYS_MAX = 30     # Jours max avant départ

# Listes pour générer des attributs aléatoires réalistes
SIZES = [20, 40]
TYPES = ["import", "export", "transshipment"]

def generate_random_container() -> dict:
    """Génère un conteneur d'exemple."""
    size = random.choice(SIZES)
    ctype = random.choice(TYPES)
    
    if size == 40:
        weight = round(random.uniform(15.0, 30.0), 1)
    else:
        weight = round(random.uniform(5.0, 25.0), 1)
        
    days_to_departure = random.randint(DELAY_DAYS_MIN, DELAY_DAYS_MAX)
    hours_to_departure = random.randint(0, 23)
    departure_dt = datetime.now() + timedelta(days=days_to_departure, hours=hours_to_departure)
    
    return {
        "size": size,
        "weight": weight,
        "type": ctype,
        "departure_time": departure_dt.isoformat(),
        # Optionnel: on peut spécifier les zones souhaitées
        "zones_20ft": ["A", "B"],
        "zones_40ft": ["C", "D"]
    }

def run_pipeline():
    print(f"📦 Génération de la Pipeline : {TOTAL_CONTAINERS} conteneurs...")
    
    payload = []
    for _ in range(TOTAL_CONTAINERS):
        payload.append(generate_random_container())
        
    print(f"🚀 Envoi des {TOTAL_CONTAINERS} conteneurs en BATCH (Optimisation EDD)...")
    
    start_time = time.time()
    try:
        response = requests.post(ENDPOINT, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            duration = time.time() - start_time
            print("\n✅ PIPELINE TRAITÉE AVEC SUCCÈS")
            print("-" * 40)
            print(f"Conteneurs reçus  : {data['total_received']}")
            print(f"Conteneurs placés : {data['containers_placed']}")
            print(f"Temps API interne : {data['processing_time_ms']} ms")
            print(f"Temps total HTTP  : {duration:.2f} secondes")
            print(f"Occupation Yard   : {data['yard_occupancy']}")
            if data['failed_placements'] > 0:
                print(f"⚠️ Échecs (Yard plein) : {data['failed_placements']}")
        else:
            print(f"❌ Erreur API ({response.status_code}): {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("🚨 ERREUR: L'API n'est pas accessible. Avez-vous lancé 'python main.py api' ?")

if __name__ == "__main__":
    print(" === SIMULATEUR DE PIPELINE BATCH ===")
    
    reset_choice = input("🔄 Réinitialiser le yard avant d'envoyer la pipeline ? (o/N) : ").lower()
    if reset_choice == 'o':
        try:
            requests.post(f"{API_URL}/yard/init", json={"blocks": 4, "rows": 10, "max_height": 4})
            print("🧹 Nettoyage terminé.\n")
            time.sleep(1)
        except requests.exceptions.ConnectionError:
             pass
            
    run_pipeline()
