#!/usr/bin/env python3
"""
Robustness Testing for URL Phishing Detection.

Tests the model's ability to handle:
1. Obfuscated URLs (percent encoding, punycode, etc.)
2. Brand-spoofing URLs (similar domains to legitimate brands)
3. IP-based URLs
4. Edge cases (empty strings, malformed URLs, special characters)
"""

import sys
import os
import pickle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.url_feature_extractor import extract_features_from_url
from evaluation.url_evaluator import load_url_model, load_url_dataset, get_feature_names
from sklearn.model_selection import train_test_split


def create_test_url_features(url, model, feature_names):
    """Extract features and get model prediction for a URL."""
    features, explanations = extract_features_from_url(url)
    vector = [features[feat] for feat in feature_names]
    proba = model.predict_proba([vector])[0][1]
    return features, proba, explanations


def test_obfuscated_urls():
    """Test detection of obfuscated URLs."""
    print("=" * 70)
    print("OBFUSCATION TESTS")
    print("=" * 70)

    # URLs with various obfuscation techniques
    test_urls = [
        # Percent encoding
        ("http://paypa%6c.com/login", "Percent-encoded domain"),
        ("http://example.com/%2e%2e%2f%2e%2e%2fetc/passwd", "Path traversal encoded"),

        # Mixed case
        ("http://WWW.PAYPAL.COM.login-secur3.com", "Mixed case domain spoof"),

        # IP address with port
        ("http://216.58.214.206:8080/secure/login", "IP with non-standard port"),

        # Long IP decimal notation
        ("http://3232235777/admin", "Decimal IP address"),

        # Double encoding
        ("http://example%252e%252ecom/attack", "Double percent encoding"),

        # Unicode/Punycode (simplified)
        ("http://paypa1.com/login", "Homoglyph attack (1 instead of l)"),
        ("http://paypa1.com", "Similar domain to PayPal"),
    ]

    print(f"\nTesting {len(test_urls)} obfuscated URL patterns...")
    print()

    model = load_url_model()
    feature_names = get_feature_names()
    results = []

    for url, description in test_urls:
        features, proba, explanations = create_test_url_features(url, model, feature_names)
        risk_score = int(proba * 100)
        is_phishing = "PHISHING" if proba >= 0.5 else "LEGITIMATE"
        detected = "DETECTED" if risk_score > 50 else "MISSED"

        results.append({
            'url': url,
            'description': description,
            'probability': proba,
            'risk_score': risk_score,
            'is_phishing': is_phishing,
            'detected': detected
        })

        print(f"[{detected}] {description}")
        print(f"      URL: {url}")
        print(f"      Risk: {risk_score}/100 ({is_phishing})")
        if explanations:
            print(f"      Flags: {', '.join(explanations[:3])}")
        print()

    return results


def test_brand_spoofing():
    """Test detection of brand-spoofing URLs."""
    print("=" * 70)
    print("BRAND SPOOFING TESTS")
    print("=" * 70)

    # Real brand domains that should be flagged as suspicious
    spoof_urls = [
        "http://secure-paypal-account-verification-update.com",
        "http://login-google-verify-account.com",
        "http://facebook-security-alert.com",
        "http://amazon-account-suspend-notice.com",
        "http://netflix-premium-login-free.com",
        "http://apple-id-verify-restore.com",
        "http://microsoft-outlook-security-check.com",
        "http://stripe-payment-update-confirmation.com",
        "http://dropbox-file-storage-verify.com",
    ]

    print(f"\nTesting {len(spoof_urls)} brand-spoofing URL patterns...")
    print()

    model = load_url_model()
    feature_names = get_feature_names()
    results = []

    for url in spoof_urls:
        features, proba, explanations = create_test_url_features(url, model, feature_names)
        risk_score = int(proba * 100)
        is_phishing = "PHISHING" if proba >= 0.5 else "LEGITIMATE"
        detected = "DETECTED" if risk_score > 50 else "MISSED"

        results.append({
            'url': url,
            'probability': proba,
            'risk_score': risk_score,
            'is_phishing': is_phishing,
            'detected': detected
        })

        print(f"[{detected}] Risk: {risk_score}/100")
        print(f"      URL: {url}")
        if explanations:
            print(f"      Flags: {', '.join(explanations[:4])}")
        print()

    return results


def test_ip_based_urls():
    """Test detection of IP-based URLs."""
    print("=" * 70)
    print("IP-BASED URL TESTS")
    print("=" * 70)

    ip_urls = [
        ("http://192.168.1.1/admin", "Internal network IP (localhost range)"),
        ("http://10.0.0.1/dashboard", "Private Class A IP"),
        ("http://172.16.0.1/login", "Private Class B IP"),
        ("http://127.0.0.1/loopback", "Loopback address"),
        ("http://8.8.8.8/dns", "Public IP (Google DNS)"),
        ("http://198.51.100.1/test", "Documentation IP range"),
    ]

    print(f"\nTesting {len(ip_urls)} IP-based URL patterns...")
    print()

    model = load_url_model()
    feature_names = get_feature_names()
    results = []

    for url, description in ip_urls:
        features, proba, explanations = create_test_url_features(url, model, feature_names)
        risk_score = int(proba * 100)
        is_phishing = "PHISHING" if proba >= 0.5 else "LEGITIMATE"
        detected = "DETECTED" if risk_score > 50 else "MISSED"

        results.append({
            'url': url,
            'description': description,
            'probability': proba,
            'risk_score': risk_score,
            'is_phishing': is_phishing,
            'detected': detected
        })

        print(f"[{detected}] {description}")
        print(f"      URL: {url}")
        print(f"      Risk: {risk_score}/100 ({is_phishing})")
        if explanations:
            print(f"      Flags: {', '.join(explanations[:3])}")
        print()

    return results


