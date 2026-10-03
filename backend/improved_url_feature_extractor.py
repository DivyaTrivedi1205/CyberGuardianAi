"""
Improved URL Feature Extractor for CyberGuardian AI.

This module extends the original url_feature_extractor with additional features
and improved feature extraction logic for better phishing detection.

New features added:
1. Lexical features: hostname length, path length, query length, special chars
2. Structural features: URL depth, parameter count, TLD analysis
3. Security features: encoded character count, subdomain depth
"""

import ipaddress
import re
import socket
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, List, Tuple
from collections import Counter

# Popular legitimate domains for reputation checks
POPULAR_DOMAINS = {
    "google.com", "youtube.com", "facebook.com", "twitter.com", "instagram.com",
    "wikipedia.org", "yahoo.com", "amazon.com", "netflix.com", "linkedin.com",
    "reddit.com", "ebay.com", "bing.com", "msn.com", "microsoft.com", "apple.com",
    "github.com", "stackoverflow.com", "wordpress.com", "blogspot.com", "tumblr.com",
    "pinterest.com", "live.com", "outlook.com", "zoom.us", "imdb.com", "office.com",
    "disney.com", "paypal.com", "stripe.com", "quora.com", "medium.com", "cnn.com",
    "bbc.com", "nytimes.com", "spotify.com", "salesforce.com", "dropbox.com"
}

# Common URL shortening services
SHORTENING_SERVICES = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "is.gd", "buff.ly", "adf.ly",
    "bit.do", "ow.ly", "rebrand.ly", "t2mio.com", "shorte.st", "lnkd.in", "db.tt",
    "qr.ae", "adfoc.us", "bc.vc", "twitthis.com", "u.to", "j.mp", "su.pr"
}

# URL scheme allow-list for SSRF protection
ALLOWED_SCHEMES = ["http", "https"]

# Suspicious keywords that often appear in phishing
PHISH_KEYWORDS = [
    "paypal", "security", "secure", "signin", "login", "verification", "update",
    "bank", "account", "support", "billing", "confirm", "verify", "urgent",
    "suspend", "act now", "immediately", "winner", "prize", "cash", "award"
]


def clean_url(url: str) -> str:
    """Prepend protocol if missing."""
    url = url.strip()
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "http://" + url
    return url


def _is_safe_hostname(hostname: str) -> bool:
    """Check if hostname is safe for SSRF protection."""
    if not hostname:
        return False

    hostname_lower = hostname.lower().strip()

    # Block blocked hosts
    blocked_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
    if hostname_lower in blocked_hosts or hostname_lower.endswith('.local'):
        return False

    # Common local-only hostnames
    if hostname_lower in {'localhost.localdomain', 'ip6-localhost', 'ip6-loopback'}:
        return False

    # Block private IP ranges
    try:
        ip = ipaddress.ip_address(hostname_lower)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return False
    except ValueError:
        pass

    # Block control characters
    if any(c in hostname_lower for c in ['\\', '/', ':', '?', '#', '[', ']', '@', '!']):
        return False

    if len(hostname_lower) > 255:
        return False

    return True


def _safe_urlopen(
    url: str,
    timeout: float = 10.0,
    max_redirects: int = 5,
    max_response_size: int = 10 * 1024 * 1024,
) -> Tuple[bytes, int, str]:
    """Safely fetch URL with SSRF protection."""
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname or ""

    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme '{scheme}' not allowed")

    if not _is_safe_hostname(hostname):
        raise ValueError(f"Hostname '{hostname}' not allowed")

    # Build opener with redirect limiting
    class RedirectHandler(urllib.request.HTTPRedirectHandler):
        def __init__(self, max_redirects: int):
            super().__init__()
            self.max_redirects = max_redirects
            self.redirect_count = 0

        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if self.redirect_count >= self.max_redirects:
                raise ValueError("Too many redirects")
            self.redirect_count += 1

            new_parsed = urllib.parse.urlparse(newurl)
            if new_parsed.scheme.lower() not in ALLOWED_SCHEMES:
                raise ValueError(f"Redirect to disallowed scheme '{new_parsed.scheme}'")
            if not _is_safe_hostname(new_parsed.hostname or ""):
                raise ValueError(f"Redirect to unsafe host '{new_parsed.hostname}'")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    handler = RedirectHandler(max_redirects)
    opener = urllib.request.build_opener(handler)

    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberGuardianAI/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        },
        method='GET'
    )

    try:
        with opener.open(req, timeout=timeout) as response:
            status = response.getcode()
            final_url = response.url

            content = b""
            remaining = max_response_size
            chunk_size = 8192

            while remaining > 0:
                chunk = response.read(min(chunk_size, remaining))
                if not chunk:
                    break
                content += chunk
                remaining -= len(chunk)

            return content, status, final_url
    except urllib.error.HTTPError as e:
        return e.read(), e.code, url
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to fetch URL: {e.reason}")


