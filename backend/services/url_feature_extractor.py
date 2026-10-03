import ipaddress
import re
import socket
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, List, Tuple
import time

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

# SSRF protection: ALLOWED schemes
ALLOWED_SCHEMES = ["http", "https"]

def clean_url(url: str) -> str:
    """Prepend protocol if missing."""
    url = url.strip()
    if not url:
        return ""
    if not (url.startswith("http://") or url.startswith("https://")):
        # Default to http for parsing structure if not specified
        url = "http://" + url
    return url


def _is_safe_hostname(hostname: str) -> bool:
    """Check if hostname is safe for SSRF protection."""
    if not hostname:
        return False

    hostname_lower = hostname.lower().strip()

    # Block blocked hosts from config and common local-only domains
    blocked_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
    if hostname_lower in blocked_hosts or hostname_lower.endswith('.local'):
        return False
    # Common local-only hostnames that should never be reachable
    if hostname_lower in {'localhost.localdomain', 'ip6-localhost', 'ip6-loopback'}:
        return False

    # Block private IP ranges (RFC 1918, loopback, link-local, and CGNAT)
    try:
        # Try to parse as IP address
        ip = ipaddress.ip_address(hostname_lower)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
        # Carrier-grade NAT (RFC 6598) — not publicly routable, block for SSRF safety
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return False
    except ValueError:
        # Not an IP address — proceed to hostname checks
        pass

    # Block hostnames that resolve to private IPs (DNS rebinding protection)
    try:
        # Only check if looks like an IP or numeric hostname
        if re.match(r'^[\d\.]+$', hostname_lower):
            ip = ipaddress.ip_address(hostname_lower)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
    except (ValueError, ipaddress.AddressValueError):
        pass

    # Block hostnames containing control characters or suspicious patterns
    if any(c in hostname_lower for c in ['\\', '/', ':', '?', '#', '[', ']', '@', '!']):
        return False

    # Block excessively long hostnames (potential buffer overflow)
    if len(hostname_lower) > 255:
        return False

    return True


