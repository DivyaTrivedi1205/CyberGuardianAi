#!/usr/bin/env python3
"""
Improved Password Security Analysis Service for CyberGuardian AI.

This module provides comprehensive password strength analysis with:
1. Length evaluation
2. Character composition analysis
3. Pattern detection (repeated, sequential, keyboard)
4. Common password detection
5. Entropy estimation
6. Actionable recommendations

SECURITY REQUIREMENTS MET:
- Passwords are never stored in logs
- Passwords are never sent to external APIs
- Analysis is performed locally/in-process
- No password exposure in error messages
"""

import re
import math
from typing import Dict, Any, List, Optional, Tuple


# Common passwords list (top 100 from various data breaches)
# Using a curated list that fits within reasonable memory constraints
COMMON_PASSWORDS = {
    "password", "123456", "123456789", "12345678", "qwerty", "abc123", "password1",
    "111111", "123123", "iloveyou", "admin", "letmein", "welcome", "monkey",
    "dragon", "master", "login", "sunshine", "princess", "football", "shadow",
    "1234567", "sunshine", " Princess", "654321", "superman", "qazwsx", "michael",
    "trustno1", "batman", "passw0rd", "hello", "charlie", "donald", "admin123",
    "root", "toor", "pass", "test", "guest", "user", "manager", "secret",
    "1234", "12345", "qwerty123", "1q2w3e4r", "1qaz2wsx", "password123",
    "P@ssw0rd", "p@ssword", "pass123", "Password1", "Password", "Password123",
    "qwerty12", "123321", "1234567890", "000000", "aaaaaa", "abcdef", "abcdefg",
    "123abc", "baseball", "superman", "1qaz2wsx", "football1", "iloveyou1",
    "amanda", "ashley", "butterfly", "chocolate", "dallas", "designer",
    "eagle1", "fender", "george", "harry", "hunter", "iceman", "jennifer",
    "justin", "knight", "liverpool", "master1", "matthew", "melissa", "michelle",
    "mustang", "nathan", "new york", "orange", "pa55word", "pepper", "qweasd",
    "rachel", "red123", "redsox", "runner", "soccer", "sunrise", "thunder",
    "victor", "whisky", "yellow", "zigzag", "zxcvbnm", "zxcvbn", "starwars",
    "lovely", "loveyou", "snoopy", "bonnie", "pepper1", "sandra", "alexandra",
    "alex", "alexis", "alexande", "alexis1", "amber", "americna", "anaconda",
    "angel1", "angela", "angelina", "angels", "animal", "anthony", "apollo",
    "apples", "arctic", "argentina", "ariel", "armstrong", "artemis", "asdfgh",
    "asdfghjkl", "ashley1", "ashley123", "asshole", "august", "austin", "authority",
    "avalanche", "average", "aviation", "baby", "babygirl", "backdoor", "backup",
    "badboy", "badger", "badger1", "bailey", "baker", "banana", "bandit", "bang",
    "banker", "barbara", "barcelona", "barney", "baron", "baseball1", "basketball",
    "bass", "basset", "bates", "battle", "baxter", "beacher", "beagle", "beast",
    "beatles", "beauty", "beaver", "bebo", "becca", "becker", "becky", "beer",
    "beethoven", "beetle", "begin", "behavior", "believe", "bella", "belle",
    "belly", "bengal", "benjamin", "bennett", "benson", "bentley", "berlin",
    "bernard", "bernie", "berry", "bert", "beta", "betsy", "better", "betty",
    "beverly", "beware", "bicycle", "bigmac", "bikini", "bill", "billy", "bingo",
    "bird", "birdie", "bishop", "bitch", "biteme", "bitter", "black", "black1",
    "blackcat", "blackjack", "blackout", "blacky", "blade", "blazer", "blessed",
    "blind", "bliss", "blitz", "block", "blogger", "blonde", "blondie", "blood",
    "bloom", "blow", "blowjob", "blowme", "blue", "bluebird", "blueeyes", "blues",
    "bmw", "bobbie", "bobby", "bobcat", "bogart", "bohica", "bomber", "bond",
    "bond007", "bone", "bonehead", "bones", "bonus", "book", "boomer", "boomers",
    "boots", "bootsie", "booty", "bora", "border", "bored", "boris", "bosco",
    "boss", "boston", "bottle", "bottom", "boubie", "bougie", "boulder", "bounty",
    "boxer", "bradley", "brain", "brandi", "brandon", "brandy", "braves", "brazil",
    "breast", "brian", "brick", "bridge", "bridget", "briefs", "bright", "brigitte",
    "bring", "broad", "bronco", "bronx", "brooke", "brother", "brown", "browny",
    "browser", "bruce", "bruiser", "bruno", "brutus", "buck", "bucket", "buckle",
    "buffalo", "buffet", "buffy", "bugger", "bugs", "build", "bullet", "bullseye",
    "bullfrog", "bulldog", "bumble", "bunker", "bunny", "bureauboi", "burger",
    "bureaucrat", "burn", "burner", "bush", "buster", "busy", "butch", "butler",
    "butt", "butter", "buttercup", "butterfly", "butthead", "buttme", "button",
    "buzz", "buzzer", "byte", "cabbage", "cable", "caesar", "cactus", "caitlin",
    "calendar", "cali", "califor", "calvin", "camaro", "camera", "camp", "campbell",
    "camping", "campus", "cancer", "candace", "candice", "candle", "candy", "canela",
    "cannon", "cantaloupe", "cannery", "cannibal", "cannonball", "canon", "canuck",
    "canyon", "cape", "caper", "capital", "capone", "caprice", "capri", "captain",
    "cara", "caravan", "carbon", "card", "cardinal", "cardiff", "cardshark",
    "carebear", "cargo", "carina", "carl", "carla", "carlton", "carmen", "carmen1",
    "carmen12", "carmen123", "carmine", "carol", "carol1", "carol123", "carole",
    "caroline", "carolyn", "carpedie", "carpet", "carrie", "carroll", "carry",
    "carter", "cartman", "cartoon", "casa", "casandra", "cascade", "casey", "casey1",
    "cash", "cashflow", "caspian", "cass", "cassandra", "cassie", "caster",
    "castillo", "castle", "castor", "cat", "catalina", "catfish", "catman", "catnip",
    "cats", "cathy", "cattle", "catty", "catwoman", "caucasian", "caught", "cause",
    "cavalier", "cavern", "cayman", "cayman1", "ceasar", "cecelia", "cecile",
    "cecilia", "cecily", "celeb", "celebrate", "celestial", "celica", "celine",
    "celtic", "celtics", "cement", "cemetery", "central", "century", "cerberus",
    "cereal", "ceremony", "ceres", "certified", "cervix", "chacha", "chachi",
    "chad", "chaela", "chai", "chain", "chains", "chaingang", "chair", "chalk",
    "challenge", "chamber", "champ", "champion", "champlain", "chance", "chancer",
    "change", "channel", "chantal", "chao", "chaos", "chapman", "chapter", "charcoal",
    "charlene", "charles", "charley", "charlie", "charlie1", "charlie123", "charlotte",
    "charlott", "charming", "charon", "chase", "chaser", "chassis", "chatter",
    "chavez", "cheater", "check", "checker", "cheeky", "cheer", "cheerio",
    "cheers", "cheese", "cheese1", "cheese123", "cheeseburger", "cheesy", "chef",
    "chelsea", "chelsea1", "chelsea123", "chemical", "chemist", "chemy", "cherry",
    "chess", "chessie", "chester", "chestnut", "chevelle", "chevychevvy", "chevy",
    "chevy1", "chex", "chic", "chick", "chicken", "chicken1", "chico", "chicane",
    "chicano", "chicken", "chicken123", "chico1", "chief", "chigau", "chigma",
    "child", "children", "chill", "chillout", "chilli", "chimera", "chimp",
    "china", "chinese", "chip", "chipmunk", "chips", "chloe", "chloe1", "chocolate",
    "chocolate1", "chocolates", "choke", "cholly", "chong", "choose", "chopper",
    "chops", "chord", "chortle", "chorus", "choucho", "chow", "chowder", "christ",
    "christ1", "christa", "christian", "christmas", "christopher", "chromium",
    "chronic", "chronicle", "chronos", "chubby", "chuck", "chuckles", "chuckie",
    "chucky", "chul", "chump", "chunk", "chunky", "churon", "chute", "church",
    "cinder", "cindy", "cindy1", "cinema", "cinnamon", "circle", "circus",
    "circus1", "cirque", "cirrus", "cisco", "cissy", "citadel", "citizen",
    "citroen", "city", "civic", "civil", "clam", "clamber", "clammy", "clank",
    "clap", "claret", "clarinet", "clarinetist", "clarissa", "clark", "clash",
    "class", "classic", "classy", "clatter", "claude", "claudia", "claudio",
    "claus", "claw", "clay", "clayton", "clean", "clear", "clearwater", "cleat",
    "cleats", "cleave", "clef", "cleft", "clem", "clement", "clementine", "cleo",
    "cleopatra", "cletus", "cliche", "click", "client", "cliff", "clifford",
    "clifton", "climb", "climber", "clinch", "clinger", "clint", "clinton",
    "clio", "clipeus", "clipper", "clips", "clique", "clistix", "cloaca",
    "cloche", "clock", "clockwork", "clog", "cloister", "clone", "close",
    "closer", "cloth", "clothes", "clothing", "cloud", "cloudy", "clover",
    "clovis", "club", "cluck", "clue", "clueless", "clump", "clumsy", "clunk",
    "cluster", "clutch", "coach", "coal", "coast", "coastal", "coat", "cobain",
    "cobra", "coca", "cock", "cockapoo", "cockatiel", "cockatoo", "cockroach",
    "cocktail", "coco", "cocoa", "coconut", "cod", "cody", "coffee", "coffin",
    "coil", "coin", "coke", "cold", "coldfire", "coldplay", "coldwave", "cole",
    "colin", "collage", "collapse", "collar", "collect", "collector", "colleen",
    "college", "collie", "collier", "collier1", "collin", "colombia", "colon",
    "colonel", "color", "colorado", "colorful", "colt", "columbia", "columbus",
    "coma", "come", "comedy", "comet", "comfort", "comic", "command", "commander",
    "commencement", "comment", "commerce", "comet", "comedy", "common", "commune",
    "compact", "company", "compare", "compass", "complete", "complex", "comply",
    "component", "compose", "composite", "composition", "comprehend", "compress",
    "comprise", "compromise", "compromise", "compulsory", "computer", "comrade",
    "con", "conan", "conceal", "concede", "conceive", "concept", "concern",
    "concert", "conclude", "concrete", "concept", "concern", "concert", "conclude",
    "concrete", "concur", "condemn", "condense", "condiment", "condition", "condo",
    "condor", "conduct", "confer", "confess", "confetti", "confide", "confirm",
    "conflict", "conform", "confuse", "congratulate", "congress", "conjure",
    "connect", "connection", "conquest", "conquer", "conscience", "conscious",
    "conscript", "consensus", "consent", "consequence", "conservative",
    "consider", "consist", "constant", "constitute", "constraint", "construct",
    "construe", "consult", "consultant", "consulting", "consummate", "consume",
    "consumer", "consumption", "contact", "contain", "contemporary", "contempt",
    "contend", "content", "contest", "context", "continent", "continue", "continuity",
    "continuous", "contour", "contract", "contractor", "contrary", "contrary",
    "contrast", "contribute", "contrivance", "contrive", "control", "controversy",
    "contusion", "convene", "convenient", "convent", "convergence", "conversation",
    "converse", "convert", "convey", "convex", "convict", "convince", "convoke",
    "convoy", "convulse", "convulsion", "cook", "cookie", "cooking", "cool",
    "cooler", "coon", "coop", "cooperate", "cooperation", "cooperative", "coordinator",
    "cop", "cope", "copier", "copper", "copy", "coral", "cord", "cordial", "core",
    "cork", "corn", "corner", "corporate", "corps", "corpse", "corpus", "correct",
    "correction", "correspond", "corridor", "corrupt", "cortex", "cosmic",
    "cosmos", "cost", "costume", "cot", "cottage", "cotton", "couch", "cough",
    "could", "council", "counsel", "counselor", "count", "countdown", "counter",
    "country", "county", "couple", "coupon", "courage", "courier", "course",
    "court", "courtesy", "cover", "covet", "cow", "coward", "cowboy", "crab",
    "crack", "cracker", "crackle", "cradle", "craft", "craftsman", "crag",
    "craig", "cramp", "crane", "crane1", "crank", "cranky", "crash", "crass",
    "crate", "crave", "crawl", "crawfish", "crazy", "cream", "create", "creation",
    "creative", "creature", "credit", "creditor", "creek", "creep", "creme",
    "creole", "crepe", "crescent", "crest", "crew", "crib", "crime", "crimp",
    "crimson", "cringe", "crinkle", "cripple", "crisp", "croak", "crochet",
    "crock", "crockery", "crocodile", "crocus", "croft", "crony", "crook",
    "croon", "crop", "cross", "crow", "crowd", "crown", "crucial", "crude",
    "cruel", "cruise", "cruiser", "crumb", "crumble", "crummy", "crump", "crumper",
    "crumple", "crunch", "crusade", "crush", "crust", "cry", "crysanthemum",
    "crypt", "crystal", "cub", "cubic", "cubist", "cubit", "cuckoo", "cuddle",
    "cuddly", "cue", "cuff", "culinary", "culminate", "culpable", "culture",
    "culvert", "cumbersome", "cumulus", "cunning", "cunt", "cup", "cupcake",
    "cupid", "cupola", "cur", "curate", "curb", "curiosity", "curious", "curl",
    "curry", "curse", "cursor", "curtain", "curve", "cushion", "custard",
    "custody", "custom", "customer", "cut", "cute", "cycle", "cylinder",
    "cynical", "cypress", "czar"
}

