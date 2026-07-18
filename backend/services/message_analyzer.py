import os
import pickle
import re
from typing import Dict, Any, List

# Load the trained message model
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "message_classifier.pkl"))

_model = None

def get_message_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
        else:
            raise FileNotFoundError(f"Message classifier model not found at {MODEL_PATH}")
    return _model

def analyze_message_text(message: str) -> Dict[str, Any]:
    """
    Analyzes a message text for spam/phishing risk.
    Returns:
        prediction: "Spam/Phishing" or "Legitimate"
        risk_score: 0-100 score representing threat level
        feedback: list of reasons/explanations for the risk score
    """
    message = message.strip()
    if not message:
        return {
            "prediction": "Legitimate",
            "risk_score": 0,
            "feedback": ["Message is empty."]
        }
        
    feedback = []
    
    # 1. Run Machine Learning Model
    try:
        model = get_message_model()
        # Predict probability of spam/phishing (class 1)
        prob = model.predict_proba([message])[0][1]
        risk_score = int(prob * 100)
    except Exception as e:
        print(f"Error predicting message spam: {e}")
        # Fallback to pure heuristics if model is not loaded
        risk_score = 0
        
    # 2. Run Explainable Heuristics to generate feedback
    
    # Check for urgent/scam words
    urgency_words = ["urgent", "immediately", "action required", "suspension", "locked", "expire", "unauthorized", "verify now"]
    has_urgency = any(re.search(rf"\b{word}\b", message, re.IGNORECASE) for word in urgency_words)
    if has_urgency:
        feedback.append("The message uses urgent language typical of social engineering and phishing attacks.")
        if risk_score < 50:
            risk_score = max(risk_score, 45) # adjust score slightly for heuristics

    # Check for financial/prize words
    prize_words = ["winner", "won", "prize", "free entry", "cash", "award", "claim", "gift card", "selected", "lottery"]
    has_prize = any(re.search(rf"\b{word}\b", message, re.IGNORECASE) for word in prize_words)
    if has_prize:
        feedback.append("The message contains financial lures or claims that you have won a prize or free gift.")
        if risk_score < 50:
            risk_score = max(risk_score, 50)

    # Check for links/URLs
    if re.search(r"https?://[^\s]+|www\.[^\s]+", message):
        feedback.append("The message contains a web link. Avoid clicking links in unsolicited messages.")
        if risk_score < 40:
            risk_score = max(risk_score, 40)

    # Check for requests for sensitive info
    sensitive_words = ["password", "pin number", "ssn", "social security", "credit card", "bank transfer", "cvv", "otp"]
    has_sensitive = any(re.search(rf"\b{word}\b", message, re.IGNORECASE) for word in sensitive_words)
    if has_sensitive:
        feedback.append("The message asks for sensitive credentials or security information.")
        if risk_score < 70:
            risk_score = max(risk_score, 70)

    # Check for phone numbers/contact back requests
    if re.search(r"call\s+\+?\d{1,4}[-\s]?\d{3,4}[-\s]?\d{3,4}|text\s+to\s+\d{5,6}", message, re.IGNORECASE):
        feedback.append("The message asks you to call or text back to a specific number, a common vishing/smishing tactic.")

    # Check for excessive capitalization (shouting)
    caps_ratio = sum(1 for c in message if c.isupper()) / max(1, sum(1 for c in message if c.isalpha()))
    if caps_ratio > 0.4 and len(message) > 20:
        feedback.append("The message uses excessive capital letters, creating artificial panic.")

    # Classify prediction category
    if risk_score >= 70:
        prediction = "Phishing/Spam"
    elif risk_score >= 35:
        prediction = "Suspicious"
    else:
        prediction = "Legitimate"
        
    if not feedback:
        feedback.append("No obvious language indicators of phishing or spam were identified.")
        
    return {
        "prediction": prediction,
        "risk_score": risk_score,
        "feedback": feedback
    }
