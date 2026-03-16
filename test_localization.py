import sys
import os

# Add the project root to sys.path to import models
sys.path.append(os.getcwd())

from models.yard import Slot

def test_localization():
    examples = [
        {"input": ("K", 19, 1, 4), "expected": "K-019-A-04"},
        {"input": ("CZ", 72, 2, 1), "expected": "CZ-072-B-01"},
        {"input": ("BY", 62, 1, 3), "expected": "BY-062-A-03"},
        {"input": ("BX", 1, 1, 5), "expected": "BX-001-A-05"},
    ]

    print("--- Testing Formatting ---")
    for ex in examples:
        block, bay, row, tier = ex["input"]
        slot = Slot(block_id=block, bay=bay, row=row, tier=tier)
        res = slot.localization
        print(f"Input: {ex['input']} -> Result: {res} | Expected: {ex['expected']}")
        assert res == ex["expected"], f"Formatting failed for {ex['input']}"

    print("\n--- Testing Parsing (Strict hyphenated) ---")
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

    print("\n--- Testing Parsing (Flexibility without hyphens) ---")
    flexible_loc = "B001C01"
    res = Slot.from_localization(flexible_loc)
    expected = {"block_id": "B", "bay": 1, "row": 3, "tier": 1}
    print(f"Input: {flexible_loc} -> Result: {res} | Expected: {expected}")
    assert res == expected

    print("\n--- Testing Round-trip ---")
    test_loc = "BY-062-C-04"
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
