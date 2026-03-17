import csv
import random
from datetime import datetime, timedelta

def generate_large_csv(filename, count=450):
    headers = ['id', 'weight', 'type', 'departure_time', 'size']
    types = ['import', 'export', 'transshipment']
    sizes = [20, 40]
    
    start_date = datetime.now() + timedelta(days=1)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i in range(1, count + 1):
            container_id = f"CNTR-{i:03d}"
            weight = round(random.uniform(5.0, 30.0), 1)
            ctype = random.choice(types)
            # Spread departure times over 30 days
            departure = start_date + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            size = random.choice(sizes)
            
            writer.writerow([
                container_id,
                weight,
                ctype,
                departure.strftime('%Y-%m-%dT%H:%M:%S'),
                size
            ])
    
    print(f"✅ Fichier {filename} généré avec {count} conteneurs.")

if __name__ == "__main__":
    generate_large_csv('c:\\PFE_MARSA_MAROC\\sample_containers.csv', 450)
