import time
import json
import random
import requests
from datetime import datetime, timedelta

# Configuration de l'API
API_URL = "http://127.0.0.1:8000"
ENDPOINT = f"{API_URL}/containers/place"

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
    print("📡 Démarrage du Streaming Live de conteneurs...")
    print("Appuyez sur Ctrl+C pour arrêter.")
    
    container_count = 0
    try:
        while True:
            payload = generate_random_container()
            
            try:
                response = requests.post(ENDPOINT, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    container_count += 1
                    best_slot = data['best_slot']
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Conteneur #{container_count} ({payload['size']}ft) placé -> Bloc {best_slot['block']}, Rangée {best_slot['row']}, Niveau {best_slot['tier']}")
                else:
                    print(f"⚠️ Erreur API ({response.status_code}): {response.text}")
                    # Si le yard est plein, on s'arrête
                    if response.status_code == 400 and "Yard" in response.text:
                        print("🛑 Le Yard semble plein. Arrêt du streaming.")
                        break
            except requests.exceptions.ConnectionError:
                print("🚨 API injoignable. Tentative de reconnexion dans 5 secondes...")
                time.sleep(5)
                continue
                
            # Délai aléatoire entre 1 et 3 secondes pour simuler un vrai flux
            time.sleep(random.uniform(1.0, 3.0))
            
    except KeyboardInterrupt:
        print(f"\n🛑 Streaming arrêté manuellement. {container_count} conteneurs placés.")

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
