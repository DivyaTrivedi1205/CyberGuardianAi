#!/usr/bin/env python3
"""
URL Phishing Model Error Analysis

This script performs detailed error analysis on the URL phishing detection model,
focusing on understanding why specific URLs receive low risk scores.
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.url_evaluator import load_url_model, load_url_dataset
from services.url_feature_extractor import extract_features_from_url

# Paths
PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
RESULTS_DIR = os.path.join(PROJECT_ROOT, 'evaluation', 'results')


def get_feature_importance(model, feature_names):
    """Get feature importance from the model."""
    importance = model.get_booster().get_score(importance_type='gain')
    importance_df = pd.DataFrame([
        {'feature': f, 'gain': v}
        for f, v in importance.items()
    ])
    importance_df = importance_df.sort_values('gain', ascending=False)
    return importance_df


def analyze_url_features(url):
    """Extract and analyze features for a URL."""
    features, explanations = extract_features_from_url(url)
    return features, explanations


def load_test_dataset():
    """Load the test dataset for detailed analysis."""
    from sklearn.model_selection import train_test_split
    X, y = load_url_dataset()

    # Use the same split as training
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    return X_train, X_test, y_train, y_test


def load_model_with_features():
    """Load the model and get feature names."""
    model_path = os.path.join(MODELS_DIR, 'url_classifier.pkl')
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    return model_data['model'], model_data['features']


def analyze_known_failures():
    """Analyze the two known failing test cases."""
    print("=" * 70)
    print("KNOWN FAILURE CASES ANALYSIS")
    print("=" * 70)

    test_urls = [
        ("http://paypal-security-update.fake-site.com/login", "Expected: Phishing"),
        ("http://192.168.1.1/admin", "Expected: Phishing"),
    ]

    model, feature_names = load_model_with_features()

    for url, expected in test_urls:
        print(f"\n{'-'*60}")
        print(f"URL: {url}")
        print(f"Expected: {expected}")
        print()

        # Extract features using the extractor
        features, explanations = analyze_url_features(url)
        print("Features extracted by url_feature_extractor:")
        for feat, val in features.items():
            print(f"  {feat:35s} = {val}")

        # Prepare vector for model
        vector = [features[feat] for feat in feature_names]

        # Get model prediction
        pred = model.predict([vector])[0]
        proba = model.predict_proba([vector])[0]

        print()
        print(f"Model Prediction: {'Phishing' if pred == 1 else 'Legitimate'}")
        print(f"Phishing Probability: {proba[1]:.4f}")
        print(f"Legitimate Probability: {proba[0]:.4f}")
        print()
        print("Feature explanations:")
        for exp in explanations:
            print(f"  - {exp}")


def analyze_test_errors():
    """Analyze errors on the test set."""
    print("\n" + "=" * 70)
    print("TEST SET ERROR ANALYSIS")
    print("=" * 70)

    X_train, X_test, y_train, y_test = load_test_dataset()
    model, feature_names = load_model_with_features()

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    # Find false negatives (phishing predicted as legitimate)
    fn_indices = [i for i, (true, pred) in enumerate(zip(y_test, y_pred)) if pred == 0 and true == 1]

    print(f"\nTotal test samples: {len(y_test)}")
    print(f"False Negatives (phishing predicted as legitimate): {len(fn_indices)}")
    print(f"False Positives (legitimate predicted as phishing): {sum(1 for t, p in zip(y_test, y_pred) if p == 1 and t == 0)}")

    if fn_indices:
        print(f"\n{'-'*60}")
        print("Top 5 False Negatives (Most Suspicious Phishing Missed)")
        print(f"{'-'*60}")

        for idx in fn_indices[:5]:
            true_label = y_test.iloc[idx] if hasattr(y_test, 'iloc') else y_test[idx]
            pred_label = y_pred[idx]
            proba = y_proba[idx][1] if hasattr(y_proba, '__getitem__') else y_proba[idx][1]

            print(f"\nIndex: {idx}")
            print(f"  True: Phishing (1), Predicted: Legitimate (0)")
            print(f"  Phishing Probability: {proba:.4f}")

            # Get features for this sample
            row = X_test.iloc[idx] if hasattr(X_test, 'iloc') else X_test[idx]
            print(f"  Key feature values:")
            for feat in feature_names[:10]:  # Show first 10 features
                val = row[feat] if hasattr(row, 'get') else row[feature_names.index(feat)]
                print(f"    {feat}: {val}")


def analyze_feature_correlations():
    """Analyze feature correlations with the target."""
    print("\n" + "=" * 70)
    print("FEATURE CORRELATION ANALYSIS")
    print("=" * 70)

    X, y = load_url_dataset()

    # Convert y to Series for correlation
    if not isinstance(y, pd.Series):
        y = pd.Series(y, name='target')

    # Calculate correlation with target
    correlations = X.corrwith(y)
    correlations = correlations.sort_values(ascending=False)

    print("\nFeatures most positively correlated with Phishing:")
    for feat, corr in correlations.head(10).items():
        print(f"  {feat:35s}: {corr:+.4f}")

    print("\nFeatures most negatively correlated with Phishing:")
    for feat, corr in correlations.tail(10).items():
        print(f"  {feat:35s}: {corr:+.4f}")


def analyze_model_features():
    """Analyze the 30 features in detail."""
    print("\n" + "=" * 70)
    print("30 URL FEATURE DOCUMENTATION")
    print("=" * 70)

    feature_docs = {
        'having_IP_Address': {
            'type': 'lexical',
            'description': 'URL uses IP address as domain (-1) vs hostname (1)',
            'phishing_indication': -1
        },
        'URL_Length': {
            'type': 'lexical',
            'description': 'URL length category: short(1), medium(0), long(-1)',
            'phishing_indication': -1
        },
        'Shortining_Service': {
            'type': 'lexical',
            'description': 'URL uses a URL shortening service (-1) vs direct (1)',
            'phishing_indication': -1
        },
        'having_At_Symbol': {
            'type': 'lexical',
            'description': 'URL contains @ symbol (-1) vs none (1)',
            'phishing_indication': -1
        },
        'double_slash_redirecting': {
            'type': 'structural',
            'description': 'Double slash in path after index 7 (-1) vs none (1)',
            'phishing_indication': -1
        },
        'Prefix_Suffix': {
            'type': 'lexical',
            'description': 'Domain has hyphen (-1) vs none (1)',
            'phishing_indication': -1
        },
        'having_Sub_Domain': {
            'type': 'structural',
            'description': 'Subdomain count: few(1), moderate(0), many(-1)',
            'phishing_indication': -1
        },
        'SSLfinal_State': {
            'type': 'security',
            'description': 'HTTPS present (1) vs HTTP (-1)',
            'phishing_indication': -1
        },
        'Domain_registeration_length': {
            'type': 'heuristic',
            'description': 'Domain is popular/registered (1) vs unknown (-1)',
            'phishing_indication': -1
        },
        'Favicon': {
            'type': 'heuristic',
            'description': 'Favicon from same domain (1) vs external (-1)',
            'phishing_indication': -1
        },
        'port': {
            'type': 'structural',
            'description': 'Standard port (80/443) (1) vs non-standard (-1)',
            'phishing_indication': -1
        },
        'HTTPS_token': {
            'type': 'lexical',
            'description': '"https" token in domain name (-1) vs none (1)',
            'phishing_indication': -1
        },
        'Request_URL': {
            'type': 'heuristic',
            'description': 'External resources percentage (-1, 0, 1)',
            'phishing_indication': -1
        },
        'URL_of_Anchor': {
            'type': 'heuristic',
            'description': 'Suspicious anchor links percentage (-1, 0, 1)',
            'phishing_indication': -1
        },
        'Links_in_tags': {
            'type': 'heuristic',
            'description': 'External links in tags percentage (-1, 0, 1)',
            'phishing_indication': -1
        },
        'SFH': {
            'type': 'heuristic',
            'description': 'Form submission handler (empty=-1, external=0, same=1)',
            'phishing_indication': -1
        },
        'Submitting_to_email': {
            'type': 'heuristic',
            'description': 'Form submits to email (-1) vs none (1)',
            'phishing_indication': -1
        },
        'Abnormal_URL': {
            'type': 'heuristic',
            'description': 'Domain matches WHOIS (1) vs mismatch (-1)',
            'phishing_indication': -1
        },
        'Redirect': {
            'type': 'heuristic',
            'description': 'Redirect detected (1) vs none (0)',
            'phishing_indication': 1
        },
        'on_mouseover': {
            'type': 'heuristic',
            'description': 'Status bar modified (-1) vs none (1)',
            'phishing_indication': -1
        },
        'RightClick': {
            'type': 'heuristic',
            'description': 'Right-click disabled (-1) vs enabled (1)',
            'phishing_indication': -1
        },
        'popUpWidnow': {
            'type': 'heuristic',
            'description': 'Popup prompts used (-1) vs none (1)',
            'phishing_indication': -1
        },
        'Iframe': {
            'type': 'heuristic',
            'description': 'IFrame embedded (-1) vs none (1)',
            'phishing_indication': -1
        },
        'age_of_domain': {
            'type': 'heuristic',
            'description': 'Domain is old (1) vs new (-1)',
            'phishing_indication': -1
        },
        'DNSRecord': {
            'type': 'heuristic',
            'description': 'DNS resolution successful (1) vs failed (-1)',
            'phishing_indication': -1
        },
        'web_traffic': {
            'type': 'heuristic',
            'description': 'High traffic (1) vs low (-1)',
            'phishing_indication': -1
        },
        'Page_Rank': {
            'type': 'heuristic',
            'description': 'High PageRank (1) vs low (-1)',
            'phishing_indication': -1
        },
        'Google_Index': {
            'type': 'heuristic',
            'description': 'Indexed by Google (1) vs not (-1)',
            'phishing_indication': -1
        },
        'Links_pointing_to_page': {
            'type': 'heuristic',
            'description': 'Backlinks present (1) vs none (-1)',
            'phishing_indication': -1
        },
        'Statistical_report': {
            'type': 'heuristic',
            'description': 'Suspicious keywords (-1) vs none (1)',
            'phishing_indication': -1
        }
    }

    for feat, doc in feature_docs.items():
        print(f"\n{feat}:")
        print(f"  Category: {doc['type']}")
        print(f"  Description: {doc['description']}")
        print(f"  Phishing indicator: {doc['phishing_indication']}")


def main():
    """Run all analyses."""
    print("URL Phishing Model Error Analysis")
    print("=" * 70)

    # 1. Document all features
    analyze_model_features()

    # 2. Analyze known failures
    analyze_known_failures()

    # 3. Analyze test set errors
    analyze_test_errors()

    # 4. Feature correlations
    analyze_feature_correlations()

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
