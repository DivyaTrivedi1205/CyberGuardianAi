import re
import socket
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Tuple

# Popular/legitimate domains whitelist for heuristics
POPULAR_DOMAINS = {
    "google.com", "youtube.com", "facebook.com", "twitter.com", "instagram.com",
    "wikipedia.org", "yahoo.com", "amazon.com", "netflix.com", "linkedin.com",
    "reddit.com", "ebay.com", "bing.com", "msn.com", "microsoft.com", "apple.com",
    "github.com", "stackoverflow.com", "wordpress.com", "blogspot.com", "tumblr.com",
    "pinterest.com", "live.com", "outlook.com", "zoom.us", "imdb.com", "office.com",
    "disney.com", "paypal.com", "stripe.com", "quora.com", "medium.com", "cnn.com",
    "bbc.com", "nytimes.com", "spotify.com", "salesforce.com", "dropbox.com"
}

# Common shortening services
SHORTENING_SERVICES = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "is.gd", "buff.ly", "adf.ly",
    "bit.do", "ow.ly", "rebrand.ly", "t2mio.com", "shorte.st", "lnkd.in", "db.tt",
    "qr.ae", "adfoc.us", "bc.vc", "twitthis.com", "u.to", "j.mp", "su.pr"
}

def clean_url(url: str) -> str:
    """Prepend protocol if missing."""
    url = url.strip()
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        # Default to http for parsing structure if not specified
        url = "http://" + url
    return url

