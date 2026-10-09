import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import patch
from routes.security import analyze_url, analyze_message
from models.security_schemas import UrlAnalysisRequest, MessageAnalysisRequest

def mock_reputation(ind, ind_type):
    return None

def mock_save(*args, **kwargs):
    pass

@patch('routes.security.check_community_reputation', side_effect=mock_reputation)
@patch('routes.security.db_connection')
def run_tests(mock_db, mock_rep):
    print("=" * 60)
    print("TESTING UNIFIED RISK API (Phase 10)")
    print("=" * 60)

    # 1. 192.168.1.1 regression
    req1 = UrlAnalysisRequest(url="http://192.168.1.1/admin")
    res1 = analyze_url(req1, current_user=None)
    
    print("\n[URL] http://192.168.1.1/admin")
    print(f"Risk Score: {res1.risk_score}")
    print(f"Prediction: {res1.prediction}")
    status = "PASS" if res1.prediction in ["Suspicious", "Phishing", "High Risk"] else "FAIL"
    print(f"[{status}] Fixed ML False Negative by relying on heuristic fusion!")

    # 2. paypal-security-update
    req2 = UrlAnalysisRequest(url="http://paypal-security-update.fake-site.com/login")
    res2 = analyze_url(req2, current_user=None)
    
    print("\n[URL] http://paypal-security-update.fake-site.com/login")
    print(f"Risk Score: {res2.risk_score}")
    print(f"Prediction: {res2.prediction}")
    status = "PASS" if res2.prediction in ["Suspicious", "Phishing", "High Risk"] else "FAIL"
    print(f"[{status}] Enhanced risk score correctly identifies phishing traits.")
    
    # 3. Legitimate URL
    req3 = UrlAnalysisRequest(url="https://google.com")
    res3 = analyze_url(req3, current_user=None)
    
    print("\n[URL] https://google.com")
    print(f"Risk Score: {res3.risk_score}")
    print(f"Prediction: {res3.prediction}")
    status = "PASS" if res3.prediction == "Low Risk" or res3.prediction == "Legitimate" else "FAIL"
    print(f"[{status}] Preserved baseline legitimate predictions.")

    # 4. Deepfake through pure endpoint
    from models.security_schemas import PasswordAnalysisRequest
    from routes.security import analyze_password_endpoint
    
    req4 = PasswordAnalysisRequest(password="password123")
    res4 = analyze_password_endpoint(req4, current_user=None)
    print("\n[PASSWORD] password123")
    print(f"Risk Score: {res4.unified_assessment['overall_risk_score']}")
    status = "PASS" if res4.unified_assessment['overall_risk_category'] in ["Suspicious", "High Risk"] else "FAIL"
    print(f"[{status}] Password assessment integrated unified logic securely.")

if __name__ == "__main__":
    run_tests()