def test_edge_cases():
    """Test handling of edge cases."""
    print("=" * 70)
    print("EDGE CASE TESTS")
    print("=" * 70)

    edge_cases = [
        ("", "Empty string"),
        ("not-a-url", "No protocol"),
        ("http://", "Protocol only"),
        ("http:///path", "Missing hostname"),
        ("http://valid.com/path?query=1&safe=0", "Valid with query params"),
        ("http://sub.domain.example.co.uk", "Deep subdomain"),
        ("http://a.b.c.d.e.f.g.example.com", "Many subdomains"),
        ("http://example.com/very/long/path/that/continues/and/continues/for/a/while", "Long path"),
    ]

    print(f"\nTesting {len(edge_cases)} edge case patterns...")
    print()

    model = load_url_model()
    feature_names = get_feature_names()
    results = []

    for url, description in edge_cases:
        try:
            # Clean URL first
            from services.url_feature_extractor import clean_url
            clean_url_result = clean_url(url)
            if not clean_url_result:
                raise ValueError("Invalid URL format")

            # Extract features
            features, proba, explanations = create_test_url_features(url, model, feature_names)
            risk_score = int(proba * 100)
            is_phishing = "PHISHING" if proba >= 0.5 else "LEGITIMATE"

            results.append({
                'url': url,
                'description': description,
                'probability': proba,
                'risk_score': risk_score,
                'is_phishing': is_phishing,
                'error': None
            })

            status = "OK"
            print(f"[{status}] {description}")
            print(f"      URL: '{url}'")
            print(f"      Risk: {risk_score}/100 ({is_phishing})")
            if explanations:
                print(f"      Flags: {', '.join(explanations[:3])}")
        except Exception as e:
            results.append({
                'url': url,
                'description': description,
                'probability': 0,
                'risk_score': 0,
                'is_phishing': 'UNHANDLED',
                'error': str(e)
            })
            print(f"[UNHANDLED] {description}")
            print(f"      Exception: {e}")
        print()

    return results


def test_threshold_optimization():
    """Analyze optimal threshold for improved detection."""
    print("=" * 70)
    print("THRESHOLD OPTIMIZATION")
    print("=" * 70)

    # Load test data
    X, y = load_url_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = load_url_model()
    y_proba = model.predict_proba(X_test)[:, 1]

    # Analyze different thresholds
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]

    print(f"\nAnalyzing threshold trade-offs on test set...")
    print(f"Total test samples: {len(y_test)}")
    print(f"Phishing cases in test: {y_test.sum()}")
    print()

    results = []

    for threshold in thresholds:
        y_pred = (y_proba >= threshold).astype(int)

        # Calculate metrics
        tp = ((y_pred == 1) & (y_test == 1)).sum()
        tn = ((y_pred == 0) & (y_test == 0)).sum()
        fp = ((y_pred == 1) & (y_test == 0)).sum()
        fn = ((y_pred == 0) & (y_test == 1)).sum()

        accuracy = (tp + tn) / len(y_test)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        results.append({
            'threshold': threshold,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn
        })

        print(f"Threshold: {threshold:.1f}")
        print(f"  TP: {tp:4d} | TN: {tn:4d} | FP: {fp:4d} | FN: {fn:4d}")
        print(f"  Accuracy:  {accuracy*100:6.2f}%")
        print(f"  Precision: {precision*100:6.2f}%")
        print(f"  Recall:    {recall*100:6.2f}%")
        print(f"  F1:        {f1*100:6.2f}%")
        print()

    return results


def main():
    """Run all robustness tests."""
    print()
    print("#" * 70)
    print("# CYBERGUARDIAN - URL PHISHING DETECTION ROBUSTNESS TESTS")
    print("#" * 70)
    print()

    all_results = {
        'obfuscation': test_obfuscated_urls(),
        'brand_spoofing': test_brand_spoofing(),
        'ip_based': test_ip_based_urls(),
        'edge_cases': test_edge_cases(),
        'threshold_analysis': test_threshold_optimization()
    }

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Count detection rates
    obfuscation_detected = sum(1 for r in all_results['obfuscation'] if r['detected'] == 'DETECTED')
    spoofing_detected = sum(1 for r in all_results['brand_spoofing'] if r['detected'] == 'DETECTED')
    ip_detected = sum(1 for r in all_results['ip_based'] if r['detected'] == 'DETECTED')

    print(f"\nObfuscation Tests: {obfuscation_detected}/{len(all_results['obfuscation'])} detected")
    print(f"Brand Spoofing: {spoofing_detected}/{len(all_results['brand_spoofing'])} detected")
    print(f"IP-Based URLs: {ip_detected}/{len(all_results['ip_based'])} detected")

    print()
    print("Robustness testing complete.")

    return all_results


if __name__ == '__main__':
    main()
