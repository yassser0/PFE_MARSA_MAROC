import requests
import json
from datetime import datetime, timedelta

API_URL = "http://127.0.0.1:8000"

def test_batch_upload():
    print("🚀 Testing Batch Upload with Custom IDs...")
    
    # 1. Initialize Yard
    print("🧹 Initializing Yard...")
    requests.post(f"{API_URL}/yard/init", json={"blocks": 4, "bays": 10, "rows": 3, "max_height": 4})
    
    # 2. Prepare Data
    now = datetime.now()
    data = [
        {
            "id": "CUSTOM-001",
            "size": 20,
            "weight": 15.5,
            "type": "import",
            "departure_time": (now + timedelta(days=5)).isoformat()
        },
        {
            "id": "CUSTOM-002",
            "size": 40,
            "weight": 22.0,
            "type": "export",
            "departure_time": (now + timedelta(days=10)).isoformat()
        }
    ]
    
    # 3. Call API
    print("📤 Sending batch data...")
    response = requests.post(f"{API_URL}/containers/place_batch", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success: {result['message']}")
        print(f"Stats: {result}")
        
        # 4. Verify IDs in Registry
        print("🔍 Verifying IDs in Yard...")
        yard_resp = requests.get(f"{API_URL}/yard/state")
        if yard_resp.status_code == 200:
            yard_state = yard_resp.json()
            # Depending on how yard state is returned, we check for our IDs
            # This is a basic check.
            found_ids = []
            for block in yard_state.get('blocks', {}).values():
                for stack in block.get('stacks', {}).values():
                    for slot in stack.get('slots', []):
                        if slot.get('container_id') in ["CUSTOM-001", "CUSTOM-002"]:
                            found_ids.append(slot['container_id'])
            
            if len(found_ids) == 2:
                print("🏆 Verification Successful: Both custom IDs found in the yard!")
            else:
                print(f"⚠️ Warning: Found {len(found_ids)}/2 IDs. Found: {found_ids}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_batch_upload()
