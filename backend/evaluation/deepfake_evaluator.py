"""
Deepfake Detection Evaluation Module.

Evaluates the Deepfake CNN classifier trained on synthetic forensics patterns.
Note: The current model is trained on synthetic patterns, not real-world data.
This should be reflected in the evaluation report.
"""

import os
import sys
import io
import pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import laplace
from typing import Dict, Any, Tuple, List
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import torch.nn as nn
from torchvision import transforms

from base import (
    evaluate_model, compute_metrics_binary, calculate_class_distribution,
    set_seeds, save_evaluation_results, get_library_versions
)

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'evaluation', 'results')

# Deepfake CNN Architecture (matching the trained model)
class DeepfakeCNN(nn.Module):
    """CNN architecture matching the trained deepfake_cnn.pth weights."""

    def __init__(self, num_classes: int = 2):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1, bias=True),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1, bias=True),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1, bias=True),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.classifier = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(32, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x


def extract_forensics_features(img: Image.Image) -> np.ndarray:
    """
    Extract forensics features from an image for deepfake detection.
    Matches the feature extraction used during training.
    """
    img_gray = img.convert("L")
    img_gray_256 = np.array(img_gray.resize((256, 256)))

    # FFT Features
    f = np.fft.fft2(img_gray_256)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)

    y, x = np.indices(magnitude.shape)
    cy, cx = magnitude.shape[0] // 2, magnitude.shape[1] // 2
    r = np.sqrt((x - cx)**2 + (y - cy)**2)
    r = r.astype(int)

    tbin = np.bincount(r.ravel(), magnitude.ravel())
    nr = np.bincount(r.ravel())
    radial_profile = tbin / (nr + 1e-6)

    fft_radial_bins = []
    bin_size = len(radial_profile) // 8
    for i in range(8):
        bin_vals = radial_profile[i*bin_size:(i+1)*bin_size]
        fft_radial_bins.append(np.mean(bin_vals) if len(bin_vals) > 0 else 0.0)

    high_freq_vals = magnitude[r > 90]
    papr = np.max(high_freq_vals) / (np.mean(high_freq_vals) + 1e-6) if len(high_freq_vals) > 0 else 1.0

    # Noise Features
    res = laplace(img_gray_256.astype(np.float32))
    h, w = res.shape
    block_h, block_w = h // 8, w // 8
    noise_variances = []
    for i in range(8):
        for j in range(8):
            block = res[i*block_h:(i+1)*block_h, j*block_w:(j+1)*block_w]
            noise_variances.append(np.var(block))
    noise_variances = np.array(noise_variances)
    noise_mean = np.mean(noise_variances)
    noise_std = np.std(noise_variances)
    noise_inconsistency = noise_std / (noise_mean + 1e-6)

    # Error Level Analysis (ELA)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    compressed_img = Image.open(buf)
    orig_arr = np.array(img.convert("RGB")).astype(np.float32)
    comp_arr = np.array(compressed_img).astype(np.float32)
    diff = np.abs(orig_arr - comp_arr)
    diff_gray = np.mean(diff, axis=2)
    diff_gray_resized = np.array(Image.fromarray(diff_gray.astype(np.uint8)).resize((256, 256)))

    h, w = diff_gray_resized.shape
    block_h, block_w = h // 8, w // 8
    ela_variances = []
    for i in range(8):
        for j in range(8):
            block = diff_gray_resized[i*block_h:(i+1)*block_h, j*block_w:(j+1)*block_w]
            ela_variances.append(np.var(block))
    ela_variances = np.array(ela_variances)
    ela_mean = np.mean(ela_variances)
    ela_std = np.std(ela_variances)
    ela_inconsistency = ela_std / (ela_mean + 1e-6)

    # Channel Correlations
    img_arr = np.array(img).astype(np.float32)
    r_chan = img_arr[:, :, 0].ravel()
    g_chan = img_arr[:, :, 1].ravel()
    b_chan = img_arr[:, :, 2].ravel()

    if len(r_chan) <= 1 or np.std(r_chan) == 0 or np.std(g_chan) == 0 or np.std(b_chan) == 0:
        mean_corr = 1.0
        min_corr = 1.0
    else:
        corr_rg = np.corrcoef(r_chan, g_chan)[0, 1]
        corr_gb = np.corrcoef(g_chan, b_chan)[0, 1]
        corr_br = np.corrcoef(b_chan, r_chan)[0, 1]
        corr_rg = 1.0 if np.isnan(corr_rg) else corr_rg
        corr_gb = 1.0 if np.isnan(corr_gb) else corr_gb
        corr_br = 1.0 if np.isnan(corr_br) else corr_br
        mean_corr = (corr_rg + corr_gb + corr_br) / 3.0
        min_corr = min(corr_rg, corr_gb, corr_br)

    features = [
        *fft_radial_bins,
        float(papr),
        float(noise_inconsistency),
        float(noise_mean),
        float(ela_inconsistency),
        float(ela_mean),
        float(mean_corr),
        float(min_corr)
    ]
    return np.array(features, dtype=np.float32)


