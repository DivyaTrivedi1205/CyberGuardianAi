from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class RiskExplanation(BaseModel):
    category: str
    score: int
    meaning: str
    contributing_factors: List[str]
    missing_detectors: List[str]
    recommendations: List[str]
    limitations: List[str]

class UnifiedAssessment(BaseModel):
    overall_risk_score: int
    overall_risk_category: str
    explanations: RiskExplanation

def normalize_score(score: Any, is_probability: bool = False) -> Optional[int]:
    """Normalize score to 0-100 safely."""
    try:
        if score is None:
            return None
        val = float(score)
        if val != val: # NaN check
            return None
        if val == float('inf') or val == float('-inf'):
            return None
            
        if is_probability:
            val = val * 100
        return int(max(0, min(100, val)))
    except (ValueError, TypeError):
        return None

def compute_unified_risk(
    model_score: Optional[int], 
    reputation_status: Optional[str] = None,
    heuristic_score: Optional[int] = None,
    domain: str = "general",
    explanations: List[str] = None
) -> UnifiedAssessment:
    """
    Deterministically fuses different risk signals into a unified assessment.
    Returns structured explanation.
    """
    components = []
    missing = []
    
    # Defaults
    final_score = 0
    highest_risk = 0
    
    if explanations is None:
        explanations = []

    # Process reputation first (Highest priority override if Verified)
    if reputation_status == "verified_threat":
        highest_risk = 100
        components.append("✅ CrowdShield Community Blocklist (Verified Threat)")
    elif reputation_status == "pending":
        highest_risk = max(highest_risk, 60)
        components.append("⚠️ CrowdShield Unverified Community Reports")
    else:
        missing.append("Verified Community Reports")

    # Process ML model score
    norm_val = normalize_score(model_score)
    if norm_val is not None:
        highest_risk = max(highest_risk, norm_val)
        components.append(f"🤖 Machine Learning Model Confidence: {norm_val}/100")
    else:
        missing.append("ML Model Assessment unavailable or failed")
        
    # Process Heuristics
    norm_heur = normalize_score(heuristic_score)
    if norm_heur is not None:
        highest_risk = max(highest_risk, norm_heur)
        components.append(f"🔍 Static Heuristic Checks: {norm_heur}/100")
    
    final_score = highest_risk

    # Never treat a failed detector as 0 risk silently
    if norm_val is None and norm_heur is None and reputation_status is None:
        final_score = 50 # Unknown/Suspicious baseline

    if final_score >= 70:
        category = "High Risk"
        meaning = "This content is highly likely to be malicious."
        if domain == "url":
            recommendation = ["Do NOT click or enter credentials.", "Close the page immediately."]
        elif domain == "message":
            recommendation = ["Do NOT reply.", "Do NOT click links.", "Delete the message."]
        elif domain == "password":
            recommendation = ["DO NOT use this password.", "Use a password manager to generate a complex password."]
        else:
            recommendation = ["Avoid interacting with this content.", "Assume it is fabricated/malicious."]
    elif final_score >= 35:
        category = "Suspicious" if domain != "password" else "Weak Password"
        meaning = "This content exhibits some questionable traits." if domain != "password" else "This password is weak and can be cracked easily."
        recommendation = ["Proceed with extreme caution.", "Verify through an alternate channel."] if domain != "password" else ["Add length, uppercase, numbers, and symbols."]
    else:
        category = "Low Risk" if domain != "password" else "Strong Password"
        meaning = "No significant immediate threats detected." if domain != "password" else "This password is secure and resistant to common attacks."
        recommendation = ["Standard caution applies."] if domain != "password" else ["Ensure this password is not reused across multiple accounts."]
        
    if norm_val is None and norm_heur is None:
        meaning += " (Warning: Analysis engines were unavailable, relying on default safe-fail metrics)"

    return UnifiedAssessment(
        overall_risk_score=final_score,
        overall_risk_category=category,
        explanations=RiskExplanation(
            category=category,
            score=final_score,
            meaning=meaning,
            contributing_factors=components + explanations,
            missing_detectors=missing,
            recommendations=recommendation,
            limitations=["Model scores represent heuristics and statistical probability, not guaranteed truth.",
                         "Risk assessment can have false positives and false negatives."]
        )
    )
