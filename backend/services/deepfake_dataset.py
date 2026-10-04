"""
PyTorch Dataset and DataLoader infrastructure for Real Deepfake Training/Evaluation.
Designed primarily for datasets derived from standard benchmarks (e.g., FaceForensics++).
"""

import os
import re
import collections
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, UnidentifiedImageError
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms

def extract_video_id(filename: str) -> str:
    """
    Extract a base video ID from a frame filename to prevent data leakage.
    FaceForensics++ convention: e.g. '001_003_frame001.png' -> video_id '001_003'
    Fallback: Assume the filename structure separates video ID and frame by an underscore.
    If no underscore exists, the whole filename (minus extension) is the video ID.
    """
    basename = os.path.splitext(os.path.basename(filename))[0]

    # Common format: {video_id}_frame{num} or {video_id}_{frame}
    match = re.match(r'^(.*?)_?(?:frame|f)?\d+$', basename, re.IGNORECASE)
    if match and match.group(1):
        return match.group(1)

    return basename

class DeepfakeDataset(Dataset):
    """
    PyTorch Dataset for real-world deepfake classification.
    Expects a standard layout if provided directly:
        <dataset_dir>/
            real/
                vid1_frame1.jpg
                vid1_frame2.jpg
            fake/
                vid2_frame1.jpg
                ...
    """

    def __init__(
        self,
        samples: List[Tuple[str, int]],
        transform: Optional[transforms.Compose] = None,
        target_size: Tuple[int, int] = (128, 128) # Matches current CNN architecture size
    ):
        self.samples = samples
        self.transform = transform
        self.target_size = target_size

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        filepath, label = self.samples[idx]

        try:
            img = Image.open(filepath).convert("RGB")
        except Exception:
            # Fallback to an empty array to prevent crashing mid-training
            # Validation should catch these before this point.
            img = Image.new("RGB", self.target_size, (0, 0, 0))

        if self.transform:
            img_tensor = self.transform(img)
        else:
            # Default transformation matching the current DeepfakeCNN normalization
            default_t = transforms.Compose([
                transforms.Resize(self.target_size),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            img_tensor = default_t(img)

        return img_tensor, label


def scan_and_validate_dataset(dataset_dir: str) -> Tuple[List[Tuple[str, int]], Dict[str, Any]]:
    """
    Scans the directory for valid images, handles class extraction, and reports validation stats.
    Returns:
        samples (List of (filepath, class_label))
        stats (Dict of validation statistics)
    """
    real_dir = os.path.join(dataset_dir, "real")
    fake_dir = os.path.join(dataset_dir, "fake")

    if not (os.path.exists(real_dir) or os.path.exists(fake_dir)):
        raise FileNotFoundError(f"Deepfake dataset structure missing at {dataset_dir}. Expected 'real' and 'fake' subdirectories.")

    valid_samples = []
    stats = {
        'total_files_scanned': 0,
        'corrupted_files': 0,
        'unsupported_formats': 0,
        'real_count': 0,
        'fake_count': 0,
        'video_ids_count': 0
    }

    allowed_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

    def process_dir(directory: str, label: int):
        if not os.path.exists(directory):
            return

        for root, _, files in os.walk(directory):
            for file in files:
                stats['total_files_scanned'] += 1
                ext = os.path.splitext(file)[1].lower()

                if ext not in allowed_exts:
                    stats['unsupported_formats'] += 1
                    continue

                filepath = os.path.join(root, file)

                # Image Validation
                try:
                    with Image.open(filepath) as img:
                        img.verify()

                    valid_samples.append((filepath, label))
                    if label == 0:
                        stats['real_count'] += 1
                    else:
                        stats['fake_count'] += 1
                except (IOError, SyntaxError, UnidentifiedImageError):
                    stats['corrupted_files'] += 1

    process_dir(real_dir, 0)
    process_dir(fake_dir, 1)

    video_ids = set([extract_video_id(f[0]) for f in valid_samples])
    stats['video_ids_count'] = len(video_ids)

    return valid_samples, stats


def create_leak_free_splits(
    samples: List[Tuple[str, int]],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42
) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]], List[Tuple[str, int]]]:
    """
    Split the dataset into train/val/test by VIDEO ID, not by unique frame.
    This guarantees that frames from the exact same source video do not straddle
    Train and Validation sets, strictly preventing data leakage.
    """
    if not samples:
        return [], [], []

    # Map video_id -> list of corresponding samples
    video_to_samples = collections.defaultdict(list)
    for filepath, label in samples:
        vid_id = extract_video_id(filepath)
        video_to_samples[vid_id].append((filepath, label))

    # Group video IDs by target class to ensure balanced split per class
    # Approach: Video ID label is primarily its mode label.
    video_class_map = collections.defaultdict(list)
    for vid, samps in video_to_samples.items():
        # majority label for video
        labels = [s[1] for s in samps]
        maj_label = max(set(labels), key=labels.count)
        video_class_map[maj_label].append(vid)

    rng = np.random.RandomState(seed)

    train_samples, val_samples, test_samples = [], [], []

    for label, vids in video_class_map.items():
        rng.shuffle(vids)
        total_vids = len(vids)

        train_end = max(1, int(round(total_vids * train_ratio))) if total_vids > 2 else int(total_vids * train_ratio)
        val_end = train_end + max(1, int(round(total_vids * val_ratio))) if total_vids > 2 else train_end + int(total_vids * val_ratio)

        train_vids = vids[:train_end]
        val_vids = vids[train_end:val_end]
        test_vids = vids[val_end:]

        for vid in train_vids:
            train_samples.extend(video_to_samples[vid])
        for vid in val_vids:
            val_samples.extend(video_to_samples[vid])
        for vid in test_vids:
            test_samples.extend(video_to_samples[vid])

    return train_samples, val_samples, test_samples


def get_deepfake_dataloaders(
    dataset_dir: str,
    batch_size: int = 32,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42
) -> Tuple[Optional[DataLoader], Optional[DataLoader], Optional[DataLoader], Dict[str, Any]]:
    """
    Core function to retrieve robust dataloaders for real dataset modeling.
    Returns (train_loader, val_loader, test_loader, validation_stats).
    """
    try:
        samples, stats = scan_and_validate_dataset(dataset_dir)

        if not samples:
            stats['error'] = "Dataset directory exists but contained no valid, uncorrupted images."
            return None, None, None, stats

        train_s, val_s, test_s = create_leak_free_splits(
            samples, train_ratio=train_ratio, val_ratio=val_ratio, seed=seed
        )

        stats['train_samples'] = len(train_s)
        stats['val_samples'] = len(val_s)
        stats['test_samples'] = len(test_s)

        # Standard transformations - Training gets basic augmentation
        train_transform = transforms.Compose([
            transforms.Resize((128, 128)),
            # Adding slight rotation and horizontal flip to prevent overfitting
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomApply([transforms.RandomRotation(15)], p=0.3),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        eval_transform = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        train_loader = DataLoader(DeepfakeDataset(train_s, transform=train_transform), batch_size=batch_size, shuffle=True, drop_last=True)
        val_loader = DataLoader(DeepfakeDataset(val_s, transform=eval_transform), batch_size=batch_size, shuffle=False)
        test_loader = DataLoader(DeepfakeDataset(test_s, transform=eval_transform), batch_size=batch_size, shuffle=False)

        return train_loader, val_loader, test_loader, stats

    except FileNotFoundError as e:
        return None, None, None, {'error': str(e)}
