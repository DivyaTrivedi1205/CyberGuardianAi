#!/usr/bin/env python3
"""
Dataset Inspection and Validation Tests for FaceForensics++ C23
"""

import os
import sys
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.deepfake_dataset import (
    inspect_faceforensics_dataset,
    verify_no_leakage,
    get_deepfake_dataloaders,
    scan_faceforensics_csv,
    extract_video_id,
)

DATASET_PATH = r"C:\Users\DIVYA\OneDrive\Desktop\Desktopp\Datasets\FaceForensics++_C23"


def test_video_id_extraction():
    """Test that video IDs are extracted correctly from various patterns."""
    print("=== Testing Video ID Extraction ===")

    test_cases = [
        ("original/000.mp4", "000"),
        ("Deepfakes/000_003.mp4", "000_003"),
        ("DeepFakeDetection/01_02__meeting_serious__YVGY8LOK.mp4", "01_02__meeting_serious__YVGY8LOK"),
        ("Face2Face/001_870.mp4", "001_870"),
        ("NeuralTextures/002_006.mp4", "002_006"),
    ]

    all_passed = True
    for filename, expected in test_cases:
        result = extract_video_id(filename)
        passed = result == expected
        all_passed = all_passed and passed
        status = "PASS" if passed else f"FAIL (got: {result})"
        print(f"  {filename} -> {result} [{status}]")

    print(f"Video ID extraction: {'ALL PASSED' if all_passed else 'SOME FAILED'}\n")
    return all_passed


def test_dataset_inspection():
    """Inspect the FaceForensics++ C23 dataset structure and statistics."""
    print("=== FaceForensics++ C23 Dataset Inspection ===")

    if not os.path.exists(DATASET_PATH):
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        return None

    result = inspect_faceforensics_dataset(DATASET_PATH)
    pprint(result)

    # Verify key statistics
    print("\n=== Verification ===")
    checks = []

    # Check manipulation types
    manip_types = result.get('manipulation_types', {})
    expected_types = ['original', 'Deepfakes', 'Face2Face', 'FaceShifter', 'FaceSwap', 'NeuralTextures', 'DeepFakeDetection']
    for mt in expected_types:
        count = manip_types.get(mt, 0)
        checks.append((f"  {mt}: {count} videos", count > 0))

    # Check class balance
    cb = result.get('class_balance', {})
    checks.append((f"  Original (REAL): {cb.get('real', 0)}", cb.get('real', 0) == 1000))
    checks.append((f"  Manipulated (FAKE): {cb.get('fake', 0)}", cb.get('fake', 0) == 6000))

    for msg, passed in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{msg} [{status}]")

    return result


def test_dataloader_loading():
    """Test that dataloaders can be created from the dataset."""
    print("\n=== Testing Dataloader Creation ===")

    if not os.path.exists(DATASET_PATH):
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        return None

    print(f"Loading dataset from: {DATASET_PATH}")

    try:
        train_dl, val_dl, test_dl, stats = get_deepfake_dataloaders(
            dataset_dir=DATASET_PATH,
            batch_size=32,
            train_ratio=0.7,
            val_ratio=0.15,
            seed=42,
            target_size=(224, 224),
            video_mode=False,
            frames_per_video=5,
        )

        print(f"\n=== Dataloader Stats ===")
        print(f"  Train samples: {stats.get('train_samples', 'N/A')}")
        print(f"  Validation samples: {stats.get('val_samples', 'N/A')}")
        print(f"  Test samples: {stats.get('test_samples', 'N/A')}")
        print(f"  Total usable videos: {stats.get('video_ids_count', 'N/A')}")
        print(f"  Class balance: REAL={stats.get('real_count', 0)}, FAKE={stats.get('fake_count', 0)}")

        if train_dl is None:
            print(f"  ERROR: train_loader is None")
            print(f"  Stats: {stats}")
            return None

        print(f"\n=== DataLoader Verification ===")
        print(f"  Train loader batches: {len(train_dl)}")
        print(f"  Val loader batches: {len(val_dl)}")
        print(f"  Test loader batches: {len(test_dl)}")

        # Get one batch to verify
        for inputs, labels in train_dl:
            print(f"  Sample batch shape: inputs={inputs.shape}, labels={labels.shape}")
            print(f"  Sample labels: {labels[:10].tolist()}")
            break

        return {'train': train_dl, 'val': val_dl, 'test': test_dl, 'stats': stats}

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_leakage_prevention():
    """Test that video IDs are not leaked between splits."""
    print("\n=== Testing Video-ID Leakage Prevention ===")

    if not os.path.exists(DATASET_PATH):
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        return False

    try:
        train_dl, val_dl, test_dl, stats = get_deepfake_dataloaders(
            dataset_dir=DATASET_PATH,
            batch_size=32,
            train_ratio=0.7,
            val_ratio=0.15,
            seed=42,
        )

        if train_dl is None:
            print("  ERROR: Could not create dataloaders")
            return False

        # Get the underlying dataset from dataloaders to check video IDs
        # Note: DataLoader wraps the dataset, so we access through internal properties
        train_dataset = train_dl.dataset
        val_dataset = val_dl.dataset
        test_dataset = test_dl.dataset

        # Extract video IDs from each split
        train_vids = set(s[2] for s in train_dataset.samples)
        val_vids = set(s[2] for s in val_dataset.samples)
        test_vids = set(s[2] for s in test_dataset.samples)

        # Verify no overlap
        train_val_overlap = len(train_vids & val_vids)
        train_test_overlap = len(train_vids & test_vids)
        val_test_overlap = len(val_vids & test_vids)

        print(f"  Train unique videos: {len(train_vids)}")
        print(f"  Val unique videos: {len(val_vids)}")
        print(f"  Test unique videos: {len(test_vids)}")
        print(f"  Train-Val overlap: {train_val_overlap} (should be 0)")
        print(f"  Train-Test overlap: {train_test_overlap} (should be 0)")
        print(f"  Val-Test overlap: {val_test_overlap} (should be 0)")

        no_leakage = (train_val_overlap == 0 and
                      train_test_overlap == 0 and
                      val_test_overlap == 0)

        print(f"\nLeakage prevention: {'PASS' if no_leakage else 'FAIL'}")
        return no_leakage

    except Exception as e:
        print(f"ERROR during leakage test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all dataset inspection and validation tests."""
    print("=" * 60)
    print("FaceForensics++ C23 Dataset Inspection & Validation")
    print("=" * 60)
    print()

    results = {}

    # Test 1: Video ID extraction
    results['video_id_extraction'] = test_video_id_extraction()

    # Test 2: Dataset inspection
    results['dataset_inspection'] = test_dataset_inspection()

    # Test 3: Dataloader creation
    results['dataloader'] = test_dataloader_loading()

    # Test 4: Leakage prevention
    results['leakage'] = test_leakage_prevention()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test_name, result in results.items():
        if result is True:
            status = "PASS"
        elif result is False:
            status = "FAIL"
        elif result is None:
            status = "SKIPPED (missing dataset)"
        else:
            status = "PARTIAL"
        print(f"  {test_name}: {status}")

    all_passed = all(v is True for v in results.values() if v is not None)
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    return results


if __name__ == "__main__":
    main()
