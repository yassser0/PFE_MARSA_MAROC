import sys
import os

# Add the project root to sys.path to import models
sys.path.append(os.getcwd())

from models.yard import Slot

def test_localization():
    examples = [
        {"input": ("K", 19, 1, 4), "expected": "K019A04"},
        {"input": ("CZ", 72, 2, 1), "expected": "CZ072B01"},
        {"input": ("BY", 62, 1, 3), "expected": "BY062A03"},
        {"input": ("BX", 1, 1, 5), "expected": "BX001A05"},
    ]

    print("--- Testing Formatting ---")
    for ex in examples:
        block, bay, row, tier = ex["input"]
        slot = Slot(block_id=block, bay=bay, row=row, tier=tier)
        res = slot.localization
        print(f"Input: {ex['input']} -> Result: {res} | Expected: {ex['expected']}")
        assert res == ex["expected"], f"Formatting failed for {ex['input']}"

    print("\n--- Testing Parsing ---")
    for ex in examples:
        loc = ex["expected"]
        res = Slot.from_localization(loc)
        expected_components = {
            "block_id": ex["input"][0],
            "bay": ex["input"][1],
            "row": ex["input"][2],
            "tier": ex["input"][3]
        }
        print(f"Input: {loc} -> Result: {res} | Expected: {expected_components}")
        assert res == expected_components, f"Parsing failed for {loc}"

    print("\n--- Testing Round-trip ---")
    test_loc = "BY062C04"
    components = Slot.from_localization(test_loc)
    slot = Slot(**components)
    assert slot.localization == test_loc
    print(f"Round-trip success for {test_loc}")

    print("\nAll tests passed successfully!")

if __name__ == "__main__":
    try:
        test_localization()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
