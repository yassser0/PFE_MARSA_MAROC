import time
import json
import random
import requests
from datetime import datetime, timedelta

# Configuration de l'API
API_URL = "http://127.0.0.1:8000"
ENDPOINT = f"{API_URL}/containers/place"

# Configuration du simulateur
INTERVAL_SECONDS = 2  # Temps entre chaque arrivée de camion (en secondes)
TOTAL_CONTAINERS = 200 # Nombre total de conteneurs à envoyer
DELAY_DAYS_MIN = 1      # Jours min avant départ
DELAY_DAYS_MAX = 30     # Jours max avant départ

# Listes pour générer des attributs aléatoires réalistes
SIZES = [20, 40]
TYPES = ["import", "export", "transshipment"]
WEIGHT_MIN = 5.0
WEIGHT_MAX = 30.0

def generate_random_container() -> dict:
    """Génère un conteneur avec des caractéristiques aléatoires."""
    size = random.choice(SIZES)
    ctype = random.choice(TYPES)
    
    # Ex: Les conteneurs 40ft sont généralement plus lourds
    if size == 40:
        weight = round(random.uniform(15.0, 30.0), 1)
    else:
        weight = round(random.uniform(5.0, 25.0), 1)
        
    # Date de départ aléatoire dans le futur
    days_to_departure = random.randint(DELAY_DAYS_MIN, DELAY_DAYS_MAX)
    hours_to_departure = random.randint(0, 23)
    departure_dt = datetime.now() + timedelta(days=days_to_departure, hours=hours_to_departure)
    
    return {
        "size": size,
        "weight": weight,
        "type": ctype,
        "departure_time": departure_dt.isoformat()
    }

def run_producer(interactive: bool = False):
    """Démarre la boucle d'envoi en continu."""
    print(f"Démarrage du simulateur de flux : {TOTAL_CONTAINERS} conteneurs à générer.")
    if interactive:
        print("Mode INTERACTIF : Appuyez sur Entrée pour envoyer chaque conteneur.")
    else:
        print(f"Fréquence : 1 conteneur toutes les {INTERVAL_SECONDS} secondes.")
    print("-" * 50)
    
    success_count = 0
    
    for i in range(1, TOTAL_CONTAINERS + 1):
        if interactive:
            input(f"Appuyez sur Entrée pour envoyer le conteneur {i}/{TOTAL_CONTAINERS}...")
            
        payload = generate_random_container()
        
        try:
            # Envoi de la requête POST à l'API
            response = requests.post(ENDPOINT, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                cid = data.get("container_id", "Unknown")
                slot = data.get("best_slot", {})
                pos = slot.get("position_key", "Aucun")
                score = round(data.get("best_score", 0), 2)
                
                print(f"[{i}/{TOTAL_CONTAINERS}] ✅ Validé: {cid} ({payload['size']}ft, {payload['weight']}t) -> ({pos}) [Score:{score}]")
                success_count += 1
            else:
                error_msg = response.json().get('detail', 'Erreur Inconnue')
                print(f"[{i}/{TOTAL_CONTAINERS}] ❌ Échec : {error_msg}")
                
                # Si le yard est plein, on arrête
                if "Aucun slot disponible" in error_msg:
                    print("🛑 Le yard est plein. Fin de la simulation.")
                    break
                    
        except requests.exceptions.ConnectionError:
            print("🚨 ERREUR: L'API n'est pas accessible. Avez-vous lancé 'python main.py api' ?")
            break
            
        # Pause avant le prochain camion (seulement si non interactif)
        if not interactive:
            time.sleep(INTERVAL_SECONDS)
        
    print("-" * 50)
    print(f"🏁 Simulation terminée. {success_count}/{TOTAL_CONTAINERS} conteneurs placés avec succès.")

if __name__ == "__main__":
    try:
        print(" PRODUCER - GÉNÉRATEUR DE FLUX")
        print("-" * 30)
        
        # Demander si on veut réinitialiser le yard
        reset_choice = input("🔄 Réinitialiser le yard (effacer les conteneurs existants) ? (o/N) : ").lower()
        if reset_choice == 'o':
            print("🧹 Nettoyage du yard...")
            try:
                requests.post(f"{API_URL}/yard/init", json={"blocks": 4, "rows": 10, "max_height": 4})
                time.sleep(1)
            except requests.exceptions.ConnectionError:
                print("🚨 Impossible de se connecter à l'API pour réinitialiser.")
        else:
            print("Conservation des conteneurs existants.")

        # Demander le mode de fonctionnement
        mode_choice = input(" Mode interactif (pas à pas) ? (O/n) : ").lower()
        is_interactive = mode_choice != 'n'
        
        run_producer(interactive=is_interactive)
    except KeyboardInterrupt:
        print("\nSimulation arrêtée manuellement.")
