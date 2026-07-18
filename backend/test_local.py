import sys
import os

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.url_feature_extractor import extract_features_from_url
from services.message_analyzer import analyze_message_text
from routes.security import get_url_model

def test_url_pipeline():
    print("Testing URL Pipeline...")
    urls = [
        "https://google.com",
        "http://signin-paypal-login.security-verification.com/webapps/login"
    ]
    
    # Verify model load
    try:
        model_data = get_url_model()
        print("Successfully loaded URL classifier model.")
        print(f"Expects {len(model_data['features'])} features: {model_data['features'][:5]}...")
    except Exception as e:
        print(f"Error loading URL model: {e}")
        return
        
    for url in urls:
        print(f"\nAnalyzing URL: {url}")
        features, explanations = extract_features_from_url(url)
        print(f"Extracted {len(features)} features.")
        
        # Prepare vector
        vector = [features[feat] for feat in model_data["features"]]
        
        # Predict
        prob = model_data["model"].predict_proba([vector])[0][1]
        risk_score = int(prob * 100)
        print(f"Risk Score: {risk_score}/100")
        print(f"Explanations found: {len(explanations)}")
        for exp in explanations[:3]:
            print(f" - {exp}")

def test_message_pipeline():
    print("\nTesting Message Pipeline...")
    messages = [
        "Hey, are we still meeting for lunch today?",
        "URGENT: Your account has been suspended! Text back bank details to verify or claim your free $1000 prize now!"
    ]
    
    for msg in messages:
        print(f"\nAnalyzing Message: {msg}")
        analysis = analyze_message_text(msg)
        print(f"Prediction: {analysis['prediction']}")
        print(f"Risk Score: {analysis['risk_score']}/100")
        print("Feedback:")
        for fb in analysis["feedback"]:
            print(f" - {fb}")

if __name__ == "__main__":
    test_url_pipeline()
    test_message_pipeline()
