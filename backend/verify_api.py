import requests
import sys

BASE_URL = "http://localhost:8000"

def test_backend():
    print("Testing backend...")
    
    # 1. Add Techs
    techs = ["T1", "T2", "T3"]
    ids = []
    for name in techs:
        res = requests.post(f"{BASE_URL}/techs", json={"name": name})
        print(f"Add {name}: {res.status_code}")
        if res.status_code != 200:
            print(res.text)
            sys.exit(1)
        ids.append(res.json()["id"])
    
    print(f"Added IDs: {ids}")

    # 2. Reorder
    # Reverse order
    reversed_ids = ids[::-1]
    res = requests.post(f"{BASE_URL}/techs/reorder", json={"tech_ids": reversed_ids})
    print(f"Reorder: {res.status_code}")
    if res.status_code != 200:
        print(res.text)
        sys.exit(1)
        
    # 3. Verify Order
    res = requests.get(f"{BASE_URL}/techs")
    data = res.json()
    # Filter for our techs
    my_techs = [t for t in data if t["id"] in ids]
    # Check if order matches reversed_ids
    # Note: get_techs_sorted returns sorted by queue_position
    sorted_ids = [t["id"] for t in my_techs]
    
    print(f"Expected: {reversed_ids}")
    print(f"Actual:   {sorted_ids}")
    
    if sorted_ids == reversed_ids:
        print("PASS: Reorder verified")
    else:
        print("FAIL: Order mismatch")
        sys.exit(1)

if __name__ == "__main__":
    try:
        test_backend()
    except Exception as e:
        print(f"Exception: {e}")
        sys.exit(1)
