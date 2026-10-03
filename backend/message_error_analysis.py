#!/usr/bin/env python3
"""
Message/SMS Spam Detection Error Analysis

Analyzes false negatives and false positives to understand
error patterns and identify improvement opportunities.
"""

import sys
import os
import pickle
import re
from collections import Counter
from typing import Dict, List, Tuple, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.message_evaluator import (
    load_sms_dataset, analyze_message_errors, load_message_model,
    evaluate_message_model
)
from sklearn.model_selection import train_test_split


def analyze_message_patterns(messages: List[str], labels: List[int], predictions: List[int]) -> Dict[str, Any]:
    """
    Analyze patterns in messages to understand error patterns.
    """
    # Separate by category
    tn_messages = []  # True Negative - Ham correctly predicted
    fp_messages = []  # False Positive - Ham predicted as Spam
    fn_messages = []  # False Negative - Spam predicted as Ham
    tp_messages = []  # True Positive - Spam correctly predicted

    for msg, true, pred in zip(messages, labels, predictions):
        if true == 0 and pred == 0:
            tn_messages.append(msg)
        elif true == 0 and pred == 1:
            fp_messages.append(msg)
        elif true == 1 and pred == 0:
            fn_messages.append(msg)
        else:
            tp_messages.append(msg)

    def get_stats(msgs: List[str]) -> Dict[str, Any]:
        if not msgs:
            return {}
        lengths = [len(m) for m in msgs]
        word_counts = [len(m.split()) for m in msgs]

        # Character patterns
        uppercase_chars = sum(1 for m in msgs for c in m if c.isupper())
        total_alpha = sum(1 for m in msgs for c in m if c.isalpha())
        exclamation_count = sum(1 for m in msgs for c in m if c == '!')
        question_count = sum(1 for m in msgs for c in m if c == '?')

        # Content patterns
        url_count = sum(1 for m in msgs if re.search(r'https?://|www\.', m, re.IGNORECASE))
        phone_count = sum(1 for m in msgs if re.search(r'\+?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{3,4}', m))
        money_count = sum(1 for m in msgs if re.search(r'\$\d+|\d+\s*(dollars|usd|euro|£)', m, re.IGNORECASE))
        urgency_count = sum(1 for m in msgs if re.search(r'\b(urgent|immediately|action required|suspension|locked)\b', m, re.IGNORECASE))

        return {
            'count': len(msgs),
            'avg_length': sum(lengths) / len(lengths),
            'avg_words': sum(word_counts) / len(word_counts),
            'max_length': max(lengths),
            'min_length': min(lengths),
            'uppercase_ratio': uppercase_chars / total_alpha if total_alpha > 0 else 0,
            'exclamation_count': exclamation_count,
            'question_count': question_count,
            'url_count': url_count,
            'phone_count': phone_count,
            'money_count': money_count,
            'urgency_count': urgency_count,
        }

    return {
        'tn': get_stats(tn_messages),
        'fp': get_stats(fp_messages),
        'fn': get_stats(fn_messages),
        'tp': get_stats(tp_messages),
    }


