import os
import shutil
import tempfile
import sys
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.deepfake_dataset import extract_video_id, create_leak_free_splits, scan_and_validate_dataset

def test_video_id_extraction():
    print("Testing Video ID Extraction...")
    assert extract_video_id("001_003_frame001.png") == "001_003"
    assert extract_video_id("vid1_f10.jpg") == "vid1"
    assert extract_video_id("completely_random_name.webp") == "completely_random_name"
    assert extract_video_id("001_frame001.jpg") == "001"
    print("[OK] Video ID extraction passed")

def test_dataset_scanning_and_leakage():
    print("\nTesting Dataset Scanning and Anti-Leakage Splits...")
    # Create mock dataset
    temp_dir = tempfile.mkdtemp()
    try:
        real_dir = os.path.join(temp_dir, "real")
        fake_dir = os.path.join(temp_dir, "fake")
        os.makedirs(real_dir)
        os.makedirs(fake_dir)

        def create_mock_img(path):
            img = Image.new("RGB", (10, 10), (255, 0, 0))
            img.save(path)

        # Create 3 real videos, 5 frames each
        for v in range(1, 4):
            for f in range(5):
                create_mock_img(os.path.join(real_dir, f"real_vid{v}_frame{f}.jpg"))

        # Create 3 fake videos, 5 frames each
        for v in range(1, 4):
            for f in range(5):
                create_mock_img(os.path.join(fake_dir, f"fake_vid{v}_frame{f}.jpg"))

        # Scrape and validate
        samples, stats = scan_and_validate_dataset(temp_dir)

        assert stats['real_count'] == 15
        assert stats['fake_count'] == 15
        assert stats['video_ids_count'] == 6 # real_vid1-3, fake_vid1-3
        assert stats['corrupted_files'] == 0

        # Test splits
        train_s, val_s, test_s = create_leak_free_splits(samples, train_ratio=0.33, val_ratio=0.33, seed=42)

        def get_vids_from_split(split):
            return set([extract_video_id(s[0]) for s in split])

        train_vids = get_vids_from_split(train_s)
        val_vids = get_vids_from_split(val_s)
        test_vids = get_vids_from_split(test_s)

        # Guarantee NO LEAKAGE (No intersection between train/val/test video IDs)
        assert len(train_vids.intersection(val_vids)) == 0, "Leakage between train and val!"
        assert len(train_vids.intersection(test_vids)) == 0, "Leakage between train and test!"
        assert len(val_vids.intersection(test_vids)) == 0, "Leakage between val and test!"

        # In a very small dataset with strict class grouping,
        # ensure that every single split got exactly its frames together.
        for t in train_vids:
            # Each video had 5 frames
            count = sum(1 for s in train_s if extract_video_id(s[0]) == t)
            assert count == 5

        print("[OK] Dataset scanning and valid file metrics passed")
        print("[OK] Strict Video-ID anti-leakage splitting passed")
        print(f"Total samples: {len(samples)} | Train: {len(train_s)} | Val: {len(val_s)} | Test: {len(test_s)}")

    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    print("=== Running Dataset & Leakage Protection Tests ===")
    test_video_id_extraction()
    test_dataset_scanning_and_leakage()
    print("=== All Dataset Tests Passed ===")