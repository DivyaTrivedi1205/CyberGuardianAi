"""
Evaluation Report Generator for CyberGuardian ML Models.

Generates human-readable and machine-readable evaluation reports
for all detection models (URL, Message, Deepfake).
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'evaluation', 'results')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'evaluation', 'reports')


def load_evaluation_results(file_path: str) -> Dict[str, Any]:
    """Load evaluation results from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_metrics_table(metrics: Dict[str, Any]) -> str:
    """Format metrics as a human-readable table."""
    lines = [
        "| Metric              | Value           |",
        "|---------------------|-----------------|",
    ]

    metric_pairs = [
        ('accuracy', 'Accuracy'),
        ('precision', 'Precision'),
        ('recall', 'Recall'),
        ('f1_score', 'F1-Score'),
        ('roc_auc', 'ROC-AUC'),
        ('pr_auc', 'PR-AUC'),
    ]

    for key, label in metric_pairs:
        value = metrics.get(key)
        if value is not None:
            lines.append(f"| {label:19} | {value*100:14.2f}% |")

    return '\n'.join(lines)


def format_confusion_matrix(cm: List[List[int]], labels: List[str]) -> str:
    """Format confusion matrix as a human-readable table."""
    lines = [
        f"|                  | Predicted {labels[0]:10} | Predicted {labels[1]:10} |",
        "|------------------|---------------------------|---------------------------|",
        f"| Actual {labels[0]:10} | {cm[0][0]:21d} | {cm[0][1]:21d} |",
        f"| Actual {labels[1]:10} | {cm[1][0]:21d} | {cm[1][1]:21d} |",
    ]
    return '\n'.join(lines)


def format_class_distribution(dist: Dict[str, Any]) -> str:
    """Format class distribution as a human-readable table."""
    lines = [
        "| Class              | Count   | Percentage |",
        "|--------------------|---------|------------|",
    ]

    for label, count in dist.get('class_counts', {}).items():
        pct = dist.get('class_percentages', {}).get(label, 0)
        lines.append(f"| {label:18} | {count:7d} | {pct:10.2f}% |")

    return '\n'.join(lines)


