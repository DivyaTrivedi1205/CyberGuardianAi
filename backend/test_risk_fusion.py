import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.risk_fusion import compute_unified_risk, normalize_score

def run_tests():
    print("=" * 60)
    print("TESTING RISK FUSION ENGINE (Phase 10)")
    print("=" * 60)

    # 1. Normalize tests
    print("\nTest 1: Score Normalization")
    assert normalize_score(None) is None
    assert normalize_score(50.5) == 50
    assert normalize_score(-10) == 0
    assert normalize_score(150) == 100
    assert normalize_score(0.85, is_probability=True) == 85
    assert normalize_score(float('nan')) is None
    assert normalize_score(float('inf')) is None
    assert normalize_score("invalid") is None
    print(" [PASS] Normalization handles NaNs, Invalid, Bounds gracefully")

    # 2. Heuristic Only
    print("\nTest 2: General Suspicious Fallbacks")
    u1 = compute_unified_risk(model_score=None, heuristic_score=45)
    assert u1.overall_risk_score == 45
    assert u1.overall_risk_category == "Suspicious"
    print(" [PASS] Handled base heuristic rules")

    # 3. Community Verifications (Maximum Priority)
    print("\nTest 3: CrowdShield Priority Override")
    u2 = compute_unified_risk(model_score=10, reputation_status="verified_threat")
    assert u2.overall_risk_score == 100
    assert u2.overall_risk_category == "High Risk"
    assert "✅ CrowdShield Community Blocklist" in u2.explanations.contributing_factors[0]
    print(" [PASS] CrowdShield verified threats take maximum priority")

    # 4. Unknown/Failed detection
    print("\nTest 4: Failing safely on unknown status")
    u3 = compute_unified_risk(model_score=None, heuristic_score=None, reputation_status=None)
    assert u3.overall_risk_score == 50
    assert u3.overall_risk_category == "Suspicious"
    print(" [PASS] Empty features do NOT default to 0 (Authentic), they fail gracefully to 50 (Suspicious)")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
