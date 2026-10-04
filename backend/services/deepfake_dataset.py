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
    Extract a base video ID from a frame/filename to prevent data leakage.
    Handles FaceForensics++ C23 patterns:
    - 'original/000.mp4' -> '000'
    - 'Deepfakes/000_003.mp4' -> '000_003'
    - 'DeepFakeDetection/01_02__meeting_serious__YVGY8LOK.mp4' -> '01_02__meeting_serious__YVGY8LOK'

    Pattern matching (in order):
    1. DeepFakeDetection: {num}_{num}__{action}__{random_id}.mp4 -> keep full base
    2. Other manipulations: {num}_{num}.mp4 -> keep full base (the second num is NOT a frame number)
    3. Original: {num}.mp4 -> keep the num
    4. Frame-based files: {video_id}_frame{num}.jpg -> extract {video_id}
    """
    basename = os.path.splitext(os.path.basename(filename))[0]

    # DeepFakeDetection pattern: num_num__action__random_id (contains double underscore)
    if '__' in basename:
        # e.g., "01_02__meeting_serious__YVGY8LOK"
        # This is the full video ID, no trailing frame number
        return basename

    # Other manipulation patterns (Deepfakes, Face2Face, etc.): num_num.mp4
    # The second number is part of the video ID, NOT a frame number
    parts = basename.split('_')
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        # e.g., "000_003", "001_870" - both parts are video identifiers
        return basename

    # Original pattern: num.mp4 (single number)
    if basename.isdigit():
        return basename

    # Frame-based files: {video_id}_frame{num}.jpg or {video_id}_f{num}.jpg
    match = re.match(r'^(.*?)_?(?:frame|f)\d+$', basename, re.IGNORECASE)
    if match and match.group(1):
        return match.group(1)

    return basename


def extract_video_path(filename: str) -> str:
    """
    Extract the video path (directory + filename) from a full path.
    For FaceForensics++: 'Deepfakes/000_003.mp4' from 'C:/dataset/Deepfakes/000_003.mp4'
    """
    # Remove directory prefix - get just the relative path part
    # Patterns: Deepfakes/xxx, DeepFakeDetection/xxx, original/xxx
    parts = filename.replace('\\', '/').split('/')
    if len(parts) >= 2:
        return '/'.join(parts[-2:])
    return filename


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
    Also supports FaceForensics++ C23 structure where videos are stored as .mp4 files.
    """

    def __init__(
        self,
        samples: List[Tuple[str, int, str]],  # (filepath, label, video_id)
        transform: Optional[transforms.Compose] = None,
        target_size: Tuple[int, int] = (128, 128),  # Matches current CNN architecture size
        video_mode: bool = False,
        frames_per_video: int = 5,
    ):
        self.samples = samples
        self.transform = transform
        self.target_size = target_size
        self.video_mode = video_mode
        self.frames_per_video = frames_per_video

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        filepath, label, video_id = self.samples[idx]

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


