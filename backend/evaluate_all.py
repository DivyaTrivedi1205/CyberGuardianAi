#!/usr/bin/env python3
"""
Main evaluation script for CyberGuardian ML models.

This script runs comprehensive evaluation for all three detection models:
1. URL Phishing Detection (XGBoost)
2. Message Spam Detection (TF-IDF + Logistic Regression)
3. Deepfake Detection (CNN + Random Forest)

Usage:
    python evaluate_all.py [--seed N] [--output-dir DIR]

Arguments:
    --seed N        Random seed for reproducibility (default: 42)
    --output-dir DIR Directory to save results (default: evaluation/results)

The script:
- Loads trained models from the models/ directory
- Evaluates each model on test data
- Computes comprehensive metrics (accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix)
- Saves results to JSON files
- Generates a comprehensive evaluation report
"""

import os
import sys
import argparse
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.url_evaluator import evaluate_url_model, analyze_url_errors
from evaluation.message_evaluator import evaluate_message_model, analyze_message_errors
from evaluation.deepfake_evaluator import evaluate_deepfake_model
from evaluation.report import generate_evaluation_report
from evaluation.base import set_seeds


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate CyberGuardian ML models'
    )
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Directory to save results')

    args = parser.parse_args()

    print("=" * 70)
    print("CYBERGUARDIAN AI - ML EVALUATION FRAMEWORK")
    print("=" * 70)
    print(f"Random Seed: {args.seed}")
    print(f"Output Directory: {args.output_dir}")
    print()

    # Set seeds for reproducibility
    set_seeds(args.seed)

    # Results directory
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'evaluation', 'results'
    )

    # Evaluate URL model
    print("=" * 70)
    print("Evaluating URL Phishing Detection Model")
    print("=" * 70)
    url_output = os.path.join(output_dir, f'url_evaluation_{args.seed}.json')
    try:
        url_results = evaluate_url_model(output_path=url_output, random_state=args.seed)
        url_error_analysis = analyze_url_errors(
            url_results.get('model', None),
            None,  # Will need to reload for error analysis
            None,
            url_results.get('feature_names', [])
        )
        print(f"URL evaluation completed.")
    except Exception as e:
        print(f"URL evaluation failed: {e}")
        url_results = None

    print()

    # Evaluate Message model
    print("=" * 70)
    print("Evaluating Message Spam Detection Model")
    print("=" * 70)
    message_output = os.path.join(output_dir, f'message_evaluation_{args.seed}.json')
    try:
        message_results = evaluate_message_model(output_path=message_output, random_state=args.seed)
        message_error_analysis = analyze_message_errors(
            message_results.get('pipeline', None),
            None, None,  # Will need to reload for error analysis
            top_n=10
        )
        print(f"Message evaluation completed.")
    except Exception as e:
        print(f"Message evaluation failed: {e}")
        message_results = None

    print()

    # Evaluate Deepfake model
    print("=" * 70)
    print("Evaluating Deepfake Detection Model")
    print("=" * 70)
    deepfake_output = os.path.join(output_dir, f'deepfake_cnn_evaluation_{args.seed}.json')
    try:
        deepfake_results = evaluate_deepfake_model(output_path=deepfake_output, random_state=args.seed)
        print(f"Deepfake evaluation completed.")
    except Exception as e:
        print(f"Deepfake evaluation failed: {e}")
        deepfake_results = None

    print()
    print("=" * 70)
    print("Generating Evaluation Report")
    print("=" * 70)

    try:
        report = generate_evaluation_report(
            url_results_path=url_output if url_results else None,
            message_results_path=message_output if message_results else None,
            deepfake_results_path=deepfake_output if deepfake_results else None
        )
        print("Report generated successfully.")
    except Exception as e:
        print(f"Report generation failed: {e}")

    print()
    print("=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    print(f"\nResults saved to: {output_dir}")
    print(f"Reports saved to: {os.path.join(os.path.dirname(output_dir), 'reports')}")


if __name__ == '__main__':
    main()
