import time
import json
import random
import requests
from datetime import datetime, timedelta

# Configuration de l'API
API_URL = "http://127.0.0.1:8000"
ENDPOINT_SINGLE = f"{API_URL}/containers/place"
ENDPOINT_BATCH = f"{API_URL}/containers/place_batch"
ENDPOINT_HOUSEKEEPING = f"{API_URL}/yard/housekeeping"

# Paramètres d'optimisation
BATCH_SIZE = 5      # Nombre de conteneurs à accumuler avant optimization batch
HOUSEKEEPING_FREQ = 2 # Déclencher le housekeeping tous les N batches

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
        
    days_to_departure = random.randint(1, 30)
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

def run_streaming():
    print(f"📡 Démarrage du Streaming Live (Buffer: {BATCH_SIZE} containers)...")
    print("Appuyez sur Ctrl+C pour arrêter.")
    
    container_count = 0
    batch_count = 0
    buffer = []
    
    try:
        while True:
            # Générer un nouveau conteneur et l'ajouter au buffer
            new_container = generate_random_container()
            buffer.append(new_container)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📥 Container reçu. Buffer: {len(buffer)}/{BATCH_SIZE}")
            
            # Si le buffer est plein, on traite le batch
            if len(buffer) >= BATCH_SIZE:
                try:
                    print(f"🚀 Envoi du batch de {BATCH_SIZE} conteneurs à l'optimiseur...")
                    response = requests.post(ENDPOINT_BATCH, json=buffer)
                    
                    if response.status_code == 200:
                        data = response.json()
                        container_count += data['containers_placed']
                        batch_count += 1
                        print(f"✅ Batch #{batch_count} traité : {data['message']} (Occupancy: {data['yard_occupancy']})")
                        
                        # Vider le buffer
                        buffer = []
                        
                        # Déclenchement périodique du Housekeeping (Tabu Search)
                        if batch_count % HOUSEKEEPING_FREQ == 0:
                            print("🧹 Lancement du Housekeeping automatique (Tabu Search)...")
                            hk_res = requests.post(ENDPOINT_HOUSEKEEPING)
                            if hk_res.status_code == 200:
                                hk_data = hk_res.json()
                                print(f"✨ {hk_data['message']}")
                            else:
                                print(f"⚠️ Erreur Housekeeping ({hk_res.status_code}): {hk_res.text}")
                    else:
                        print(f"⚠️ Erreur API Batch ({response.status_code}): {response.text}")
                        if "Yard" in response.text:
                            print("🛑 Le Yard semble plein. Arrêt du streaming.")
                            break
                            
                except requests.exceptions.ConnectionError:
                    print("🚨 API injoignable. Tentative de reconnexion dans 5 secondes...")
                    time.sleep(5)
                    continue
            
            # Délai aléatoire entre 0.5 et 1.5 secondes pour simuler un flux rapide
            time.sleep(random.uniform(0.5, 1.5))
            
    except KeyboardInterrupt:
        # Traiter les conteneurs restants dans le buffer si possible
        if buffer:
            print(f"\n📦 Traitement des {len(buffer)} conteneurs restants dans le buffer...")
            requests.post(ENDPOINT_BATCH, json=buffer)
            container_count += len(buffer)
            
        print(f"\n🛑 Streaming arrêté. Total : {container_count} conteneurs placés.")

if __name__ == "__main__":
    print(" === SIMULATEUR DE STREAMING LIVE ===")
    
    reset_choice = input("🔄 Réinitialiser le yard avant de démarrer le streaming ? (o/N) : ").lower()
    if reset_choice == 'o':
        try:
            requests.post(f"{API_URL}/yard/init", json={"blocks": 4, "rows": 10, "max_height": 4})
            print("🧹 Nettoyage terminé.\n")
            time.sleep(1)
        except requests.exceptions.ConnectionError:
             pass
            
    run_streaming()
