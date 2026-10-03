#!/usr/bin/env python3
"""
Password Security Module Tests

Tests the password analyzer for:
- Strength classification
- Pattern detection
- Common password detection
- Security requirements (no password in logs/errors)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from improved_password_service import analyze_password, format_analysis_for_api, check_common_password
from services.password_service import score_password


def test_password_strength():
    """Test password strength classification."""
    print("=" * 70)
    print("PASSWORD STRENGTH CLASSIFICATION")
    print("=" * 70)

    test_cases = [
        ("", "Empty password"),
        ("a", "Single character"),
        ("abc", "Very short lowercase"),
        ("Password1", "Short with complexity"),
        ("CorrectHorseBatteryStaple", "Long passphrase"),
        ("Tr0ub4dor&3", "Complex 11-char"),
        ("MyP@ssw0rd!2024", "Complex with year"),
        ("qwerty123", "Keyboard pattern"),
        ("admin123456", "Predictable pattern"),
    ]

    for pwd, desc in test_cases:
        result = analyze_password(pwd)
        formatted = format_analysis_for_api(result)
        print(f"\n{desc}:")
        print(f"  Input: {pwd[:30]}..." if len(pwd) > 30 else f"  Input: {pwd}")
        print(f"  Score: {formatted['score']}/100")
        print(f"  Strength: {formatted['strength']}")
        print(f"  Length: {formatted['length']}")
        print(f"  Entropy: {formatted['entropy_estimate']}")


def test_pattern_detection():
    """Test pattern detection."""
    print("\n" + "=" * 70)
    print("PATTERN DETECTION")
    print("=" * 70)

    test_cases = [
        ("aaa111", "Repeated characters"),
        ("abc123", "Sequential"),
        ("qwerty123", "Keyboard pattern"),
        ("password2024", "Year pattern"),
        ("MyPassword!1", "No obvious patterns"),
    ]

    for pwd, desc in test_cases:
        result = analyze_password(pwd)
        print(f"\n{desc}: '{pwd}'")
        print(f"  Patterns: {len(result['patterns_detected'])}")
        for p in result['patterns_detected']:
            print(f"    - {p['type']}: {p['description']}")


def test_common_passwords():
    """Test common password detection."""
    print("\n" + "=" * 70)
    print("COMMON PASSWORD DETECTION")
    print("=" * 70)

    common_tests = [
        ("password", True),
        ("qwerty", True),
        ("admin", True),
        ("iloveyou", True),
        ("CorrectHorseBatteryStaple", False),
        ("MyStr0ngP@ss!", False),
    ]

    print("\nCommon Password Check:")
    for pwd, expected_common in common_tests:
        is_common, match = check_common_password(pwd)
        status = "DETECTED" if is_common else "NOT DETECTED"
        expected = "EXPECTED" if is_common == expected_common else "UNEXPECTED"
        print(f"  [{status}] [{expected}] '{pwd}' - Match: {match}")


def test_security_requirements():
    """Test that passwords are not leaked in analysis results."""
    print("\n" + "=" * 70)
    print("SECURITY REQUIREMENTS")
    print("=" * 70)

    sensitive_passwords = [
        "SuperSecretPassword123!",
        "MyConfidentialPassword!",
        "PasswordWithNoLeaks",
    ]

    print("\nTesting that passwords are not included in results:")

    for pwd in sensitive_passwords:
        result = analyze_password(pwd)
        formatted = format_analysis_for_api(result)

        # Check that password is not in findings
        findings_str = " ".join(formatted['findings']).lower()
        recommendations_str = " ".join(formatted['recommendations']).lower()

        pwd_lower = pwd.lower()

        leaked = False
        if pwd_lower in findings_str:
            leaked = True
            print(f"  [FAIL] Password leaked in findings: {pwd}")

        if pwd_lower in recommendations_str:
            leaked = True
            print(f"  [FAIL] Password leaked in recommendations: {pwd}")

        if not leaked:
            print(f"  [PASS] Password not leaked: {pwd[:10]}...")

    print("\nTest completed.")


def test_edge_cases():
    """Test edge cases."""
    print("\n" + "=" * 70)
    print("EDGE CASES")
    print("=" * 70)

    edge_cases = [
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        ("a" * 100, "Very long password"),
        ("a" * 200, "Extremely long password"),
        ("aA1!", "Minimal diversity"),
        ("12345678901234567890", "Pure numeric"),
        ("aaaaaaaaaaaaaaaaaaaa", "Pure repeated"),
    ]

    for pwd, desc in edge_cases:
        try:
            result = analyze_password(pwd)
            formatted = format_analysis_for_api(result)
            print(f"\n{desc}:")
            print(f"  Score: {formatted['score']}/100")
            print(f"  Length: {formatted['length']}")
            print(f"  Strength: {formatted['strength']}")
        except Exception as e:
            print(f"\n{desc}: [ERROR] {e}")


def test_scoring_consistency():
    """Test that scoring is consistent."""
    print("\n" + "=" * 70)
    print("SCORING CONSISTENCY")
    print("=" * 70)

    test_passwords = [
        "password",  # Very weak
        "Password1",  # Moderate
        "CorrectHorseBatteryStaple",  # Strong
        "MyVerySecurePassword!2024",  # Strong
    ]

    print("\nRunning multiple times to verify consistency:")
    for pwd in test_passwords:
        results = []
        for i in range(3):
            result = analyze_password(pwd)
            results.append(result['score'])

        if len(set(results)) == 1:
            print(f"  [PASS] '{pwd[:20]}...' - Consistent score: {results[0]}")
        else:
            print(f"  [FAIL] '{pwd[:20]}...' - Inconsistent scores: {results}")


def main():
    """Run all tests."""
    print()
    print("#" * 70)
    print("# CYBERGUARDIAN - PASSWORD SECURITY MODULE TESTS")
    print("#" * 70)
    print()

    test_password_strength()
    test_pattern_detection()
    test_common_passwords()
    test_security_requirements()
    test_edge_cases()
    test_scoring_consistency()

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)


if __name__ == '__main__':
    main()