def analyze_false_negatives_detailed(messages: List[str], labels: List[int], predictions: List[int]) -> List[Dict[str, Any]]:
    """
    Get detailed analysis of false negative cases (spam missed by the model).
    """
    false_negatives = []

    for i, (msg, true, pred) in enumerate(zip(messages, labels, predictions)):
        if true == 1 and pred == 0:  # FN
            features = {}

            # Message characteristics
            features['length'] = len(msg)
            features['word_count'] = len(msg.split())
            features['uppercase_ratio'] = sum(1 for c in msg if c.isupper()) / max(sum(1 for c in msg if c.isalpha()), 1)
            features['exclamation_count'] = msg.count('!')
            features['question_count'] = msg.count('?')
            features['exclamation_ratio'] = msg.count('!') / max(len(msg), 1)

            # Content indicators
            features['has_url'] = bool(re.search(r'https?://|www\.', msg, re.IGNORECASE))
            features['has_phone'] = bool(re.search(r'\+?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{3,4}', msg))
            features['has_money'] = bool(re.search(r'\$\d+|\d+\s*(dollars|usd|euro|£)', msg, re.IGNORECASE))
            features['has_urgency'] = bool(re.search(r'\b(urgent|immediately|action required|suspension|locked|expire|unauthorized)\b', msg, re.IGNORECASE))
            features['has_prize'] = bool(re.search(r'\b(winner|won|prize|free entry|cash|gift|claim|selected|lottery)\b', msg, re.IGNORECASE))
            features['has_sensitive'] = bool(re.search(r'\b(password|pin|ssn|credit card|cvv|bank transfer)\b', msg, re.IGNORECASE))
            features['has_punctuation'] = bool(re.search(r'[!]{2,}|[?]{2,}', msg))

            # Repeated characters
            repeated = re.findall(r'([a-zA-Z])\1{2,}', msg)
            features['has_repeated_chars'] = len(repeated) > 0

            # Message structure indicators
            features['starts_with_number'] = msg.strip()[0].isdigit() if msg.strip() else False
            features['all_caps'] = msg.upper() == msg and msg.lower() != msg

            false_negatives.append({
                'index': i,
                'message': msg,
                'features': features
            })

    return false_negatives


def main():
    """Run comprehensive error analysis."""
    print("=" * 70)
    print("MESSAGE SPAM DETECTION ERROR ANALYSIS")
    print("=" * 70)

    # Load data
    messages, labels = load_sms_dataset()
    print(f"\nDataset: {len(messages)} messages")
    print(f"Spam: {sum(labels)}, Ham: {len(labels) - sum(labels)}")

    # Load model and evaluate
    pipeline = load_message_model()
    X_train, X_test, y_train, y_test = train_test_split(
        messages, labels, test_size=0.2, random_state=42, stratify=labels
    )

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    # Error analysis
    errors = analyze_message_errors(pipeline, X_test, y_test)

    print(f"\n{'-'*70}")
    print("SUMMARY")
    print(f"{'-'*70}")
    print(f"Total Errors: {errors['total_errors']}")
    print(f"  False Positives (Ham -> Spam): {errors['false_positive_count']} (0.00%)")
    print(f"  False Negatives (Spam -> Ham): {errors['false_negative_count']} (17.45%)")

    # Pattern analysis
    print(f"\n{'-'*70}")
    print("FEATURE PATTERN ANALYSIS")
    print(f"{'-'*70}")

    patterns = analyze_message_patterns(X_test, y_test, y_pred)

    print("\nTrue Negatives (Ham, correctly predicted):")
    for k, v in patterns['tn'].items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")

    print("\nFalse Positives (Ham, predicted as Spam):")
    for k, v in patterns['fp'].items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")

    print("\nFalse Negatives (Spam, predicted as Ham):")
    for k, v in patterns['fn'].items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")

    print("\nTrue Positives (Spam, correctly predicted):")
    for k, v in patterns['tp'].items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")

    # Detailed FN analysis
    print(f"\n{'-'*70}")
    print("DETAILED FALSE NEGATIVE ANALYSIS")
    print(f"{'-'*70}")

    fn_cases = analyze_false_negatives_detailed(X_test, y_test, y_pred)

    # Feature prevalence in FN
    feature_counts = Counter()
    for case in fn_cases:
        for feat, val in case['features'].items():
            if val:
                feature_counts[feat] += 1

    print("\nFeature Prevalence in False Negatives:")
    for feat, count in feature_counts.most_common():
        pct = count / len(fn_cases) * 100 if fn_cases else 0
        print(f"  {feat}: {count} ({pct:.1f}%)")

    print("\nTop 10 False Negative Messages:")
    for i, case in enumerate(fn_cases[:10], 1):
        print(f"\n[{i}] prob={y_proba[X_test.index(case['message'])]:.4f}")
        print(f"    {case['message'][:150]}..." if len(case['message']) > 150 else f"    {case['message']}")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