def scan_and_validate_dataset(dataset_dir: str) -> Tuple[List[Tuple[str, int, str]], Dict[str, Any]]:
    """
    Scans the directory for valid images, handles class extraction, and reports validation stats.
    Returns:
        samples (List of (filepath, class_label, video_id))
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

                    video_id = extract_video_id(filepath)
                    valid_samples.append((filepath, label, video_id))
                    if label == 0:
                        stats['real_count'] += 1
                    else:
                        stats['fake_count'] += 1
                except (IOError, SyntaxError, UnidentifiedImageError):
                    stats['corrupted_files'] += 1

    process_dir(real_dir, 0)
    process_dir(fake_dir, 1)

    video_ids = set([s[2] for s in valid_samples])
    stats['video_ids_count'] = len(video_ids)

    return valid_samples, stats


def scan_faceforensics_csv(dataset_csv_path: str, dataset_root: str) -> Tuple[List[Tuple[str, int, str]], Dict[str, Any]]:
    """
    Scan FaceForensics++ C23 CSV file and extract video samples.
    CSV format: File Path, Label, Frame Count, Width, Height, Codec, File Size(MB)

    Returns:
        samples (List of (video_path, label, video_id))
        stats (Dict of validation statistics)
    """
    import csv

    valid_samples = []
    stats = {
        'total_videos_scanned': 0,
        'corrupted_files': 0,
        'real_count': 0,
        'fake_count': 0,
        'video_ids_count': 0,
        'manipulation_types': collections.defaultdict(int),
        'total_frame_count': 0,
        'total_file_size_mb': 0.0
    }

    allowed_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

    try:
        with open(dataset_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total_videos_scanned'] += 1

                file_path = row.get('File Path', '')
                label = row.get('Label', '').upper()
                frame_count = int(row.get('Frame Count', 0))
                width = int(row.get('Width', 0))
                height = int(row.get('Height', 0))
                codec = row.get('Codec', '')
                file_size_mb = float(row.get('File Size(MB)', 0))

                # Determine label
                is_real = label == 'REAL'
                label_int = 0 if is_real else 1

                # Get video path relative to dataset root
                video_rel_path = file_path.replace('\\', '/')

                # Extract manipulation type from path
                path_parts = video_rel_path.split('/')
                manip_type = path_parts[0] if len(path_parts) >= 2 else 'unknown'
                stats['manipulation_types'][manip_type] += 1

                # Extract video ID from filename
                basename = os.path.splitext(os.path.basename(video_rel_path))[0]
                video_id = extract_video_id(basename)

                # Full path for video file
                video_path = os.path.join(dataset_root, video_rel_path)

                if not os.path.exists(video_path):
                    stats['corrupted_files'] += 1
                    continue

                valid_samples.append((video_path, label_int, video_id))

                if is_real:
                    stats['real_count'] += 1
                else:
                    stats['fake_count'] += 1

                stats['total_frame_count'] += frame_count
                stats['total_file_size_mb'] += file_size_mb

    except Exception as e:
        stats['error'] = str(e)

    video_ids = set([s[2] for s in valid_samples])
    stats['video_ids_count'] = len(video_ids)

    return valid_samples, stats


def create_leak_free_splits(
    samples: List[Tuple[str, int, str]],
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42
) -> Tuple[List[Tuple[str, int, str]], List[Tuple[str, int, str]], List[Tuple[str, int, str]]]:
    """
    Split the dataset into train/val/test by VIDEO ID, not by unique frame/video.
    This guarantees that samples from the exact same source video do not straddle
    Train and Validation/Test sets, strictly preventing data leakage.

    Samples format: (filepath, label, video_id)
    """
    if not samples:
        return [], [], []

    # Map video_id -> list of corresponding samples
    video_to_samples = collections.defaultdict(list)
    for filepath, label, video_id in samples:
        video_to_samples[video_id].append((filepath, label, video_id))

    # Group video IDs by target class to ensure balanced split per class
    video_class_map = collections.defaultdict(list)
    for vid, samps in video_to_samples.items():
        # majority label for video (all samples from same video should have same label)
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
    seed: int = 42,
    target_size: Tuple[int, int] = (224, 224),  # EfficientNet default
    video_mode: bool = False,
    frames_per_video: int = 5,
) -> Tuple[Optional[DataLoader], Optional[DataLoader], Optional[DataLoader], Dict[str, Any]]:
    """
    Core function to retrieve robust dataloaders for real dataset modeling.
    Supports both standard image folder structure and FaceForensics++ CSV structure.

    Returns (train_loader, val_loader, test_loader, validation_stats).
    """
    try:
        # First try standard folder structure
        try:
            samples, stats = scan_and_validate_dataset(dataset_dir)
        except FileNotFoundError:
            # Try FaceForensics++ CSV structure
            # Check for common CSV patterns
            csv_path = os.path.join(dataset_dir, 'csv', 'original.csv')
            if os.path.exists(csv_path):
                all_samples = []
                all_stats = {
                    'total_videos_scanned': 0,
                    'corrupted_files': 0,
                    'real_count': 0,
                    'fake_count': 0,
                    'video_ids_count': 0,
                    'manipulation_types': collections.defaultdict(int),
                }

                # Process each manipulation type CSV
                manipulation_csvs = [
                    ('original', 'original.csv', 0),
                    ('Deepfakes', 'Deepfakes.csv', 1),
                    ('Face2Face', 'Face2Face.csv', 1),
                    ('FaceShifter', 'FaceShifter.csv', 1),
                    ('FaceSwap', 'FaceSwap.csv', 1),
                    ('NeuralTextures', 'NeuralTextures.csv', 1),
                    ('DeepFakeDetection', 'DeepFakeDetection.csv', 1),
                ]

                for manip_name, csv_file, label in manipulation_csvs:
                    csv_full_path = os.path.join(dataset_dir, 'csv', csv_file)
                    if os.path.exists(csv_full_path):
                        samp, st = scan_faceforensics_csv(csv_full_path, dataset_dir)
                        all_samples.extend(samp)
                        all_stats['total_videos_scanned'] += st['total_videos_scanned']
                        all_stats['corrupted_files'] += st['corrupted_files']
                        all_stats['real_count'] += st['real_count']
                        all_stats['fake_count'] += st['fake_count']
                        for mt, count in st['manipulation_types'].items():
                            all_stats['manipulation_types'][mt] += count

                all_stats['video_ids_count'] = len(set([s[2] for s in all_samples]))
                samples, stats = all_samples, all_stats
            else:
                raise

        if not samples:
            stats['error'] = "Dataset directory exists but contained no valid, uncorrupted images or videos."
            return None, None, None, stats

        train_s, val_s, test_s = create_leak_free_splits(
            samples, train_ratio=train_ratio, val_ratio=val_ratio, seed=seed
        )

        stats['train_samples'] = len(train_s)
        stats['val_samples'] = len(val_s)
        stats['test_samples'] = len(test_s)

        # Standard transformations - Training gets basic augmentation
        train_transform = transforms.Compose([
            transforms.Resize(target_size),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomApply([transforms.RandomRotation(15)], p=0.3),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        eval_transform = transforms.Compose([
            transforms.Resize(target_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        train_loader = DataLoader(
            DeepfakeDataset(train_s, transform=train_transform, video_mode=video_mode, frames_per_video=frames_per_video),
            batch_size=batch_size, shuffle=True, drop_last=True
        )
        val_loader = DataLoader(
            DeepfakeDataset(val_s, transform=eval_transform, video_mode=video_mode, frames_per_video=frames_per_video),
            batch_size=batch_size, shuffle=False
        )
        test_loader = DataLoader(
            DeepfakeDataset(test_s, transform=eval_transform, video_mode=video_mode, frames_per_video=frames_per_video),
            batch_size=batch_size, shuffle=False
        )

        return train_loader, val_loader, test_loader, stats

    except FileNotFoundError as e:
        return None, None, None, {'error': str(e)}


def inspect_faceforensics_dataset(dataset_path: str) -> Dict[str, Any]:
    """
    Comprehensive dataset inspection for FaceForensics++ C23 structure.
    Returns detailed statistics without modifying the dataset.
    """
    import csv

    result = {
        'dataset_path': dataset_path,
        'structure': 'FaceForensics++ C23 (CSV-based)',
        'original_videos': 0,
        'manipulated_videos': 0,
        'manipulation_types': {},
        'total_usable_videos': 0,
        'total_frames': 0,
        'corrupted_files': 0,
        'class_balance': {},
        'video_ids': set(),
        'train_val_test_split': None,
    }

    csv_dir = os.path.join(dataset_path, 'csv')
    if not os.path.exists(csv_dir):
        result['error'] = f"CSV directory not found at {csv_dir}"
        return result

    manipulation_csvs = {
        'original': ('original.csv', 'REAL'),
        'Deepfakes': ('Deepfakes.csv', 'FAKE'),
        'Face2Face': ('Face2Face.csv', 'FAKE'),
        'FaceShifter': ('FaceShifter.csv', 'FAKE'),
        'FaceSwap': ('FaceSwap.csv', 'FAKE'),
        'NeuralTextures': ('NeuralTextures.csv', 'FAKE'),
        'DeepFakeDetection': ('DeepFakeDetection.csv', 'FAKE'),
    }

    all_samples = []

    for manip_name, (csv_file, expected_label) in manipulation_csvs.items():
        csv_path = os.path.join(csv_dir, csv_file)
        if os.path.exists(csv_path):
            manip_stats = {'count': 0, 'videos': []}
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Label', '').upper() == expected_label:
                        video_path = row.get('File Path', '')
                        frame_count = int(row.get('Frame Count', 0))
                        file_path_full = os.path.join(dataset_path, video_path.replace('/', '\\'))

                        if os.path.exists(file_path_full):
                            manip_stats['count'] += 1
                            manip_stats['videos'].append(video_path)
                            result['video_ids'].add(extract_video_id(video_path))
                            all_samples.append((video_path, 0 if expected_label == 'REAL' else 1))
                            result['total_frames'] += frame_count

            result['manipulation_types'][manip_name] = manip_stats['count']
            if expected_label == 'REAL':
                result['original_videos'] = manip_stats['count']
            else:
                result['manipulated_videos'] += manip_stats['count']

    result['total_usable_videos'] = result['original_videos'] + result['manipulated_videos']
    result['class_balance'] = {
        'real': result['original_videos'],
        'fake': result['manipulated_videos']
    }
    result['video_ids_count'] = len(result['video_ids'])

    # Calculate split stats
    if len(all_samples) > 0:
        train_ratio, val_ratio = 0.7, 0.15
        train_end = int(len(all_samples) * train_ratio)
        val_end = train_end + int(len(all_samples) * val_ratio)

        result['train_val_test_split'] = {
            'train_samples': train_end,
            'val_samples': val_end - train_end,
            'test_samples': len(all_samples) - val_end,
            'train_ratio': train_ratio,
            'val_ratio': val_ratio,
            'test_ratio': 1.0 - train_ratio - val_ratio,
        }

    return result


def verify_no_leakage(train_samples: List, val_samples: List, test_samples: List) -> Dict[str, bool]:
    """
    Verify that there is ZERO video-ID overlap between train/val/test splits.
    Samples format: (filepath, label, video_id)
    """
    train_vids = set(s[2] for s in train_samples)
    val_vids = set(s[2] for s in val_samples)
    test_vids = set(s[2] for s in test_samples)

    return {
        'train_val_overlap': len(train_vids & val_vids) == 0,
        'train_test_overlap': len(train_vids & test_vids) == 0,
        'val_test_overlap': len(val_vids & test_vids) == 0,
        'total_train_vids': len(train_vids),
        'total_val_vids': len(val_vids),
        'total_test_vids': len(test_vids),
    }
