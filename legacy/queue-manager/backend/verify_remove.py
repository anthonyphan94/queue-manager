import requests
import sys

BASE_URL = "http://localhost:8000"

def test_remove():
    print("Testing Remove...")
    
    # 1. Add Tech
    res = requests.post(f"{BASE_URL}/techs", json={"name": "Temp Tech"})
    if res.status_code != 200:
        print("Add failed")
        sys.exit(1)
    tech_id = res.json()["id"]
    print(f"Added Temp Tech ID: {tech_id}")
    
    # 2. Verify exists
    res = requests.get(f"{BASE_URL}/techs")
    ids = [t["id"] for t in res.json()]
    if tech_id not in ids:
        print("Tech not found in list")
        sys.exit(1)
        
    # 3. Delete
    print(f"Deleting ID: {tech_id}")
    res = requests.delete(f"{BASE_URL}/techs/{tech_id}")
    if res.status_code != 200:
        print(f"Delete failed: {res.text}")
        sys.exit(1)
        
    # 4. Verify removed
    res = requests.get(f"{BASE_URL}/techs")
    ids = [t["id"] for t in res.json()]
    if tech_id in ids:
        print("FAIL: Tech still exists in list!")
        sys.exit(1)
        
    print("PASS: Tech removed")

if __name__ == "__main__":
    try:
        test_remove()
    except Exception as e:
        print(f"Exception: {e}")
        sys.exit(1)
