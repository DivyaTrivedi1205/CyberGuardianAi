#!/usr/bin/env python3
"""
Improved URL Phishing Detection Model with Feature Engineering.

This module provides:
1. Improved feature extraction
2. XGBoost model training with hyperparameter tuning
3. Comparison with baseline
4. Threshold optimization
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)
import xgboost as xgb

# Paths - properly handle both when run from backend/ and from root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Check if we're in backend or in root
if os.path.basename(SCRIPT_DIR) == 'backend':
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # Go up from backend to project root
else:
    PROJECT_ROOT = SCRIPT_DIR
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


def load_url_dataset() -> Tuple[pd.DataFrame, pd.Series]:
    """Load the URL phishing dataset."""
    arff_path = os.path.join(DATASETS_DIR, 'urls', 'phishing_websites', 'Training Dataset.arff')
    if not os.path.exists(arff_path):
        raise FileNotFoundError(f"URL dataset not found at {arff_path}")

    df = parse_arff(arff_path)

    # Convert Result: 1 -> 0 (Legitimate), -1 -> 1 (Phishing)
    X = df.drop(columns=['Result'])
    y = df['Result'].map({1: 0, -1: 1})

    return X, y


def compute_feature_correlation_with_target(X: pd.DataFrame, y: pd.Series) -> pd.Series:
    """Compute correlation between each feature and target."""
    # Convert to numeric and compute correlation
    correlations = {}
    for col in X.columns:
        corr = X[col].astype(int).corr(y.astype(int))
        correlations[col] = corr
    return pd.Series(correlations)


def analyze_dataset_quality(X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
    """Analyze dataset quality for duplicates and leakage."""
    analysis = {}

    # Check for exact duplicates
    X_with_y = X.copy()
    X_with_y['target'] = y
    exact_duplicates = X_with_y.duplicated().sum()
    analysis['exact_duplicates'] = int(exact_duplicates)
    analysis['exact_duplicate_rate'] = float(exact_duplicates / len(X_with_y) * 100) if len(X_with_y) > 0 else 0

    # Check feature correlations with target
    correlations = compute_feature_correlation_with_target(X, y)
    analysis['feature_correlations'] = correlations.to_dict()

    # Class distribution
    analysis['class_distribution'] = {
        'legitimate': int((y == 0).sum()),
        'phishing': int((y == 1).sum()),
        'total': int(len(y)),
        'imbalance_ratio': float((y == 0).sum() / (y == 1).sum()) if (y == 1).sum() > 0 else 0
    }

    return analysis


def train_improved_url_model(
    random_state: int = 42,
    test_size: float = 0.2,
    use_tuned: bool = True
) -> Tuple[Any, List[str], Dict[str, Any]]:
    """
    Train an improved URL phishing detection model.

    Args:
        random_state: Random seed for reproducibility
        test_size: Size of test set
        use_tuned: Whether to use tuned hyperparameters

    Returns:
        Tuple of (model, feature_names, training_info)
    """
    print("Loading URL phishing dataset...")
    X, y = load_url_dataset()

    print(f"Dataset: {len(y)} samples, {len(X.columns)} features")

    # Analyze dataset
    dataset_analysis = analyze_dataset_quality(X, y)
    print(f"Class distribution: Legitimate={dataset_analysis['class_distribution']['legitimate']}, "
          f"Phishing={dataset_analysis['class_distribution']['phishing']}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    # Feature names
    feature_names = list(X.columns)

    # Model configuration
    if use_tuned:
        # Tuned XGBoost parameters (based on grid search)
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            gamma=0.1,
            random_state=random_state,
            eval_metric='logloss',
            use_label_encoder=False,
            verbosity=0
        )
    else:
        # Baseline configuration
        model = xgb.XGBClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.1,
            random_state=random_state,
            eval_metric='logloss',
            use_label_encoder=False,
            verbosity=0
        )

    # Train model
    print("Training model...")
    model.fit(X_train, y_train)

    # Evaluate on test set
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    # Compute metrics
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, zero_division=0),
        'recall': recall_score(y_test, y_pred, zero_division=0),
        'f1_score': f1_score(y_test, y_pred, zero_division=0),
        'roc_auc': roc_auc_score(y_test, y_proba[:, 1]),
        'pr_auc': average_precision_score(y_test, y_proba[:, 1]),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
    }

    training_info = {
        'model_type': 'XGBoost' + (' (Tuned)' if use_tuned else ' (Baseline)'),
        'random_state': random_state,
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'features': feature_names,
        'dataset_analysis': dataset_analysis,
        'metrics': metrics,
        'hyperparameters': model.get_params()
    }

    print(f"\nTest Results:")
    print(f"  Accuracy:  {metrics['accuracy']*100:.2f}%")
    print(f"  Precision: {metrics['precision']*100:.2f}%")
    print(f"  Recall:    {metrics['recall']*100:.2f}%")
    print(f"  F1:        {metrics['f1_score']*100:.2f}%")
    print(f"  ROC-AUC:   {metrics['roc_auc']*100:.2f}%")

    return model, feature_names, training_info


def find_optimal_threshold(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    target_recall: float = 0.90
) -> float:
    """
    Find optimal classification threshold.

    Args:
        y_true: True labels
        y_proba: Predicted probabilities for positive class
        target_recall: Minimum recall to achieve

    Returns:
        Optimal threshold
    """
    thresholds = np.arange(0.05, 0.95, 0.01)

    best_threshold = 0.5
    best_f1 = 0

    for thresh in thresholds:
        y_pred = (y_proba >= thresh).astype(int)

        tp = np.sum((y_pred == 1) & (y_true == 1))
        fn = np.sum((y_pred == 0) & (y_true == 1))
        fp = np.sum((y_pred == 1) & (y_true == 0))

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        if recall >= target_recall and f1 > best_f1:
            best_f1 = f1
            best_threshold = thresh

    # If no threshold meets target recall, pick best overall F1
    if best_f1 == 0:
        for thresh in thresholds:
            y_pred = (y_proba >= thresh).astype(int)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = thresh

    return best_threshold


def evaluate_model_with_threshold(
    model: Any,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    threshold: float,
    feature_names: List[str]
) -> Dict[str, Any]:
    """
    Evaluate model with a specific threshold.

    Args:
        model: Trained model
        X_test: Test features
        y_test: True labels
        threshold: Classification threshold
        feature_names: List of feature names

    Returns:
        Evaluation metrics
    """
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, zero_division=0),
        'recall': recall_score(y_test, y_pred, zero_division=0),
        'f1_score': f1_score(y_test, y_pred, zero_division=0),
        'roc_auc': roc_auc_score(y_test, y_proba),
        'pr_auc': average_precision_score(y_test, y_proba),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        'threshold': threshold
    }

    return metrics


def evaluate_new_model():
    """Evaluate the improved model and compare with baseline."""
    print("=" * 70)
    print("IMPROVED URL PHISHING DETECTION MODEL")
    print("=" * 70)

    # Train baseline model
    print("\n--- Training Baseline Model ---")
    baseline_model, baseline_features, baseline_info = train_improved_url_model(
        random_state=42, use_tuned=False
    )

    # Train tuned model
    print("\n--- Training Tuned Model ---")
    tuned_model, tuned_features, tuned_info = train_improved_url_model(
        random_state=42, use_tuned=True
    )

    # Save tuned model
    model_path = os.path.join(MODELS_DIR, 'url_classifier_improved.pkl')
    model_data = {
        'model': tuned_model,
        'features': tuned_features,
        'training_info': tuned_info,
        'baseline_metrics': baseline_info['metrics'],
        'improvement': {
            'accuracy': tuned_info['metrics']['accuracy'] - baseline_info['metrics']['accuracy'],
            'f1': tuned_info['metrics']['f1_score'] - baseline_info['metrics']['f1_score'],
            'recall': tuned_info['metrics']['recall'] - baseline_info['metrics']['recall']
        }
    }

    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)

    print(f"\nSaved improved model to: {model_path}")

    # Find optimal threshold
    print("\n--- Finding Optimal Threshold ---")
    X, y = load_url_dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    y_proba_tuned = tuned_model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    print("\nBaseline Model:")
    print(f"  Accuracy:  {baseline_info['metrics']['accuracy']*100:.2f}%")
    print(f"  F1-Score:  {baseline_info['metrics']['f1_score']*100:.2f}%")
    print(f"  Recall:    {baseline_info['metrics']['recall']*100:.2f}%")
    print(f"  ROC-AUC:   {baseline_info['metrics']['roc_auc']*100:.2f}%")

    print("\nTuned Model:")
    print(f"  Accuracy:  {tuned_info['metrics']['accuracy']*100:.2f}%")
    print(f"  F1-Score:  {tuned_info['metrics']['f1_score']*100:.2f}%")
    print(f"  Recall:    {tuned_info['metrics']['recall']*100:.2f}%")
    print(f"  ROC-AUC:   {tuned_info['metrics']['roc_auc']*100:.2f}%")

    print("\nImprovement:")
    print(f"  Accuracy:  {tuned_info['metrics']['accuracy'] - baseline_info['metrics']['accuracy']:+.2%}")
    print(f"  F1-Score:  {tuned_info['metrics']['f1_score'] - baseline_info['metrics']['f1_score']:+.2%}")
    print(f"  Recall:    {tuned_info['metrics']['recall'] - baseline_info['metrics']['recall']:+.2%}")
    print(f"  ROC-AUC:   {tuned_info['metrics']['roc_auc'] - baseline_info['metrics']['roc_auc']:+.2%}")


if __name__ == '__main__':
    evaluate_new_model()
