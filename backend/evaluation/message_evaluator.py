"""
Message/Spam Detection Evaluation Module.

Evaluates the TF-IDF + Logistic Regression message classifier.
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer

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


def load_sms_dataset() -> Tuple[List[str], np.ndarray]:
    """
    Load the SMS Spam Collection dataset.
    Returns (messages, labels) where labels are 0=Ham, 1=Spam.
    """
    sms_path = os.path.join(DATASETS_DIR, 'messages', 'smsspam', 'SMSSpamCollection')
    if not os.path.exists(sms_path):
        raise FileNotFoundError(f"SMS dataset not found at {sms_path}")

    messages = []
    labels = []

    with open(sms_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t', 1)
            if len(parts) == 2:
                label, message = parts
                # ham -> 0 (Legitimate), spam -> 1 (Spam)
                labels.append(1 if label.lower() == 'spam' else 0)
                messages.append(message)

    return messages, np.array(labels)


def load_message_model() -> Any:
    """Load the message classifier pipeline."""
    model_path = os.path.join(MODELS_DIR, 'message_classifier.pkl')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Message model not found at {model_path}")

    with open(model_path, 'rb') as f:
        return pickle.load(f)


def evaluate_message_model(
    output_path: str = None,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True
) -> Dict[str, Any]:
    """
    Evaluate the message spam detection model.

    This function:
    1. Loads the SMS Spam Collection dataset
    2. Splits into train/test
    3. Evaluates the model on the test set
    4. Computes comprehensive metrics
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
    print("Loading SMS Spam Collection dataset...")
    messages, labels = load_sms_dataset()

    # Class distribution
    full_class_dist = calculate_class_distribution(
        labels, ['Ham (Legitimate)', 'Spam (Phishing)']
    )

    print(f"Full dataset: {len(labels)} samples")
    print(f"Class distribution: {full_class_dist['class_counts']}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        messages, labels, test_size=test_size, random_state=random_state,
        stratify=labels if stratify else None
    )

    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")

    # Load model
    print("\nLoading message classifier pipeline...")
    pipeline = load_message_model()

    # Get predictions and probabilities
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test) if hasattr(pipeline, 'predict_proba') else None

    # Compute metrics
    metrics = compute_metrics_binary(y_test, y_pred, y_proba)

    # Class distribution on test set
    test_class_dist = calculate_class_distribution(
        y_test, ['Ham (Legitimate)', 'Spam (Phishing)']
    )

    # Model hash
    try:
        model_hash = compute_hash(os.path.join(MODELS_DIR, 'message_classifier.pkl'))
    except Exception:
        model_hash = "unknown"

    # Vocabulary info
    tfidf = pipeline.named_steps['tfidf']
    vocabulary_size = len(tfidf.vocabulary_)

    # Build results
    results = {
        'model_name': 'TFIDF_LogisticRegression',
        'model_version': 'original',
        'model_hash': model_hash,
        'vocabulary_size': vocabulary_size,
        'vocabulary_max_features': 5000,
        'ngram_range': [1, 2],
        'stop_words': 'english',
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
        'train_samples': int(len(X_train)),
        'library_versions': get_library_versions()
    }

    # Save results if path provided
    if output_path is None:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        output_path = os.path.join(
            RESULTS_DIR,
            f'message_evaluation_{random_state}.json'
        )

    save_evaluation_results(
        results, output_path,
        'TFIDF_LogisticRegression',
        {'name': 'sms_spam_collection', 'samples': len(labels)}
    )

    print(f"\n{'='*60}")
    print("MESSAGE MODEL EVALUATION RESULTS")
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


def analyze_message_errors(
    pipeline: Any,
    X_test: List[str],
    y_test: np.ndarray,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Analyze misclassified message examples to identify error patterns.

    Args:
        pipeline: Trained message classification pipeline
        X_test: Test messages
        y_test: True labels
        top_n: Number of top errors to analyze

    Returns:
        Dictionary with error analysis results
    """
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)

    # Find false positives (predict spam, but it's ham)
    false_positives = []
    for i, (true, pred, proba) in enumerate(zip(y_test, y_pred, y_proba)):
        if pred == 1 and true == 0:
            false_positives.append({
                'index': i,
                'message': X_test[i],
                'probability_spam': float(proba[1])
            })

    # Find false negatives (predict ham, but it's spam)
    false_negatives = []
    for i, (true, pred, proba) in enumerate(zip(y_test, y_pred, y_proba)):
        if pred == 0 and true == 1:
            false_negatives.append({
                'index': i,
                'message': X_test[i],
                'probability_spam': float(proba[1])
            })

    # Sort
    false_negatives.sort(key=lambda x: x['probability_spam'], reverse=True)
    false_positives.sort(key=lambda x: x['probability_spam'])

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
    results = evaluate_message_model()
    print(f"\nMessage evaluation completed. Results saved to: {results}")