class _RedirectCountingHandler(urllib.request.HTTPRedirectHandler):
    """
    Custom redirect handler that enforces a maximum hop count and validates
    every redirect target against the SSRF allow-list before following it.

    urllib follows redirects automatically, so a plain urlopen() call never
    surfaces a 3xx response — the manual redirect loop in the original code
    was dead code and max_redirects was never enforced. This handler restores
    that protection by intercepting each redirect decision.
    """

    def __init__(self, max_redirects: int = 5) -> None:
        super().__init__()
        self.max_redirects = max_redirects
        self.redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if self.redirect_count >= self.max_redirects:
            raise ValueError("Too many redirects")
        self.redirect_count += 1

        # Validate the redirect target before following it — a redirect can
        # silently point the request at an internal/private host.
        parsed = urllib.parse.urlparse(newurl)
        scheme = parsed.scheme.lower()
        if scheme not in ALLOWED_SCHEMES:
            raise ValueError(
                f"Redirect to disallowed scheme '{scheme}' blocked. "
                f"Only {ALLOWED_SCHEMES} permitted."
            )
        if not _is_safe_hostname(parsed.hostname or ""):
            raise ValueError(
                f"Redirect to unsafe host '{parsed.hostname}' blocked for security reasons."
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _resolve_public_ips(hostname: str) -> List[str]:
    """
    Resolve a hostname and return all IP addresses. Raises ValueError if any
    resolved address is private/loopback/link-local (DNS-rebinding protection).
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname '{hostname}' via DNS.")
    ips = []
    for family, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(
                f"Hostname '{hostname}' resolves to private IP {ip_str} — blocked (DNS rebinding)."
            )
        ips.append(ip_str)
    if not ips:
        raise ValueError(f"Hostname '{hostname}' resolved to no usable addresses.")
    return ips


def _safe_urlopen(
    url: str,
    timeout: float = 10.0,
    max_redirects: int = 5,
    max_response_size: int = 10 * 1024 * 1024,  # 10 MB
) -> Tuple[bytes, int, str]:
    """
    Safely open a URL with SSRF protection, timeout, redirect limits, and size limits.
    Returns (content, final_status_code, final_url).
    """
    # Parse and validate URL
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname or ""

    # Scheme allow-list
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme '{scheme}' is not allowed. Only {ALLOWED_SCHEMES} permitted.")

    # Hostname safety check
    if not _is_safe_hostname(hostname):
        raise ValueError(f"Hostname '{hostname}' is not allowed for security reasons.")

    # DNS-rebinding protection: resolve the hostname and reject any private IP.
    # Done before connecting so a hostname that resolves to 10.0.0.1 is blocked.
    _resolve_public_ips(hostname)

    # Build an opener that enforces redirect limits and validates each hop.
    handler = _RedirectCountingHandler(max_redirects=max_redirects)
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

            # Not a redirect — read response with size limit
            content = b""
            remaining = max_response_size
            chunk_size = 8192

            while remaining > 0:
                chunk = response.read(min(chunk_size, remaining))
                if not chunk:
                    break
                content += chunk
                remaining -= len(chunk)

            # If we stopped due to size limit, that's fine — we have partial content
            return content, status, final_url

    except urllib.error.HTTPError as e:
        # HTTP error (4xx, 5xx) — return what we have
        return e.read(), e.code, url
    except urllib.error.URLError as e:
        # URL error (DNS, connection, timeout)
        raise ConnectionError(f"Failed to fetch URL: {e.reason}")
    except socket.timeout:
        raise TimeoutError("Request timed out")
    except ValueError:
        # Redirect limit / SSRF block raised by our handler — propagate
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error fetching URL: {e}")


def extract_features_from_url(raw_url: str) -> Tuple[Dict[str, int], List[str]]:
    """
    Extracts 30 features from a raw URL for model classification.
    Returns:
        features: dictionary mapping feature name to its value (-1, 0, or 1)
        explanations: list of human-readable warnings/observations
    Includes SSRF protection and safe fetching.
    """
    url = clean_url(raw_url)
    features = {}
    explanations = []

    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname or ""
    path = parsed.path or ""

    # Early return for empty/invalid URLs
    if not url or not hostname:
        # Return default safe features
        for i in range(1, 31):
            features[f"Feature_{i}"] = 1  # Default safe/benign
        return features, ["Invalid or empty URL provided."]

    # 1. having_IP_Address: Phishing contains IP address
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$|^(0x[0-9a-fA-F]{2}\.){3}0x[0-9a-fA-F]{2}$|^[0-9a-fA-F:]+$'
    if re.match(ip_pattern, hostname):
        features["having_IP_Address"] = -1
        explanations.append("The domain name is an IP address, which is highly unusual for legitimate websites.")
    else:
        features["having_IP_Address"] = 1

    # 2. URL_Length:
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
    # SSRF-protected DNS lookup
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

    # 30. Statistical_report: PhishTank/StopBadware list -> -1, else -1
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

    # Try to fetch HTML content to refine page content features — WITH SSRF PROTECTION
    html = ""
    if hostname and features["DNSRecord"] == 1:
        try:
            # Use safe fetch with SSRF protection, timeout, and size limits from config
            url_fetch_timeout = getattr(__import__('config').Settings, 'MAX_URL_FETCH_TIMEOUT', 10.0)
            max_response_size_mb = getattr(__import__('config').Settings, 'MAX_RESPONSE_SIZE', 10)
            max_response_size_bytes = max_response_size_mb * 1024 * 1024

            html_content, final_status, final_url = _safe_urlopen(
                url,
                timeout=url_fetch_timeout,
                max_redirects=getattr(__import__('config').Settings, 'MAX_URL_REDIRECTS', 5),
                max_response_size=max_response_size_bytes,
            )

            if html_content:
                html = html_content.decode('utf-8', errors='ignore')

                # Check for redirect via final URL change
                if final_url != url:
                    features["Redirect"] = 1

        except Exception:
            # Fail silently and fall back to heuristics/default values
            pass

    if html:
        # Refine features based on HTML page content

        # 10. Favicon: loaded from different domain?
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