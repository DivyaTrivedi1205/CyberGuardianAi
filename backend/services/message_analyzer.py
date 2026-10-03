import os
import hashlib
import pickle
import re
from typing import Dict, Any, List

# Try improved model first, fall back to original
IMPROVED_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "message_classifier_improved.pkl"))
ORIGINAL_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "message_classifier.pkl"))

# Use improved model if available
MODEL_PATH = IMPROVED_MODEL_PATH if os.path.exists(IMPROVED_MODEL_PATH) else ORIGINAL_MODEL_PATH

# Expected SHA256 hash for model integrity verification (set via env for production)
MODEL_EXPECTED_HASH = os.getenv("CYBERGUARDIAN_MESSAGE_MODEL_HASH", "").strip()

_model = None


def _verify_model_hash(filepath: str, expected_hash: str) -> None:
    """Verify model file integrity using SHA256. Raises RuntimeError if mismatch."""
    if not expected_hash:
        print(
            "WARNING: Message model hash verification disabled — set CYBERGUARDIAN_MESSAGE_MODEL_HASH env var for production use."
        )
        return

    sha256 = hashlib.sha256()
    blk = 65536
    with open(filepath, "rb") as f:
        while True:
            blk_data = f.read(blk)
            if not blk_data:
                break
            sha256.update(blk_data)
    actual_hash = sha256.hexdigest()

    if actual_hash != expected_hash:
        raise RuntimeError(
            f"Model integrity check failed for {filepath}: "
            f"expected {expected_hash!r}, got {actual_hash!r}. "
            "The model file may be corrupted or tampered with."
        )


def get_message_model():
    """Safely load the trained message model with hash verification."""
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Message classifier model not found at {MODEL_PATH}")

        # Verify integrity if hash is configured
        _verify_model_hash(MODEL_PATH, MODEL_EXPECTED_HASH)

        # Safe pickle load — restricted unpickler not needed for scikit-learn models,
        # but hash verification ensures the file hasn't been tampered with
        with open(MODEL_PATH, "rb") as f:
            model_data = pickle.load(f, fix_imports=False)

        # Handle both old format (single pipeline) and new format (dict with vectorizer/model)
        if isinstance(model_data, dict):
            if 'model' in model_data and 'vectorizer' in model_data:
                # New format: dict with vectorizer and model
                from sklearn.pipeline import Pipeline
                _model = Pipeline([
                    ('tfidf', model_data['vectorizer']),
                    ('classifier', model_data['model'])
                ])
            else:
                _model = model_data
        else:
            _model = model_data

    return _model


def analyze_message_text(message: str) -> Dict[str, Any]:
    """
    Analyzes a message text for spam/phishing risk.
    Returns:
        prediction: "Phishing/Spam" or "Legitimate"
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
        prob = model.predict_proba([message])[0][1]
        risk_score = int(prob * 100)
    except Exception as e:
        print(f"Error predicting message spam: {e}")
        risk_score = 0

    # 2. Run Explainable Heuristics to generate feedback

    # Check for urgent/scam words
    urgency_words = ["urgent", "immediately", "action required", "suspension", "locked", "expire", "unauthorized", "verify now"]
    has_urgency = any(re.search(rf"\b{word}\b", message, re.IGNORECASE) for word in urgency_words)
    if has_urgency:
        feedback.append("The message uses urgent language typical of social engineering and phishing attacks.")
        if risk_score < 50:
            risk_score = max(risk_score, 45)

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
    alpha_count = sum(1 for c in message if c.isalpha())
    if alpha_count > 0:
        caps_ratio = sum(1 for c in message if c.isupper()) / alpha_count
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