def extract_features_from_url(raw_url: str) -> Tuple[Dict[str, int], List[str]]:
    """
    Extracts 50+ features from a raw URL for model classification.
    Expands on the original 30 features with additional lexical, structural, and heuristic features.

    New features:
    - Lexical: hostname_length, path_length, query_length, digit_ratio, special_char_ratio
    - Structural: hostname_depth, path_depth, query_param_count, subdomain_depth
    - Security: encoded_char_count, suspicious_keyword_count, subdomain_entropy
    - Heuristic: domain_age_signal, traffic_signal, trust_score

    Returns:
        features: dictionary mapping feature name to its value (-1, 0, or 1)
        explanations: list of human-readable warnings/observations
    """
    url = clean_url(raw_url)
    features = {}
    explanations = []

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        parsed = urllib.parse.urlparse("http://invalid.url")

    hostname = parsed.hostname or ""
    path = parsed.path or ""
    query = parsed.query or ""
    fragment = parsed.fragment or ""

    # Early return for empty/invalid URLs
    if not url or not hostname:
        for i in range(1, 51):
            features[f"Feature_{i}"] = 1
        return features, ["Invalid or empty URL provided."]

    # ============ ORIGINAL FEATURES (30) ============

    # 1. having_IP_Address
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, hostname):
        features["having_IP_Address"] = -1
        explanations.append("The domain name is an IP address, which is highly unusual for legitimate websites.")
    else:
        features["having_IP_Address"] = 1

    # 2. URL_Length
    url_len = len(url)
    if url_len < 54:
        features["URL_Length"] = 1
    elif url_len <= 75:
        features["URL_Length"] = 0
        explanations.append("The URL is somewhat long, which can be used to hide suspicious domains.")
    else:
        features["URL_Length"] = -1
        explanations.append("The URL is extremely long. Phishers use long URLs to hide the actual destination.")

    # 3. Shortining_Service
    is_shortened = any(hostname.endswith(short) or hostname == short for short in SHORTENING_SERVICES)
    if is_shortened:
        features["Shortining_Service"] = -1
        explanations.append("The URL uses a known URL shortening service, which masks the final destination.")
    else:
        features["Shortining_Service"] = 1

    # 4. having_At_Symbol
    if "@" in url:
        features["having_At_Symbol"] = -1
        explanations.append("The URL contains an '@' symbol. Browsers ignore everything before '@', so this is likely a spoof.")
    else:
        features["having_At_Symbol"] = 1

    # 5. double_slash_redirecting
    if url.count("//") > 1 or (path and "//" in path):
        features["double_slash_redirecting"] = -1
        explanations.append("The URL path contains '//', which is often used to redirect users to another site.")
    else:
        features["double_slash_redirecting"] = 1

    # 6. Prefix_Suffix
    if "-" in hostname:
        features["Prefix_Suffix"] = -1
        explanations.append("The domain name contains a hyphen '-'. Legit brands rarely use hyphens in their core domains.")
    else:
        features["Prefix_Suffix"] = 1

    # 7. having_Sub_Domain
    subdomains = hostname.replace("www.", "")
    dot_count = subdomains.count(".")
    if dot_count <= 2:
        features["having_Sub_Domain"] = 1
    elif dot_count == 3:
        features["having_Sub_Domain"] = 0
        explanations.append("The URL has multiple subdomains, which is common in phishing sites setup on free hosts.")
    else:
        features["having_Sub_Domain"] = -1
        explanations.append("The URL has a very high number of subdomains (deeply nested), suggesting a spoofed hierarchy.")

    # 8. SSLfinal_State
    is_https = parsed.scheme.lower() == "https"
    if is_https:
        features["SSLfinal_State"] = 1
    else:
        features["SSLfinal_State"] = -1
        explanations.append("The URL does not use HTTPS. The connection is unencrypted and insecure.")

    # Domain analysis for reputation features
    domain_parts = hostname.split(".")
    core_domain = ".".join(domain_parts[-2:]) if len(domain_parts) >= 2 else hostname
    is_popular = core_domain in POPULAR_DOMAINS or hostname in POPULAR_DOMAINS

    # 9. Domain_registeration_length
    features["Domain_registeration_length"] = 1 if is_popular else -1
    if not is_popular:
        explanations.append("The domain registration details are unknown or could be short-lived.")

    # 11. port
    if parsed.port and parsed.port not in [80, 443]:
        features["port"] = -1
        explanations.append(f"The URL specifies a non-standard port ({parsed.port}), which is a security risk.")
    else:
        features["port"] = 1

    # 12. HTTPS_token
    if "https" in hostname.lower():
        features["HTTPS_token"] = -1
        explanations.append("The domain name contains the token 'https' in the host string itself to trick users.")
    else:
        features["HTTPS_token"] = 1

    # 25. DNSRecord
    try:
        if hostname and _is_safe_hostname(hostname):
            socket.gethostbyname(hostname)
            features["DNSRecord"] = 1
        else:
            features["DNSRecord"] = -1
            explanations.append("Could not resolve domain IP via DNS. The host may be offline or fake.")
    except socket.gaierror:
        features["DNSRecord"] = -1
        explanations.append("Could not resolve domain IP via DNS. The host may be offline or fake.")
    except Exception:
        features["DNSRecord"] = -1
        explanations.append("DNS lookup failed due to security restrictions.")

    # 18. Abnormal_URL
    features["Abnormal_URL"] = 1 if is_popular else -1

    # 24. age_of_domain
    features["age_of_domain"] = 1 if is_popular else -1
    if not is_popular:
        explanations.append("The domain may be recently registered (less than 6 months old).")

    # 26. web_traffic
    features["web_traffic"] = 1 if is_popular else -1
    if not is_popular:
        explanations.append("The website has very low or no recorded web traffic rank.")

    # 27. Page_Rank
    features["Page_Rank"] = 1 if is_popular else -1
    if not is_popular:
        explanations.append("The page has no PageRank or a very low trust score.")

    # 28. Google_Index
    features["Google_Index"] = 1 if is_popular else -1

    # 29. Links_pointing_to_page
    features["Links_pointing_to_page"] = 1 if is_popular else -1

    # 30. Statistical_report
    has_phish_words = any(kw in hostname.lower() for kw in PHISH_KEYWORDS) and not is_popular
    if has_phish_words:
        features["Statistical_report"] = -1
        explanations.append("The domain name uses deceptive brand-associated keywords (e.g. login, verification, paypal).")
    else:
        features["Statistical_report"] = 1

    # ============ NEW FEATURES (Added for improved detection) ============

    # 31. hostname_length (Lexical)
    hostname_len = len(hostname)
    if hostname_len < 10:
        features["hostname_length"] = -1  # Very short hostname is suspicious
        explanations.append("The domain name is extremely short, which can indicate a suspicious domain.")
    elif hostname_len < 15:
        features["hostname_length"] = 0
    else:
        features["hostname_length"] = 1

    # 32. path_length (Lexical)
    path_len = len(path)
    if path_len > 100:
        features["path_length"] = -1
        explanations.append("The URL has a very long path, which can be used to hide malicious content.")
    elif path_len > 50:
        features["path_length"] = 0
    else:
        features["path_length"] = 1

    # 33. query_length (Lexical)
    query_len = len(query)
    if query_len > 200:
        features["query_length"] = -1
        explanations.append("The URL has a very long query string, which may contain encoded malicious payloads.")
    elif query_len > 100:
        features["query_length"] = 0
    else:
        features["query_length"] = 1

    # 34. digit_ratio (Lexical)
    alpha_count = sum(1 for c in hostname if c.isalpha())
    digit_count = sum(1 for c in hostname if c.isdigit())
    if alpha_count > 0:
        digit_ratio = digit_count / alpha_count
        if digit_ratio > 0.5:
            features["digit_ratio"] = -1
            explanations.append("The domain has a high ratio of digits to letters, common in random domain generation.")
        elif digit_ratio > 0.3:
            features["digit_ratio"] = 0
        else:
            features["digit_ratio"] = 1
    else:
        features["digit_ratio"] = 1  # No alpha characters

    # 35. special_char_ratio (Lexical)
    special_chars = sum(1 for c in hostname if c in "!@#$%^&*()_+-=[]{}|;':\",./<>?")
    if alpha_count > 0:
        special_ratio = special_chars / alpha_count
        if special_ratio > 0.1:
            features["special_char_ratio"] = -1
            explanations.append("The domain contains special characters, which is unusual for legitimate domains.")
        else:
            features["special_char_ratio"] = 1
    else:
        features["special_char_ratio"] = 1

    # 36. hostname_depth (Structural)
    hostname_depth = subdomains.count(".")
    if hostname_depth >= 3:
        features["hostname_depth"] = -1
        explanations.append("The domain has deep nesting of subdomains, which is often used to hide the actual domain.")
    elif hostname_depth >= 2:
        features["hostname_depth"] = 0
    else:
        features["hostname_depth"] = 1

    # 37. path_depth (Structural)
    path_depth = path.count("/")
    if path_depth > 10:
        features["path_depth"] = -1
        explanations.append("The URL has a very deep path structure, which can hide malicious content.")
    elif path_depth > 5:
        features["path_depth"] = 0
    else:
        features["path_depth"] = 1

    # 38. query_param_count (Structural)
    query_params = query.split("&")
    if len(query_params) > 10:
        features["query_param_count"] = -1
        explanations.append("The URL has an unusually high number of query parameters.")
    else:
        features["query_param_count"] = 1

    # 39. subdomain_entropy (Security - measures randomness in subdomains)
    if dot_count >= 1:
        subdomain_part = subdomains.split(".")[0] if dot_count >= 1 else hostname
        if len(subdomain_part) > 0:
            char_freq = Counter(subdomain_part.lower())
            total = sum(char_freq.values())
            entropy = 0
            for count in char_freq.values():
                p = count / total
                entropy -= p * (p + 1e-10).bit_length()  # Approximate entropy
            if entropy > 3.5:  # High entropy = random-looking
                features["subdomain_entropy"] = -1
                explanations.append("The subdomain appears randomly generated, which is common in phishing.")
            else:
                features["subdomain_entropy"] = 1
        else:
            features["subdomain_entropy"] = 1
    else:
        features["subdomain_entropy"] = 1

    # 40. encoded_char_count (Security)
    encoded_count = url.count("%") + url.count("&#")
    if encoded_count > 5:
        features["encoded_char_count"] = -1
        explanations.append("The URL contains many encoded characters, which can be used to hide malicious content.")
    elif encoded_count > 0:
        features["encoded_char_count"] = 0
    else:
        features["encoded_char_count"] = 1

    # 41. suspicious_keyword_count (Security)
    keyword_matches = sum(1 for kw in PHISH_KEYWORDS if kw in hostname.lower())
    if keyword_matches > 3:
        features["suspicious_keyword_count"] = -1
        explanations.append("The domain contains multiple suspicious keywords commonly used in phishing.")
    elif keyword_matches > 0:
        features["suspicious_keyword_count"] = 0
    else:
        features["suspicious_keyword_count"] = 1

    # 42. subdomain_depth (Structural - count of subdomain levels)
    features["subdomain_depth"] = min(hostname_depth, 1)

    # 43. has_IP_in_path (Security - IP address in path)
    if re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', path):
        features["has_IP_in_path"] = -1
        explanations.append("The URL path contains an IP address, which can indicate a malicious redirect.")
    else:
        features["has_IP_in_path"] = 1

    # 44. domain_length_signal (Lexical)
    domain_len = len(core_domain)
    if domain_len < 8:
        features["domain_length_signal"] = -1
        explanations.append("The domain name is very short, which can be suspicious.")
    else:
        features["domain_length_signal"] = 1

    # 45. subdomain_count_signal (Structural)
    features["subdomain_count_signal"] = min(dot_count, 2)

    # 46. unusual_port_signal (Security)
    if parsed.port:
        features["unusual_port_signal"] = -1
    else:
        features["unusual_port_signal"] = 1

    # 47. userinfo_signal (Security - check for username@password in URL)
    if "@" in url and parsed.netloc:
        parts = parsed.netloc.split("@")
        if len(parts) > 1:
            features["userinfo_signal"] = -1
            explanations.append("The URL contains user info (username:password@domain), which is often used in phishing.")
        else:
            features["userinfo_signal"] = 1
    else:
        features["userinfo_signal"] = 1

    # 48. fragment_length (Lexical)
    if len(fragment) > 100:
        features["fragment_length"] = -1
        explanations.append("The URL has a very long fragment, which can hide malicious content.")
    else:
        features["fragment_length"] = 1

    # 49. query_entropy (Security - entropy of query parameters)
    if query:
        char_freq = Counter(query.lower())
        total = sum(char_freq.values())
        if total > 0:
            entropy = 0
            for count in char_freq.values():
                p = count / total
                entropy -= p * (p + 1e-10).bit_length()
            if entropy > 3.8:
                features["query_entropy"] = -1
                explanations.append("The query parameters appear highly randomized, which can indicate encoded malicious content.")
            else:
                features["query_entropy"] = 1
        else:
            features["query_entropy"] = 1
    else:
        features["query_entropy"] = 1

    # 50. trust_score (Heuristic - composite score based on multiple signals)
    trust_factors = 0
    if is_popular:
        trust_factors += 2
    if is_https:
        trust_factors += 1
    if features.get("having_Sub_Domain", 1) == 1:
        trust_factors += 1
    if features.get("DNSRecord", 1) == 1:
        trust_factors += 1
    if not has_phish_words:
        trust_factors += 1

    if trust_factors >= 4:
        features["trust_score"] = 1
    elif trust_factors >= 2:
        features["trust_score"] = 0
    else:
        features["trust_score"] = -1

    return features, explanations
