import re
from typing import Dict, Any, List

# Definitions of keyword triggers
PSYCHOLOGY_RULES = {
    "urgency": {
        "keywords": [
            r"\bhurry\b", r"\bact now\b", r"\bimmediately\b", r"\b24 hours\b", r"\b48 hours\b",
            r"\bverify now\b", r"\baction required\b", r"\bdeadline\b", r"\bexpire\b",
            r"\blast chance\b", r"\brunning out\b", r"\bquick\b", r"\brespond immediately\b"
        ],
        "name": "Urgency",
        "description": "Manipulates the target by imposing a strict time constraint to bypass logical review.",
        "bias": "Hyperbolic Discounting (choosing immediate relief over long-term security checks)",
        "tip": "Stop and take a breath. Scammers rely on panic to rush you. Verify deadlines independently through official contacts."
    },
    "authority": {
        "keywords": [
            r"\birs\b", r"\bpaypal\b", r"\bnetflix\b", r"\bamazon\b", r"\bapple support\b",
            r"\bsecurity team\b", r"\bhelpdesk\b", r"\badmin\b", r"\bofficer\b", r"\bpolice\b",
            r"\bchief\b", r"\bmanager\b", r"\bexecutive\b", r"\bdepartment of\b", r"\bcourt\b"
        ],
        "name": "Authority",
        "description": "Spoofs official institutions, organizations, or corporate figures to command obedience.",
        "bias": "Authority Bias (the tendency to trust and obey figures of power uncritically)",
        "tip": "Legitimate organizations will never demand credentials or funds transfer over SMS or email link redirects."
    },
    "fear": {
        "keywords": [
            r"\bsuspended\b", r"\bsuspension\b", r"\blocked\b", r"\bcompromised\b", r"\bunauthorized\b",
            r"\bfrozen\b", r"\billegal\b", r"\bviolation\b", r"\bterminated\b", r"\bprosecuted\b",
            r"\bfine\b", r"\bpenalty\b", r"\barrest\b", r"\bsecurity alert\b"
        ],
        "name": "Fear / Scare Tactics",
        "description": "Threatens negative consequences (legal actions, account closures) to create stress.",
        "bias": "Loss Aversion (people are highly motivated to avoid immediate losses or punishments)",
        "tip": "Do not reply to threats. Access your profile by manually typing the official domain name in a new tab."
    },
    "greed": {
        "keywords": [
            r"\bwinner\b", r"\bwon\b", r"\bprize\b", r"\bcash prize\b", r"\bfree gift\b",
            r"\breward\b", r"\bvoucher\b", r"\bclaim\b", r"\bbonus\b", r"\blottery\b",
            r"\bfree entry\b", r"\bmillions\b", r"\breimbursement\b", r"\bcommission\b"
        ],
        "name": "Greed / Gain Lures",
        "description": "Baiting the target with financial winnings, free gifts, or lucrative opportunities.",
        "bias": "Optimism Bias & Risk Ignorance (exaggerated expectation of unexpected good fortune)",
        "tip": "If an offer sounds too good to be true, it is. Unsolicited lottery winnings or cash prizes are classic baits."
    },
    "trust": {
        "keywords": [
            r"\bfriend\b", r"\bfamily\b", r"\bbuddy\b", r"\bnephew\b", r"\bmom\b", r"\bdad\b",
            r"\bcharity\b", r"\bdonation\b", r"\bneed a favor\b", r"\bare you free\b",
            r"\bhelp me\b", r"\bcolleague\b", r"\bhey dear\b", r"\bquick favor\b"
        ],
        "name": "Trust / Empathy",
        "description": "Exploits helpfulness or personal connections by masquerading as family, friends, or charities.",
        "bias": "In-Group Favoritism & Empathy Gap (willingness to bend rules to help a close contact)",
        "tip": "Double-check with your contact through an independent voice call to ensure their profile has not been hacked."
    },
    "curiosity": {
        "keywords": [
            r"\blook at this\b", r"\bis this you\b", r"\bshocking video\b", r"\bnew photos\b",
            r"\binvoice attached\b", r"\breceipt\b", r"\bpayment doc\b", r"\btracking info\b",
            r"\bparcel delivery\b", r"\bshipping receipt\b", r"\bclick here to see\b"
        ],
        "name": "Curiosity",
        "description": "Intrigues the target to open links or files out of speculation or desire to know.",
        "bias": "Information Gap Theory (irresistible urge to close the gap between what we know and what we do not)",
        "tip": "Never open unexpected files or click tracking links for packages you did not order."
    }
}

def analyze_scam_psychology(text: str) -> Dict[str, Any]:
    """
    Analyzes content to identify the cognitive triggers and psychological manipulation.
    """
    cleaned_text = text.lower().strip()
    scores = {}
    explanations = []
    tips = []
    
    if not cleaned_text:
        return {
            "scores": {k: 0 for k in PSYCHOLOGY_RULES.keys()},
            "explanations": [],
            "tips": ["No text provided for analysis."]
        }

    # Evaluate each rule
    for key, rule in PSYCHOLOGY_RULES.items():
        matches = []
        for pattern in rule["keywords"]:
            found = re.findall(pattern, cleaned_text)
            if found:
                # Add unique keyword name (removing regex borders)
                keyword_clean = pattern.replace(r"\b", "").replace(r"\s+", " ")
                matches.append(keyword_clean)
                
        # Calculate trigger level based on match frequency
        match_count = len(matches)
        if match_count == 0:
            score = 0
        elif match_count == 1:
            score = 45
        elif match_count == 2:
            score = 75
        else:
            score = 95
            
        # Additional boosting indicators
        if key == "urgency" and ("!!!" in text or text.isupper()):
            score = min(score + 15, 100) if score > 0 else 30
            
        scores[key] = score
        
        if score > 0:
            explanations.append(
                f"{rule['name']} detected ({score}%): triggered by keywords {matches}. {rule['description']} Exploits {rule['bias']}."
            )
            tips.append(rule["tip"])
            
    # If no triggers found, return a default secure message
    if not explanations:
        tips.append("No common psychological scam manipulation tactics were found in this content.")
        
    return {
        "scores": scores,
        "explanations": explanations,
        "tips": list(set(tips))  # remove duplicate tips
    }