def extract_features_from_url(raw_url: str) -> Tuple[Dict[str, int], List[str]]:
    """
    Extracts 30 features from a raw URL for model classification.
    Returns:
        features: dictionary mapping feature name to its value (-1, 0, or 1)
        explanations: list of human-readable warnings/observations
    """
    url = clean_url(raw_url)
    features = {}
    explanations = []
    
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""
    path = parsed.path or ""
    
    # 1. having_IP_Address: Phishing contains IP address
    # Checks IPv4 (e.g. 192.168.1.1 or hex 0x58.etc) and IPv6
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$|^(0x[0-9a-fA-F]{2}\.){3}0x[0-9a-fA-F]{2}$|^[0-9a-fA-F:]+$'
    if re.match(ip_pattern, hostname):
        features["having_IP_Address"] = -1
        explanations.append("The domain name is an IP address, which is highly unusual for legitimate websites.")
    else:
        features["having_IP_Address"] = 1

    # 2. URL_Length: 
    # length < 54 -> 1, 54 <= length <= 75 -> 0, length > 75 -> -1
    url_len = len(url)
    if url_len < 54:
        features["URL_Length"] = 1
    elif url_len <= 75:
        features["URL_Length"] = 0
        explanations.append("The URL is somewhat long, which can be used to hide suspicious domains.")
    else:
        features["URL_Length"] = -1
        explanations.append("The URL is extremely long. Phishers use long URLs to hide the actual destination.")

    # 3. Shortining_Service: If shortened -> -1, else 1
    is_shortened = any(hostname.endswith(short) or hostname == short for short in SHORTENING_SERVICES)
    if is_shortened:
        features["Shortining_Service"] = -1
        explanations.append("The URL uses a known URL shortening service, which masks the final destination.")
    else:
        features["Shortining_Service"] = 1

    # 4. having_At_Symbol: @ in URL -> -1, else 1
    if "@" in url:
        features["having_At_Symbol"] = -1
        explanations.append("The URL contains an '@' symbol. Browsers ignore everything before '@', so this is likely a spoof.")
    else:
        features["having_At_Symbol"] = 1

    # 5. double_slash_redirecting: double slash in path index > 7 -> -1, else 1
    if url.count("//") > 1 or (path and "//" in path):
        features["double_slash_redirecting"] = -1
        explanations.append("The URL path contains '//', which is often used to redirect users to another site.")
    else:
        features["double_slash_redirecting"] = 1

    # 6. Prefix_Suffix: dash in domain -> -1, else 1
    if "-" in hostname:
        features["Prefix_Suffix"] = -1
        explanations.append("The domain name contains a hyphen '-'. Legit brands rarely use hyphens in their core domains.")
    else:
        features["Prefix_Suffix"] = 1

    # 7. having_Sub_Domain: count dots in domain excluding www and TLD
    # e.g., google.com has 1 dot. login.google.com has 2 dots. 
    # dots < 2 -> 1, dots == 2 -> 0, dots > 2 -> -1
    subdomains = hostname.replace("www.", "")
    dot_count = subdomains.count(".")
    if dot_count <= 2:
        # e.g., domain.co.uk (2 dots) or domain.com (1 dot)
        features["having_Sub_Domain"] = 1
    elif dot_count == 3:
        features["having_Sub_Domain"] = 0
        explanations.append("The URL has multiple subdomains, which is common in phishing sites setup on free hosts.")
    else:
        features["having_Sub_Domain"] = -1
        explanations.append("The URL has a very high number of subdomains (deeply nested), suggesting a spoofed hierarchy.")

    # 8. SSLfinal_State: https -> 1, http -> -1
    is_https = parsed.scheme.lower() == "https"
    if is_https:
        features["SSLfinal_State"] = 1
    else:
        features["SSLfinal_State"] = -1
        explanations.append("The URL does not use HTTPS. The connection is unencrypted and insecure.")

    # Check if domain belongs to a popular reputable domain
    domain_parts = hostname.split(".")
    core_domain = ".".join(domain_parts[-2:]) if len(domain_parts) >= 2 else hostname
    is_popular = core_domain in POPULAR_DOMAINS or hostname in POPULAR_DOMAINS

    # 9. Domain_registeration_length: domain reg length >= 1 yr -> 1, else -1
    features["Domain_registeration_length"] = 1 if is_popular else -1
    if not is_popular:
        explanations.append("The domain registration details are unknown or could be short-lived.")

    # 11. port: non-standard port -> -1, else 1
    if parsed.port and parsed.port not in [80, 443]:
        features["port"] = -1
        explanations.append(f"The URL specifies a non-standard port ({parsed.port}), which is a security risk.")
    else:
        features["port"] = 1

    # 12. HTTPS_token: "https" in domain part -> -1, else 1
    if "https" in hostname.lower():
        features["HTTPS_token"] = -1
        explanations.append("The domain name contains the token 'https' in the host string itself to trick users.")
    else:
        features["HTTPS_token"] = 1

    # 25. DNSRecord: DNS resolution -> 1, fail -> -1
    try:
        if hostname:
            socket.gethostbyname(hostname)
            features["DNSRecord"] = 1
        else:
            features["DNSRecord"] = -1
    except socket.gaierror:
        features["DNSRecord"] = -1
        explanations.append("Could not resolve domain IP via DNS. The host may be offline or fake.")

    # 18. Abnormal_URL: If hostname matches WHOIS. Heuristic: if popular domain, 1, else -1
    features["Abnormal_URL"] = 1 if is_popular else -1

    # 24. age_of_domain: age >= 6 months -> 1, else -1
    features["age_of_domain"] = 1 if is_popular else -1
    if not is_popular:
        explanations.append("The domain may be recently registered (less than 6 months old).")

    # 26. web_traffic: popular -> 1, unknown -> -1 (UCI: -1, 0, 1)
    features["web_traffic"] = 1 if is_popular else -1
    if not is_popular:
        explanations.append("The website has very low or no recorded web traffic rank.")

    # 27. Page_Rank: popular -> 1, else -1
    features["Page_Rank"] = 1 if is_popular else -1
    if not is_popular:
        explanations.append("The page has no PageRank or a very low trust score.")

    # 28. Google_Index: popular -> 1, else -1
    features["Google_Index"] = 1 if is_popular else -1

    # 29. Links_pointing_to_page: popular -> 1, else -1 (UCI: -1, 0, 1)
    features["Links_pointing_to_page"] = 1 if is_popular else -1

    # 30. Statistical_report: PhishTank/StopBadware list -> -1, else 1
    # Check if domain has suspicious phishing words
    phish_keywords = ["paypal", "security", "secure", "signin", "login", "verification", "update", "bank", "account", "support", "billing"]
    has_phish_words = any(kw in hostname.lower() for kw in phish_keywords) and not is_popular
    if has_phish_words:
        features["Statistical_report"] = -1
        explanations.append("The domain name uses deceptive brand-associated keywords (e.g. login, verification, paypal).")
    else:
        features["Statistical_report"] = 1

    # Default values for HTML page content features (updated if HTML is fetched successfully)
    features["Favicon"] = 1
    features["Request_URL"] = 1
    features["URL_of_Anchor"] = 1
    features["Links_in_tags"] = 1
    features["SFH"] = 1
    features["Submitting_to_email"] = 1
    features["Redirect"] = 0
    features["on_mouseover"] = 1
    features["RightClick"] = 1
    features["popUpWidnow"] = 1
    features["Iframe"] = 1

    # Try to fetch HTML content to refine page content features
    html = ""
    if hostname and features["DNSRecord"] == 1:
        try:
            # Short timeout to avoid hanging the API request
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberGuardianAI/1.0'}
            )
            with urllib.request.urlopen(req, timeout=1.5) as response:
                html = response.read().decode('utf-8', errors='ignore')
                # Count redirect if possible
                if response.geturl() != url:
                    features["Redirect"] = 1
        except Exception:
            # Fail silently and fall back to heuristics/default values
            pass

    if html:
        # Refine features based on HTML page content
        
        # 10. Favicon: loaded from different domain?
        # Extract favicon link
        favicons = re.findall(r'<link[^>]*rel=["\'](?:shortcut )?icon["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if favicons:
            favicon_url = favicons[0]
            fav_parsed = urllib.parse.urlparse(urllib.parse.urljoin(url, favicon_url))
            if fav_parsed.hostname and fav_parsed.hostname != hostname:
                features["Favicon"] = -1
                explanations.append("The website loads its favicon from an external, unrelated domain.")
        
        # Helper to check domain matching
        def is_external(link_url):
            try:
                l_parsed = urllib.parse.urlparse(urllib.parse.urljoin(url, link_url))
                if l_parsed.hostname and l_parsed.hostname != hostname:
                    return True
            except Exception:
                pass
            return False

        # 13. Request_URL: % of external resources (img, src, embed)
        # Find all src resources
        srcs = re.findall(r'<(?:img|audio|embed|iframe)[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if srcs:
            ext_count = sum(1 for src in srcs if is_external(src))
            pct = ext_count / len(srcs)
            if pct >= 0.61:
                features["Request_URL"] = -1
                explanations.append("Over 60% of external resources (images, video) are loaded from different domains.")
            elif pct >= 0.22:
                features["Request_URL"] = 0
            else:
                features["Request_URL"] = 1

        # 14. URL_of_Anchor: % of anchor links pointing to different domain or #/javascript
        anchors = re.findall(r'<a[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if anchors:
            suspicious_anchors = 0
            for href in anchors:
                href_clean = href.strip()
                if href_clean.startswith("#") or "javascript:" in href_clean.lower() or is_external(href_clean):
                    suspicious_anchors += 1
            pct = suspicious_anchors / len(anchors)
            if pct >= 0.67:
                features["URL_of_Anchor"] = -1
                explanations.append("Most links on this page point to external domains, empty tags, or scripts.")
            elif pct >= 0.31:
                features["URL_of_Anchor"] = 0
            else:
                features["URL_of_Anchor"] = 1

        # 15. Links_in_tags: % of links in meta, script, link tags
        tags_links = re.findall(r'<(?:link|script|meta)[^>]*(?:href|src)=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if tags_links:
            ext_count = sum(1 for link in tags_links if is_external(link))
            pct = ext_count / len(tags_links)
            if pct >= 0.81:
                features["Links_in_tags"] = -1
                explanations.append("Almost all metadata, script, and link elements point to external domains.")
            elif pct >= 0.17:
                features["Links_in_tags"] = 0
            else:
                features["Links_in_tags"] = 1

        # 16. SFH (Server Form Handler): form action empty, about:blank, or external
        forms = re.findall(r'<form[^>]*action=["\']([^"\']*)["\']', html, re.IGNORECASE)
        if forms:
            sfh_vals = []
            for action in forms:
                action_clean = action.strip()
                if not action_clean or action_clean.lower() == "about:blank":
                    sfh_vals.append(-1)
                elif is_external(action_clean):
                    sfh_vals.append(0)
                else:
                    sfh_vals.append(1)
            
            min_val = min(sfh_vals)
            features["SFH"] = min_val
            if min_val == -1:
                explanations.append("The form handler (SFH) action is empty or points to about:blank, risking credential leaks.")
            elif min_val == 0:
                explanations.append("The form submits user details to an external domain unrelated to this website.")
        
        # 17. Submitting_to_email: mailto or mail() action
        if "mailto:" in html or "mail(" in html:
            features["Submitting_to_email"] = -1
            explanations.append("The page code contains a 'mailto:' link, indicating it submits input to an email account.")
        else:
            features["Submitting_to_email"] = 1

        # 20. on_mouseover: status bar modified?
        if "window.status" in html or "status=" in html:
            features["on_mouseover"] = -1
            explanations.append("The website code overrides the browser status bar display to hide true links.")
        else:
            features["on_mouseover"] = 1

        # 21. RightClick: right click disabled?
        if "event.button==2" in html or "event.button == 2" in html or "contextmenu" in html or "preventDefault()" in html:
            # Heuristic contextmenu check
            if re.search(r'oncontextmenu\s*=\s*["\']return\s+false', html, re.IGNORECASE):
                features["RightClick"] = -1
                explanations.append("Right-clicking is disabled by the page script, preventing inspection of source code.")
            else:
                features["RightClick"] = 1
        else:
            features["RightClick"] = 1

        # 22. popUpWidnow: popups asking for inputs
        if "prompt(" in html:
            features["popUpWidnow"] = -1
            explanations.append("The page uses popup prompts to request inputs from the user.")
        else:
            features["popUpWidnow"] = 1

        # 23. Iframe: invisible iframe used?
        if "<iframe" in html.lower():
            features["Iframe"] = -1
            explanations.append("The website embeds hidden or invisible inline frames (iframes).")
        else:
            features["Iframe"] = 1

    return features, explanations
