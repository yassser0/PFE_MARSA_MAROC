import csv
import os
import sys

# Ajouter le répertoire racine au path pour les imports
sys.path.append(os.getcwd())

from data_generator.generator import generate_containers

def main():
    print("Génération de 400 conteneurs valides...")
    containers = generate_containers(400)
    
    output_file = "containers_400.csv"
    
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header
        writer.writerow(["id", "size", "weight", "departure_time", "type"])
        
        for c in containers:
            writer.writerow([
                c.id,
                c.size,
                round(c.weight, 2),
                c.departure_time.strftime("%Y-%m-%d %H:%M:%S"),
                c.type.value
            ])
            
    print(f"Fichier '{output_file}' généré avec succès.")

if __name__ == "__main__":
    main()
