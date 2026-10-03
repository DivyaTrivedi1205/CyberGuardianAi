"""
Base evaluation framework for CyberGuardian ML models.
Provides reproducible evaluation with proper train/validation/test separation.
"""

import os
import json
import time
import hashlib
import random
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path

# Set random seeds for reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)


def set_seeds(seed: int = SEED) -> None:
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass  # torch not available, but that's OK for evaluation


def compute_hash(filepath: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_library_versions() -> Dict[str, str]:
    """Get versions of key libraries."""
    versions = {}
    try:
        import sklearn
        versions['sklearn'] = sklearn.__version__
    except ImportError:
        pass

    try:
        import xgboost
        versions['xgboost'] = xgboost.__version__
    except ImportError:
        pass

    try:
        import torch
        versions['torch'] = torch.__version__
    except ImportError:
        pass

    try:
        import pandas
        versions['pandas'] = pandas.__version__
    except ImportError:
        pass

    try:
        import numpy
        versions['numpy'] = numpy.__version__
    except ImportError:
        pass

    return versions


def compute_metrics_binary(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    Compute comprehensive metrics for binary classification.
    Returns accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix.
    """
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, average_precision_score, confusion_matrix,
        classification_report
    )

    # Basic metrics
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    # ROC-AUC and PR-AUC if probabilities available
    auc_roc = None
    auc_pr = None
    if y_proba is not None and y_proba.ndim == 2:
        try:
            auc_roc = roc_auc_score(y_true, y_proba[:, 1])
            auc_pr = average_precision_score(y_true, y_proba[:, 1])
        except Exception:
            pass

    # Classification report (per-class)
    report = classification_report(
        y_true, y_pred, output_dict=True, zero_division=0
    )

    return {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'roc_auc': auc_roc,
        'pr_auc': auc_pr,
        'confusion_matrix': cm.tolist(),
        'confusion_matrix_labels': ['Negative', 'Positive'],
        'classification_report': report
    }


def save_evaluation_results(
    results: Dict[str, Any],
    output_path: str,
    model_name: str,
    dataset_info: Dict[str, Any]
) -> str:
    """
    Save evaluation results in a structured JSON format.
    Returns the path to the saved file.
    """
    output = {
        'model': model_name,
        'dataset': dataset_info,
        'metrics': results,
        'metadata': {
            'evaluation_timestamp': datetime.now(timezone.utc).isoformat(),
            'random_seed': SEED,
            'library_versions': get_library_versions(),
            'hostname': os.getenv('COMPUTERNAME', 'unknown')
        }
    }

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)

    return output_path


def calculate_class_distribution(y: np.ndarray, labels: List[str]) -> Dict[str, Any]:
    """Calculate class distribution from labels."""
    unique, counts = np.unique(y, return_counts=True)
    return {
        'total_samples': len(y),
        'class_counts': dict(zip(labels, counts.tolist())),
        'class_percentages': {
            label: float(count / len(y) * 100)
            for label, count in zip(labels, counts)
        },
        'dominant_class': labels[int(np.argmax(counts))],
        'minority_class': labels[int(np.argmin(counts))],
        'class_balance_ratio': float(min(counts) / max(counts))
    }


def evaluate_model(
    model: Any,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model_name: str,
    feature_names: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    save_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluate a model on test data with comprehensive metrics.

    Args:
        model: Trained model with predict() and optionally predict_proba() methods
        X_test: Test features
        y_test: True labels
        model_name: Name of the model for reporting
        feature_names: Optional list of feature names
        labels: Optional list of label names
        save_path: Optional path to save results JSON

    Returns:
        Dictionary containing evaluation results
    """
    set_seeds(SEED)

    # Get predictions
    y_pred = model.predict(X_test)

    # Get probabilities if available
    y_proba = None
    if hasattr(model, 'predict_proba'):
        try:
            y_proba = model.predict_proba(X_test)
        except Exception:
            pass

    # Compute metrics
    metrics = compute_metrics_binary(y_test, y_pred, y_proba)

    # Calculate class distribution
    if labels is None:
        labels = ['Negative', 'Positive']
    class_dist = calculate_class_distribution(y_test, labels)

    # Build results
    results = {
        'model_name': model_name,
        'feature_names': feature_names,
        'class_distribution': class_dist,
        'metrics': metrics,
        'test_samples': len(y_test)
    }

    # Save if path provided
    if save_path:
        save_evaluation_results(
            results, save_path, model_name,
            {'name': 'test', 'samples': len(y_test)}
        )

    return results