# Common patterns to detect
PATTERN_PATTERNS = {
    'repeated_chars': re.compile(r'(.)\1{2,}'),  # aaa, 111, !!!
    'sequential_letters': re.compile(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', re.IGNORECASE),
    'sequential_numbers': re.compile(r'(012|123|234|345|456|567|678|789|890)'),
    'keyboard_patterns': re.compile(r'(qwerty|asdf|zxcv|qazwsx|1qaz2wsx)', re.IGNORECASE),
    'year_pattern': re.compile(r'\b(19|20)\d{2}\b'),  # Years like 1999, 2024
    'date_pattern': re.compile(r'\b(0[1-9]|1[0-2])[/\-](0[1-9]|[12]\d|3[01])[/\-](\d{2,4})\b'),  # MM/DD/YYYY
    'predictable_sub': re.compile(r'(@|4|3|1|0|5|7)', re.IGNORECASE),  # Common leetspeak
}

# Common prefixes/suffixes
PREDICTABLE_PREFIXES = ('admin', 'user', 'test', 'guest', 'demo', 'password', 'login', 'welcome')
PREDICTABLE_SUFFIXES = ('1', '123', '1234', '12345', '123456', '!', '!', '!')


def calculate_entropy(password: str) -> float:
    """
    Calculate Shannon entropy of the password.
    Higher entropy = more randomness = harder to guess.
    """
    if not password:
        return 0.0

    # Character set size
    charset_size = 0
    if re.search(r'[a-z]', password):
        charset_size += 26
    if re.search(r'[A-Z]', password):
        charset_size += 26
    if re.search(r'\d', password):
        charset_size += 10
    if re.search(r'[^A-Za-z0-9]', password):
        charset_size += 32  # Common symbols

    if charset_size == 0:
        return 0.0

    # Entropy = length * log2(charset_size)
    entropy = len(password) * math.log2(charset_size)
    return round(entropy, 2)


def check_common_password(password: str) -> Tuple[bool, Optional[str]]:
    """
    Check if password is in the common passwords list.
    Returns (is_common, matched_password)
    """
    if not password:
        return False, None

    # Check exact match
    if password.lower() in COMMON_PASSWORDS:
        return True, password.lower()

    # Check for very common patterns with numbers
    base_patterns = ['password', 'qwerty', 'admin', 'welcome', 'monkey', 'dragon']
    for pattern in base_patterns:
        if pattern in password.lower():
            # Check if it's a predictable variant like password123
            if re.match(rf'^{re.escape(pattern)}\d+$', password.lower()):
                return True, pattern

    return False, None


def detect_patterns(password: str) -> List[Dict[str, Any]]:
    """
    Detect various password patterns.
    """
    patterns_found = []

    # Check for repeated characters
    match = PATTERN_PATTERNS['repeated_chars'].search(password)
    if match:
        patterns_found.append({
            'type': 'repeated_characters',
            'description': 'Contains repeated characters (e.g., "aaa", "111")',
            'detected': True,
            'severity': 'medium'
        })

    # Check for sequential letters
    match = PATTERN_PATTERNS['sequential_letters'].search(password)
    if match:
        patterns_found.append({
            'type': 'sequential_letters',
            'description': f'Contains sequential letters: "{match.group(1)}"',
            'detected': True,
            'severity': 'medium'
        })

    # Check for sequential numbers
    match = PATTERN_PATTERNS['sequential_numbers'].search(password)
    if match:
        patterns_found.append({
            'type': 'sequential_numbers',
            'description': f'Contains sequential numbers: "{match.group(1)}"',
            'detected': True,
            'severity': 'medium'
        })

    # Check for keyboard patterns
    match = PATTERN_PATTERNS['keyboard_patterns'].search(password)
    if match:
        patterns_found.append({
            'type': 'keyboard_pattern',
            'description': f'Contains keyboard pattern: "{match.group(1)}"',
            'detected': True,
            'severity': 'high'
        })

    # Check for year
    match = PATTERN_PATTERNS['year_pattern'].search(password)
    if match:
        patterns_found.append({
            'type': 'year',
            'description': f'Contains a year: "{match.group(0)}"',
            'detected': True,
            'severity': 'low'
        })

    # Check for date pattern
    match = PATTERN_PATTERNS['date_pattern'].search(password)
    if match:
        patterns_found.append({
            'type': 'date',
            'description': f'Contains a date pattern: "{match.group(0)}"',
            'detected': True,
            'severity': 'low'
        })

    # Check for predictable substitutions
    matches = PATTERN_PATTERNS['predictable_sub'].findall(password)
    if len(matches) >= 2:
        patterns_found.append({
            'type': 'predictable_substitution',
            'description': 'Uses predictable leetspeak substitutions (e.g., @ for a, 3 for e)',
            'detected': True,
            'severity': 'medium'
        })

    # Check for predictable prefixes
    for prefix in PREDICTABLE_PREFIXES:
        if password.lower().startswith(prefix):
            patterns_found.append({
                'type': 'predictable_prefix',
                'description': f'Has predictable prefix: "{prefix}"',
                'detected': True,
                'severity': 'medium'
            })
            break

    # Check for predictable suffixes
    for suffix in PREDICTABLE_SUFFIXES:
        if password.endswith(suffix):
            patterns_found.append({
                'type': 'predictable_suffix',
                'description': f'Has predictable suffix: "{suffix}"',
                'detected': True,
                'severity': 'low'
            })
            break

    return patterns_found


def analyze_password(password: str) -> Dict[str, Any]:
    """
    Comprehensive password analysis.

    Returns structured analysis including:
    - Score (0-100)
    - Strength classification
    - Detailed findings
    - Recommendations
    - Character composition details
    - Entropy estimate
    """
    result = {
        'score': 0,
        'strength': 'Very Weak',
        'findings': [],
        'recommendations': [],
        'length': len(password),
        'character_classes': {
            'lowercase': 0,
            'uppercase': 0,
            'digits': 0,
            'symbols': 0
        },
        'patterns_detected': [],
        'common_password': False,
        'common_password_match': None,
        'entropy_estimate': 0.0,
        'crack_time_estimate': None
    }

    # Handle empty password
    if not password:
        result['score'] = 0
        result['strength'] = 'Very Weak'
        result['findings'].append('Password is empty')
        result['recommendations'].append('Enter a password to analyze')
        return result

    # Calculate character composition
    result['character_classes']['lowercase'] = len(re.findall(r'[a-z]', password))
    result['character_classes']['uppercase'] = len(re.findall(r'[A-Z]', password))
    result['character_classes']['digits'] = len(re.findall(r'\d', password))
    result['character_classes']['symbols'] = len(re.findall(r'[^A-Za-z0-9]', password))

    # Score components
    score = 0

    # 1. LENGTH (max 40 points)
    # Short passwords: heavily penalized
    if len(password) < 6:
        score += 5
        result['findings'].append('Password is very short (less than 6 characters)')
        result['recommendations'].append('Use at least 12 characters for adequate security')
    elif len(password) < 8:
        score += 10
        result['findings'].append('Password is short (less than 8 characters)')
        result['recommendations'].append('Use at least 12 characters for better security')
    elif len(password) < 12:
        score += 20
        result['findings'].append('Password length is acceptable but could be longer')
        result['recommendations'].append('Consider using 12+ characters or a passphrase')
    elif len(password) < 16:
        score += 30
        result['findings'].append('Password has good length')
    else:
        score += 40
        result['findings'].append('Password length is excellent')

    # 2. CHARACTER COMPOSITION (max 40 points)
    char_class_score = 0

    if result['character_classes']['lowercase'] > 0:
        char_class_score += 10
    else:
        result['findings'].append('No lowercase letters')
        result['recommendations'].append('Add lowercase letters')

    if result['character_classes']['uppercase'] > 0:
        char_class_score += 10
    else:
        result['findings'].append('No uppercase letters')
        result['recommendations'].append('Add uppercase letters')

    if result['character_classes']['digits'] > 0:
        char_class_score += 10
    else:
        result['findings'].append('No digits')
        result['recommendations'].append('Add numbers')

    if result['character_classes']['symbols'] > 0:
        char_class_score += 10
    else:
        result['findings'].append('No symbols/punctuation')
        result['recommendations'].append('Add symbols or punctuation marks')

    # Bonus for diversity
    classes_used = sum(1 for v in result['character_classes'].values() if v > 0)
    if classes_used == 4:
        score += 10
        result['findings'].append('Excellent character diversity (lowercase, uppercase, digits, symbols)')
    elif classes_used >= 3:
        score += 5
        result['findings'].append('Good character diversity')

    score += char_class_score

    # 3. COMMON PASSWORD CHECK (penalty up to 50 points)
    is_common, match = check_common_password(password)
    result['common_password'] = is_common
    result['common_password_match'] = match

    if is_common:
        score -= 50
        result['findings'].append(f'Contains common password: "{match}"')
        result['recommendations'].append('Avoid common passwords and easily guessable words')

    # 4. PATTERN DETECTION (penalties)
    patterns = detect_patterns(password)
    result['patterns_detected'] = patterns

    for pattern in patterns:
        if pattern['severity'] == 'high':
            score -= 15
        elif pattern['severity'] == 'medium':
            score -= 10
        elif pattern['severity'] == 'low':
            score -= 5

    # 5. ENTROPY CALCULATION
    result['entropy_estimate'] = calculate_entropy(password)

    # Bonus for high entropy
    if result['entropy_estimate'] >= 60:
        score += 5
    elif result['entropy_estimate'] >= 50:
        score += 3

    # 6. PREDICTABLE STRUCTURE
    # Check if password is mostly predictable (e.g., "password" + year)
    if not is_common and patterns:
        predictable_count = sum(1 for p in patterns if p['severity'] in ('medium', 'high'))
        if predictable_count >= 2:
            score -= 5
            result['findings'].append('Password structure appears somewhat predictable')
            result['recommendations'].append('Avoid predictable patterns like names, years, or common words')

    # Clamp score to 0-100
    score = max(0, min(100, score))
    result['score'] = score

    # Determine strength level
    if score >= 80:
        result['strength'] = 'Very Strong'
        result['findings'].append('Password is highly resistant to brute-force attacks')
        result['recommendations'].append('This password provides excellent security')
    elif score >= 60:
        result['strength'] = 'Strong'
        result['findings'].append('Password is reasonably secure')
        result['recommendations'].append('Good password, consider adding more length or complexity')
    elif score >= 40:
        result['strength'] = 'Moderate'
        result['findings'].append('Password has some security issues')
        result['recommendations'].append('Consider making it longer and adding more character types')
    elif score >= 20:
        result['strength'] = 'Weak'
        result['findings'].append('Password has significant security issues')
        result['recommendations'].append('Strongly recommend creating a more secure password')
    else:
        result['strength'] = 'Very Weak'
        result['findings'].append('Password is extremely vulnerable to attacks')
        result['recommendations'].append('Create a completely new password with more length and variety')

    # Generate crack time estimate (qualitative, not mathematical certainty)
    result['crack_time_estimate'] = generate_crack_time_estimate(result['score'], result['entropy_estimate'])

    # Remove duplicate findings
    result['findings'] = list(dict.fromkeys(result['findings']))
    result['recommendations'] = list(dict.fromkeys(result['recommendations']))

    return result


def generate_crack_time_estimate(score: int, entropy: float) -> Dict[str, Any]:
    """
    Generate a qualitative crack time estimate.
    This is NOT a precise calculation - it's based on general security principles.
    """
    if score >= 80:
        return {
            'text': 'Years to centuries (for modern hardware)',
            'notes': 'This password would take a very long time to crack using current technology'
        }
    elif score >= 60:
        return {
            'text': 'Weeks to months (for modern hardware)',
            'notes': 'This password provides reasonable security for most purposes'
        }
    elif score >= 40:
        return {
            'text': 'Hours to days (for modern hardware)',
            'notes': 'This password could be cracked with moderate effort'
        }
    elif score >= 20:
        return {
            'text': 'Minutes to hours (for modern hardware)',
            'notes': 'This password is easily crackable and should be improved'
        }
    else:
        return {
            'text': 'Seconds to minutes (for modern hardware)',
            'notes': 'This password is extremely vulnerable and should be changed immediately'
        }


def format_analysis_for_api(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the analysis for the API response.
    Converts internal structure to API-compatible format.
    """
    return {
        'score': analysis['score'],
        'strength': analysis['strength'],
        'findings': analysis['findings'],
        'recommendations': analysis['recommendations'],
        'length': analysis['length'],
        'character_classes': analysis['character_classes'],
        'patterns_detected': analysis['patterns_detected'],
        'common_password': analysis['common_password'],
        'entropy_estimate': analysis['entropy_estimate'],
        'crack_time_estimate': analysis['crack_time_estimate']
    }


if __name__ == '__main__':
    # Test the improved password service
    test_passwords = [
        "password",
        "Password123!",
        "Tr0ub4dor&3",
        "Correct Horse Battery Staple",
        "abc123",
        "aA1!",
        "P@$$w0rd2024!",
        "qwerty123",
        "this is a very long passphrase with many words",
    ]

    for pwd in test_passwords:
        print(f"\n{'='*60}")
        print(f"Password: {pwd}")
        print(f"{'='*60}")
        result = analyze_password(pwd)
        print(f"Score: {result['score']}/100")
        print(f"Strength: {result['strength']}")
        print(f"Length: {result['length']}")
        print(f"Character Classes: {result['character_classes']}")
        print(f"Entropy: {result['entropy_estimate']}")
        print(f"Patterns: {len(result['patterns_detected'])}")
        print("Findings:")
        for f in result['findings']:
            print(f"  - {f}")
        print("Recommendations:")
        for r in result['recommendations']:
            print(f"  - {r}")