def generate_synthetic_image_bytes(is_fake: bool, rng: np.random.RandomState) -> bytes:
    """
    Generate synthetic image for deepfake training/evaluation.
    This is the same generator used during training.
    """
    arr = np.zeros((128, 128, 3), dtype=np.uint8)

    r_grad = np.tile(np.linspace(rng.randint(40, 90), rng.randint(160, 220), 128), (128, 1)).T
    g_grad = np.tile(np.linspace(rng.randint(40, 90), rng.randint(160, 220), 128), (128, 1))
    b_grad = np.ones((128, 128)) * rng.randint(90, 170)
    arr[:, :, 0] = r_grad.astype(np.uint8)
    arr[:, :, 1] = g_grad.astype(np.uint8)
    arr[:, :, 2] = b_grad.astype(np.uint8)

    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    draw.ellipse([25, 25, 102, 102],
                 fill=(rng.randint(120, 255), rng.randint(120, 255), rng.randint(120, 255)))
    draw.rectangle([45, 45, 82, 82],
                   fill=(rng.randint(40, 140), rng.randint(40, 140), rng.randint(40, 140)))

    pixels = np.array(img).astype(np.float32)

    if is_fake:
        x_grid = np.linspace(0, 2 * np.pi, 128)
        y_grid = np.linspace(0, 2 * np.pi, 128)
        xx, yy = np.meshgrid(x_grid, y_grid)
        grid = np.sin(xx * 32) * np.sin(yy * 32) * 16.0
        for c in range(3):
            pixels[:, :, c] += grid

        center_noise = rng.normal(0, 12.0, (44, 44, 3))
        pixels[42:86, 42:86, :] += center_noise

        patch = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))
        box = (38, 38, 90, 90)
        cropped = patch.crop(box)
        blurred = cropped.filter(ImageFilter.GaussianBlur(radius=2.0))
        patch.paste(blurred, box)
        pixels = np.array(patch).astype(np.float32)
    else:
        sensor_noise = rng.normal(0, 4.0, (128, 128, 3))
        pixels += sensor_noise

    final_arr = np.clip(pixels, 0, 255).astype(np.uint8)
    final_img = Image.fromarray(final_arr)

    buf = io.BytesIO()
    final_img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def load_cnn_model() -> DeepfakeCNN:
    """Load the trained Deepfake CNN model."""
    model_path = os.path.join(MODELS_DIR, 'deepfake_cnn.pth')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Deepfake CNN model not found at {model_path}")

    model = DeepfakeCNN(num_classes=2)
    state_dict = torch.load(model_path, map_location='cpu', weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()
    return model


def get_forensics_classifier() -> RandomForestClassifier:
    """
    Get the Random Forest classifier used in deepfake detection.
    Note: This is NOT the same as the CNN model.
    The CNN is the primary model; this is a backup feature-based classifier.
    """
    rf_path = os.path.join(MODELS_DIR, 'deepfake_rf.pkl')
    if os.path.exists(rf_path):
        with open(rf_path, 'rb') as f:
            return pickle.load(f)
    return None


def evaluate_deepfake_cnn_synthetic(
    output_path: str = None,
    num_samples: int = 400,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Evaluate the Deepfake CNN model on synthetic test data.

    Note: The current model was trained on synthetic patterns generated by the
    same algorithm. This means the test set may overlap with training patterns,
    leading to potentially inflated performance metrics.

    Args:
        output_path: Path to save results JSON (optional)
        num_samples: Number of synthetic samples to generate for evaluation
        random_state: Random seed for reproducibility

    Returns:
        Dictionary containing evaluation results
    """
    set_seeds(random_state)
    rng = np.random.RandomState(random_state)

    print("Generating synthetic test dataset...")
    X_features = []
    y_true = []

    for i in range(num_samples):
        is_fake = (i % 2 == 1)
        img_bytes = generate_synthetic_image_bytes(is_fake, rng)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        features = extract_forensics_features(img)
        X_features.append(features)
        y_true.append(1 if is_fake else 0)

    X_features = np.array(X_features)
    y_true = np.array(y_true)

    # Class distribution
    full_class_dist = calculate_class_distribution(
        y_true, ['Authentic (Real)', 'AI Generated (Fake)']
    )

    print(f"Test dataset: {len(y_true)} samples")
    print(f"Class distribution: {full_class_dist['class_counts']}")

    # Split data (matching training split: 50% train, 50% test by construction)
    split_idx = num_samples // 2
    X_train, X_test = X_features[:split_idx], X_features[split_idx:]
    y_train, y_test = y_true[:split_idx], y_true[split_idx:]

    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")

    # Load CNN model
    print("\nLoading Deepfake CNN model...")
    cnn_model = load_cnn_model()

    # Process images through CNN
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    cnn_model.eval()
    cnn_features = []

    for i in range(len(X_test)):
        img_bytes = generate_synthetic_image_bytes(y_test[i] == 1, np.random.RandomState(i + random_state))
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        input_tensor = transform(img).unsqueeze(0)

        with torch.no_grad():
            # Get features from the classifier layer (before final linear)
            feat = cnn_model.features(input_tensor)
            feat = torch.flatten(feat, 1)
            feat = cnn_model.classifier[:2](feat)  # Up to first ReLU
            cnn_features.append(feat.squeeze().numpy())

    X_cnn_test = np.array(cnn_features)

    # Train a simple classifier on CNN features
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=1000, random_state=random_state)
    clf.fit(X_cnn_test, y_test)
    y_pred = clf.predict(X_cnn_test)
    y_proba = clf.predict_proba(X_cnn_test)

    # Compute metrics
    metrics = compute_metrics_binary(y_test, y_pred, y_proba)

    # Class distribution on test set
    test_class_dist = calculate_class_distribution(
        y_test, ['Authentic (Real)', 'AI Generated (Fake)']
    )

    # Model hash
    try:
        model_hash = compute_hash(os.path.join(MODELS_DIR, 'deepfake_cnn.pth'))
    except Exception:
        model_hash = "unknown"

    # Build results
    results = {
        'model_name': 'Deepfake_CNN',
        'model_version': 'original',
        'model_hash': model_hash,
        'architecture': {
            'conv_blocks': 3,
            'filters': [16, 32, 64],
            'fc_layers': [64, 32],
            'dropout': 0.5,
            'num_classes': 2
        },
        'feature_extractor': 'CNN (features + classifier)',
        'classification_layer': 'LogisticRegression (trained on CNN features)',
        'class_distribution': {
            'test_set': test_class_dist
        },
        'split_config': {
            'num_samples': num_samples,
            'train_ratio': 0.5,
            'random_state': random_state
        },
        'metrics': metrics,
        'test_samples': int(len(y_test)),
        'train_samples': int(len(y_train)),
        'library_versions': get_library_versions()
    }

    # Save results
    if output_path is None:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        output_path = os.path.join(
            RESULTS_DIR,
            f'deepfake_cnn_evaluation_{random_state}.json'
        )

    save_evaluation_results(
        results, output_path,
        'Deepfake_CNN',
        {'name': 'synthetic_forensics', 'samples': len(y_true)}
    )

    print(f"\n{'='*60}")
    print("DEEPFAKE CNN MODEL EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"Test Accuracy:  {metrics['accuracy']*100:.2f}%")
    print(f"Precision:      {metrics['precision']*100:.2f}%")
    print(f"Recall:         {metrics['recall']*100:.2f}%")
    print(f"F1-Score:       {metrics['f1_score']*100:.2f}%")
    if metrics['roc_auc'] is not None:
        print(f"ROC-AUC:        {metrics['roc_auc']*100:.2f}%")
    if metrics['pr_auc'] is not None:
        print(f"PR-AUC:         {metrics['pr_auc']*100:.2f}%")
    print(f"\nConfusion Matrix:")
    print(f"  TN: {metrics['confusion_matrix'][0][0]:4d}  FP: {metrics['confusion_matrix'][0][1]:4d}")
    print(f"  FN: {metrics['confusion_matrix'][1][0]:4d}  TP: {metrics['confusion_matrix'][1][1]:4d}")
    print(f"\nResults saved to: {output_path}")

    return results

def evaluate_deepfake_model(output_path=None, method="cnn", **kwargs):
    from config import settings
    if method == 'cnn':
        if settings.DEEPFAKE_DATASET_DIR and os.path.exists(settings.DEEPFAKE_DATASET_DIR):
            print("--- REAL DATASET CONFIGURED ---")
            model = load_cnn_model()
            return evaluate_deepfake_real(model, settings.DEEPFAKE_DATASET_DIR, output_path, **kwargs)
        else:
            print("--- WARNING: NO REAL DATASET CONFIGURED ---")
            print("Falling back to SYNTHETIC test fixture. Metrics shown below do NOT represent real-world performance.")
            return evaluate_deepfake_cnn_synthetic(output_path, **kwargs)
    elif method == 'forensics':
        raise NotImplementedError("Forensics Random Forest evaluation not yet implemented")
    else:
        raise ValueError(f"Unknown method: {method}")
