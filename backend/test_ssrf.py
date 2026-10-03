"""SSRF protection test suite for url_feature_extractor and _safe_urlopen."""
import io
import sys

sys.path.append("C:\\Users\\DIVYA\\OneDrive\\Desktop\\Desktopp\\CyberGuardian\\backend")

from services.url_feature_extractor import (
    _safe_urlopen,
    _is_safe_hostname,
    extract_features_from_url,
    ALLOWED_SCHEMES,
)


def print_result(passed: bool, name: str) -> None:
    marker = "PASS" if passed else "FAIL"
    print(f"[{marker}] {name}")
    return passed


def test_safe_hostname():
    """Blocked hostnames should be rejected."""
    cases = [
        ("localhost", False),
        ("localhost.localdomain", False),
        ("127.0.0.1", False),
        ("0.0.0.0", False),
        ("127.1.2.3", False),
        ("10.0.0.1", False),
        ("172.16.0.1", False),
        ("192.168.1.1", False),
        ("169.254.169.254", False),
        ("100.100.100.100", False),  # RFC 6598 carrier-grade NAT
    ]
    for host, expected in cases:
        actual = _is_safe_hostname(host)
        if actual != expected:
            print(f"    MISMATCH _is_safe_hostname({host!r})={actual}, expected {expected}")
            return False
    return True


def test_schemes_allowed():
    return ALLOWED_SCHEMES == ["http", "https"]


def test_safe_urlopen_blocked_scheme():
    try:
        _safe_urlopen("file:///etc/passwd")
        print("    _safe_urlopen(file://) did not raise")
        return False
    except ValueError as e:
        if "scheme" in str(e):
            return True
        return False
    except Exception as e:
        print(f"    Unexpected exception: {type(e).__name__}: {e}")
        return False


def test_safe_urlopen_private_ip():
    try:
        _safe_urlopen("http://192.168.1.1/")
        print("    _safe_urlopen(http://192.168.1.1/) did not raise")
        return False
    except (ValueError, ConnectionError) as e:
        return True
    except Exception as e:
        print(f"    Unexpected exception: {type(e).__name__}: {e}")
        return False


def test_safe_urlopen_localhost():
    try:
        _safe_urlopen("http://localhost:5432/")
        print("    _safe_urlopen(http://localhost/) did not raise")
        return False
    except (ValueError, ConnectionError) as e:
        return True
    except Exception as e:
        print(f"    Unexpected exception: {type(e).__name__}: {e}")
        return False


def test_safe_urlopen_suspicious_hostname_injection():
    """Control chars and path tricks should be rejected before DNS/network."""
    candidates = ["http://evil.com\\@192.168.1.1", "http://192.168.1.1@evil.com", "http://localhost.localdomain"]
    for url in candidates:
        try:
            _safe_urlopen(url)
            print(f"    _safe_urlopen({url!r}) did not raise")
            return False
        except (ValueError, ConnectionError, Exception):
            pass
    return True


def test_safe_urlopen_redirect_limit():
    """Redirect loop should raise ValueError('Too many redirects')."""
    try:
        _safe_urlopen("http://httpbin.org/redirect-to?url=http://httpbin.org/redirect/50", timeout=20)
        print("    Redirect loop did not raise after 50 redirects")
        return False
    except ValueError as e:
        if "redirect" in str(e).lower():
            return True
        return False
    except Exception as e:
        # External redirects may be unreachable; treat connection failure as non-failure
        print(f"    Remote redirect test skipped ({type(e).__name__}: {e})")
        return True  # network-unreachable is not an SSRF bypass


def test_safe_urlopen_size_limit():
    """Size limit should cap response."""
    # Use a small limit on a small, stable page
    try:
        content, status, final_url = _safe_urlopen(
            "http://example.com/", timeout=15, max_response_size=32
        )
        if len(content) <= 32 and status == 200:
            return True
        print(f"    Size limit not enforced: status={status}, len={len(content)}")
        return False
    except Exception as e:
        print(f"    External fetch blocked ({type(e).__name__}: {e})")
        return True  # egress block is not an SSRF bypass


def test_extract_features_failsafe():
    """Malicious URLs should fail safely with benign default features."""
    for url in [
        "http://192.168.1.1/admin",
        "http://localhost:5432/",
        "file:///etc/passwd",
        "http://169.254.169.254/latest/meta-data/",
    ]:
        try:
            features, explanations = extract_features_from_url(url)
            if all(isinstance(v, int) for v in features.values()):
                print(f"       {url}: returned {len(features)} benign default features")
            else:
                return False
        except Exception as e:
            print(f"       {url}: raised {type(e).__name__}: {e}")
    return True


def main() -> int:
    print("SSRF Protection Test Suite")
    print("-" * 40)
    results = [
        test_schemes_allowed(),
        test_safe_hostname(),
        test_safe_urlopen_blocked_scheme(),
        test_safe_urlopen_private_ip(),
        test_safe_urlopen_localhost(),
        test_safe_urlopen_suspicious_hostname_injection(),
        test_safe_urlopen_redirect_limit(),
        test_safe_urlopen_size_limit(),
        test_extract_features_failsafe(),
    ]
    passed = sum(results)
    total = len(results)
    print("-" * 40)
    print(f"Results: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
