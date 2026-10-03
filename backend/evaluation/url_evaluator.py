"""
URL Phishing Detection Evaluation Module.

Evaluates the XGBoost URL phishing classifier using the phishing websites dataset.
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from pathlib import Path
from sklearn.model_selection import train_test_split

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base import (
    evaluate_model, compute_metrics_binary, calculate_class_distribution,
    set_seeds, save_evaluation_results, get_library_versions
)

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
DATASETS_DIR = os.path.join(PROJECT_ROOT, 'datasets')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'evaluation', 'results')


def parse_arff(file_path: str) -> pd.DataFrame:
    """Parse ARFF file and return DataFrame."""
    attributes = []
    data_started = False
    data_lines = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.lower().startswith('@relation'):
                continue
            if line_str.lower().startswith('@attribute'):
                parts = line_str.split()
                attr_name = parts[1]
                attributes.append(attr_name)
                continue
            if line_str.lower().startswith('@data'):
                data_started = True
                continue
            if data_started:
                vals = [int(v.strip()) for v in line_str.split(',')]
                data_lines.append(vals)

    return pd.DataFrame(data_lines, columns=attributes)


def load_url_dataset() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the URL phishing dataset.
    Returns (X, y) where X is features and y is labels (0=Legitimate, 1=Phishing).
    """
    arff_path = os.path.join(DATASETS_DIR, 'urls', 'phishing_websites', 'Training Dataset.arff')
    if not os.path.exists(arff_path):
        raise FileNotFoundError(f"URL dataset not found at {arff_path}")

    df = parse_arff(arff_path)

    # Convert Result: 1 -> 0 (Legitimate), -1 -> 1 (Phishing)
    X = df.drop(columns=['Result'])
    y = df['Result'].map({1: 0, -1: 1})

    return X, y


def load_url_model() -> Any:
    """Load the URL classifier model."""
    model_path = os.path.join(MODELS_DIR, 'url_classifier.pkl')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"URL model not found at {model_path}")

    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    return model_data['model']


def get_feature_names() -> list:
    """Get feature names from the dataset."""
    X, _ = load_url_dataset()
    return list(X.columns)


def evaluate_url_model(
    output_path: str = None,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True
) -> Dict[str, Any]:
    """
    Evaluate the URL phishing detection model.

    This function:
    1. Loads the training dataset
    2. Splits into train/test (reproducing original split if possible)
    3. Evaluates the model on the test set
    4. Computes comprehensive metrics (accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix)
    5. Returns and optionally saves results

    Args:
        output_path: Path to save results JSON (optional)
        test_size: Test set size (default 0.2, same as original training)
        random_state: Random seed for reproducibility (default 42)
        stratify: Whether to stratify the split (default True)

    Returns:
        Dictionary containing evaluation results
    """
    set_seeds(random_state)

    # Load dataset
    print("Loading URL phishing dataset...")
    X, y = load_url_dataset()

    # Class distribution in full dataset
    full_class_dist = calculate_class_distribution(
        y.values, ['Legitimate', 'Phishing']
    )

    print(f"Full dataset: {len(y)} samples")
    print(f"Class distribution: {full_class_dist['class_counts']}")

    # Split data (matching original training configuration)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y if stratify else None
    )

    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")

    # Load model
    print("\nLoading URL classifier model...")
    model = load_url_model()

    # Get test predictions and probabilities
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test) if hasattr(model, 'predict_proba') else None

    # Compute metrics
    metrics = compute_metrics_binary(y_test.values, y_pred, y_proba)

    # Class distribution on test set
    test_class_dist = calculate_class_distribution(
        y_test.values, ['Legitimate', 'Phishing']
    )

    # Model hash
    try:
        model_hash = compute_hash(os.path.join(MODELS_DIR, 'url_classifier.pkl'))
    except Exception:
        model_hash = "unknown"

    # Build results
    results = {
        'model_name': 'XGBoost_URL_Classifier',
        'model_version': 'original',
        'model_hash': model_hash,
        'feature_names': list(X.columns),
        'class_distribution': {
            'full_dataset': full_class_dist,
            'test_set': test_class_dist
        },
        'split_config': {
            'test_size': test_size,
            'random_state': random_state,
            'stratify': stratify
        },
        'metrics': metrics,
        'test_samples': int(len(y_test)),
        'train_samples': int(len(y_train)),
        'library_versions': get_library_versions()
    }

    # Save results if path provided
    if output_path is None:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        output_path = os.path.join(
            RESULTS_DIR,
            f'url_evaluation_{random_state}.json'
        )

    save_evaluation_results(
        results, output_path,
        'XGBoost_URL_Classifier',
        {'name': 'phishing_websites', 'samples': len(y)}
    )

    print(f"\n{'='*60}")
    print("URL MODEL EVALUATION RESULTS")
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


def analyze_url_errors(
    model: Any,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    feature_names: list,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Analyze misclassified URL examples to identify error patterns.

    Args:
        model: Trained URL classifier
        X_test: Test features
        y_test: True labels
        feature_names: List of feature names
        top_n: Number of top errors to analyze

    Returns:
        Dictionary with error analysis results
    """
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    # Find false positives (model predicts phishing, but it's legitimate)
    false_positives = []
    for i, (true, pred, proba) in enumerate(zip(y_test, y_pred, y_proba)):
        if pred == 1 and true == 0:
            false_positives.append({
                'index': i,
                'features': X_test.iloc[i].to_dict(),
                'probability': float(proba[1])
            })

    # Find false negatives (model predicts legitimate, but it's phishing)
    false_negatives = []
    for i, (true, pred, proba) in enumerate(zip(y_test, y_pred, y_proba)):
        if pred == 0 and true == 1:
            false_negatives.append({
                'index': i,
                'features': X_test.iloc[i].to_dict(),
                'probability': float(proba[1])
            })

    # Sort by probability to find most suspicious false negatives and least suspicious false positives
    false_negatives.sort(key=lambda x: x['probability'], reverse=True)
    false_positives.sort(key=lambda x: x['probability'])

    return {
        'false_positive_count': len(false_positives),
        'false_negative_count': len(false_negatives),
        'false_positive_rate': len(false_positives) / len(y_test),
        'false_negative_rate': len(false_negatives) / len(y_test),
        'top_false_positives': false_positives[:top_n],
        'top_false_negatives': false_negatives[:top_n],
        'total_errors': len(false_positives) + len(false_negatives)
    }


if __name__ == '__main__':
    # Run evaluation
    results = evaluate_url_model()
    print(f"\nURL evaluation completed. Results saved to: {results}")
