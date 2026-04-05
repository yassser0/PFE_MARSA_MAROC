import csv
import random
from datetime import datetime, timedelta

def generate_dwell_test_data(filename="dataset_dwell_2000.csv", count=2000):
    # Reference time: now (2026-04-05)
    now = datetime(2026, 4, 5, 12, 0, 0)
    
    # container types and sizes
    types = ["import", "export", "transshipment"]
    type_weights = [0.5, 0.35, 0.15]
    sizes = [20, 40]
    size_weights = [0.4, 0.6]
    
    prefixes = ["MSCU", "CMAU", "MRKU", "TCKU", "TLLU"]
    
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Header matching the system's expectations
        writer.writerow(["id", "size", "weight", "departure_time", "type", "slot"])
        
        for i in range(count):
            c_id = f"{random.choice(prefixes)}{random.randint(1000000, 9999999)}"
            c_size = random.choices(sizes, weights=size_weights)[0]
            c_type = random.choices(types, weights=type_weights)[0]
            
            # Weight based on size/type (realistic ranges)
            if c_type == "import":
                weight = round(random.uniform(10, 28), 1)
            elif c_type == "export":
                weight = round(random.uniform(5, 25), 1)
            else: # transshipment
                weight = round(random.uniform(8, 30), 1)
            
            # Adjust weight for 40ft
            if c_size == 40 and weight < 15:
                weight += 10
                
            # Dwell time distribution (days in the future)
            # 20% leave soon (1-3 days)
            # 50% leave mid-term (4-12 days)
            # 30% leave long-term (13-30 days)
            rand_val = random.random()
            if rand_val < 0.2:
                days_ahead = random.uniform(1, 3)
            elif rand_val < 0.7:
                days_ahead = random.uniform(4, 12)
            else:
                days_ahead = random.uniform(13, 30)
                
            departure = now + timedelta(days=days_ahead)
            departure_str = departure.strftime("%Y-%m-%dT%H:%M:%S")
            
            # No slot specified for "arrivals" (to be optimized)
            writer.writerow([c_id, c_size, weight, departure_str, c_type, ""])

    print(f"✅ Successfully generated {count} containers in {filename}")

if __name__ == "__main__":
    generate_dwell_test_data()