def generate_single_model_report(model_name: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a report for a single model."""
    # Metrics can be nested in 'metrics.metrics' structure
    raw_metrics = results.get('metrics', {})
    # Check if metrics are nested (from evaluate_model) or flat (from evaluator)
    if isinstance(raw_metrics, dict) and 'metrics' in raw_metrics:
        test_metrics = raw_metrics['metrics']
        class_dist = raw_metrics.get('class_distribution', {})
        metadata = results.get('metadata', {})
        split_config = raw_metrics.get('split_config', {})
    else:
        test_metrics = raw_metrics
        class_dist = results.get('class_distribution', {})
        metadata = results.get('metadata', {})
        split_config = results.get('split_config', {})

    report = {
        'model_name': model_name,
        'summary': {
            'accuracy': test_metrics.get('accuracy', 0),
            'precision': test_metrics.get('precision', 0),
            'recall': test_metrics.get('recall', 0),
            'f1_score': test_metrics.get('f1_score', 0),
            'roc_auc': test_metrics.get('roc_auc'),
            'pr_auc': test_metrics.get('pr_auc'),
        },
        'samples': {
            'total': results.get('test_samples', 0),
            'train': results.get('train_samples', 0),
            'class_distribution': class_dist.get('test_set', {})
        },
        'metrics': test_metrics,
        'metadata': metadata,
        'split_config': split_config,
        'limitations': []
    }

    return report


def generate_evaluation_report(
    url_results_path: str = None,
    message_results_path: str = None,
    deepfake_results_path: str = None,
    output_format: str = 'all'
) -> Dict[str, Any]:
    """
    Generate a comprehensive evaluation report for all models.

    Args:
        url_results_path: Path to URL evaluation results JSON
        message_results_path: Path to message evaluation results JSON
        deepfake_results_path: Path to deepfake evaluation results JSON
        output_format: 'all' for both formats, 'json' or 'human'

    Returns:
        Dictionary containing all reports
    """
    # Default paths
    if url_results_path is None:
        url_results_path = os.path.join(RESULTS_DIR, 'url_evaluation_42.json')
    if message_results_path is None:
        message_results_path = os.path.join(RESULTS_DIR, 'message_evaluation_42.json')
    if deepfake_results_path is None:
        deepfake_results_path = os.path.join(RESULTS_DIR, 'deepfake_cnn_evaluation_42.json')

    # Load results
    reports = {}

    if os.path.exists(url_results_path):
        url_results = load_evaluation_results(url_results_path)
        reports['url'] = generate_single_model_report('URL Phishing', url_results)
        reports['url']['dataset'] = {
            'name': 'phishing_websites',
            'source': 'Kaggle/UEF-SASL Phishing Websites Dataset',
            'features': 30,
            'samples': url_results.get('class_distribution', {}).get('full_dataset', {}).get('total_samples', 0)
        }

    if os.path.exists(message_results_path):
        message_results = load_evaluation_results(message_results_path)
        reports['message'] = generate_single_model_report('Message Spam', message_results)
        reports['message']['dataset'] = {
            'name': 'sms_spam_collection',
            'source': 'SMS Spam Collection v.1 (Almeida et al.)',
            'vocabulary_size': message_results.get('vocabulary_size', 0),
            'samples': message_results.get('class_distribution', {}).get('full_dataset', {}).get('total_samples', 0)
        }

    if os.path.exists(deepfake_results_path):
        deepfake_results = load_evaluation_results(deepfake_results_path)
        reports['deepfake'] = generate_single_model_report('Deepfake Detection', deepfake_results)
        reports['deepfake']['dataset'] = {
            'name': 'synthetic_forensics',
            'source': 'Synthetic patterns generated during training',
            'note': 'Model trained on synthetic patterns; real-world performance may vary',
            'samples': deepfake_results.get('class_distribution', {}).get('test_set', {}).get('total_samples', 0)
        }

    # Cross-model comparison table
    comparison_rows = [
        "| Model              | Accuracy | Precision | Recall   | F1-Score | ROC-AUC  |",
        "|--------------------|----------|-----------|----------|----------|----------|",
    ]

    for model_key in ['url', 'message', 'deepfake']:
        if model_key in reports:
            m = reports[model_key]
            model_name = model_key.upper().replace('MESSAGE', 'MESSAGE ')
            acc = m['summary'].get('accuracy', 0) * 100
            prec = m['summary'].get('precision', 0) * 100
            rec = m['summary'].get('recall', 0) * 100
            f1 = m['summary'].get('f1_score', 0) * 100
            auc = m['summary'].get('roc_auc')
            auc_str = f"{auc*100:.2f}%" if auc else "N/A"
            comparison_rows.append(
                f"| {model_name:18} | {acc:8.2f}% | {prec:9.2f}% | {rec:8.2f}% | {f1:8.2f}% | {auc_str:8} |"
            )

    comparison_table = '\n'.join(comparison_rows)

    # Limitations section
    limitations = {
        'url': [],
        'message': [],
        'deepfake': []
    }

    # URL limitations
    if 'url' in reports:
        limitations['url'].append(
            "The URL model is trained on a specific phishing dataset. "
            "Performance on novel phishing techniques may vary."
        )

    # Message limitations
    if 'message' in reports:
        limitations['message'].append(
            "The message model is trained on SMS spam data. "
            "Performance on other message types (email, social media) may vary."
        )

    # Deepfake limitations
    if 'deepfake' in reports:
        limitations['deepfake'].append(
            "The deepfake model is trained on SYNTHETIC patterns, not real-world data. "
            "The current implementation serves as a proof-of-concept but may not "
            "generalize to actual deepfake images or videos."
        )
        limitations['deepfake'].append(
            "The evaluation uses the same synthetic generator as training, "
            "which may lead to inflated performance metrics."
        )

    # Generate reports
    final_report = {
        'generated_at': datetime.now().isoformat(),
        'random_seed': 42,
        'models': reports,
        'comparison_table': comparison_table,
        'limitations': limitations
    }

    # Human-readable text report
    human_report = []
    human_report.append("=" * 70)
    human_report.append("CYBERGUARDIAN AI - ML EVALUATION REPORT")
    human_report.append("=" * 70)
    human_report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    human_report.append(f"Random Seed: 42")
    human_report.append("")

    for model_key, model_report in reports.items():
        human_report.append("-" * 70)
        human_report.append(f"{model_report['model_name']} Model")
        human_report.append("-" * 70)

        if 'dataset' in model_report:
            ds = model_report['dataset']
            human_report.append(f"Dataset: {ds.get('name', 'Unknown')}")
            human_report.append(f"Source: {ds.get('source', 'Unknown')}")
            human_report.append(f"Samples: {ds.get('samples', 'N/A')}")

        if model_report.get('limitations'):
            human_report.append("\nLimitations:")
            for lim in model_report['limitations']:
                human_report.append(f"  - {lim}")

        human_report.append("")
        human_report.append("Metrics:")
        human_report.append(format_metrics_table(model_report['metrics']))

        if 'confusion_matrix' in model_report['metrics']:
            cm = model_report['metrics']['confusion_matrix']
            labels = model_report['metrics'].get('confusion_matrix_labels', ['Neg', 'Pos'])
            human_report.append("")
            human_report.append("Confusion Matrix:")
            human_report.append(format_confusion_matrix(cm, labels))

        human_report.append("")

    human_report.append("=" * 70)
    human_report.append("CROSS-MODEL COMPARISON")
    human_report.append("=" * 70)
    human_report.append(comparison_table)
    human_report.append("")

    # Save reports
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if output_format in ('all', 'json'):
        json_path = os.path.join(REPORTS_DIR, 'evaluation_report.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2)
        print(f"JSON report saved to: {json_path}")

    if output_format in ('all', 'human'):
        human_path = os.path.join(REPORTS_DIR, 'evaluation_report.txt')
        with open(human_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(human_report))
        print(f"Human-readable report saved to: {human_path}")

    return final_report


if __name__ == '__main__':
    # Generate report
    report = generate_evaluation_report()
    print("\n" + "=" * 70)
    print("EVALUATION REPORT GENERATED")
    print("=" * 70)
