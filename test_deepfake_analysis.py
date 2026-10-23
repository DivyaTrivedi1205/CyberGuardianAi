"""
Focused deepfake detection tests to trace feature combination and identify false positives.

Tests:
1. Low CNN risk + high forensic anomaly scores (tests override behavior)
2. Genuine image without EXIF metadata
3. Genuine image with camera EXIF
4. Fake/manipulated image

Run: cd backend && python -c "from services.deepfake_analyzer import analyze_deepfake; test_..."
"""
import os
import sys
import io
import json
import hashlib
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# Add backend to path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

def create_solid_image(color=(128, 128, 128), size=(256, 256), format='PNG'):
    """Create a simple solid color image."""
    img = Image.new('RGB', size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue(), img

def create_gradient_image(size=(256, 256)):
    """Create a gradient image (likely to trigger forensic analysis)."""
    arr = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    for i in range(size[0]):
        for j in range(size[1]):
            arr[i, j] = [
                int(128 + 64 * np.sin(i / 20)),
                int(128 + 64 * np.cos(j / 20)),
                int(128 + 64 * np.sin((i + j) / 20))
            ]
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue(), img

def create_high_noise_image(size=(256, 256)):
    """Create image with high noise variance (triggers forensic anomaly)."""
    arr = np.random.randint(0, 255, (size[0], size[1], 3), dtype=np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue(), img

def create_low_noise_image(size=(256, 256)):
    """Create image with very low noise (smooth, might trigger smooth skin score)."""
    arr = np.ones((size[0], size[1], 3), dtype=np.uint8) * 128
    # Add very subtle noise
    arr = arr + np.random.randint(-5, 6, arr.shape).astype(np.int16)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue(), img

def add_exif_to_image(img, make="Canon", model="EOS R5"):
    """Add camera EXIF metadata to an image."""
    exif = Image.Exif()
    exif[271] = make  # Make
    exif[272] = model  # Model
    exif[305] = "1.0.0"  # Software
    buf = io.BytesIO()
    img.save(buf, format='JPEG', exif=exif)
    return buf.getvalue()

def trace_analysis(file_bytes, file_name="test.jpg", content_type="image/jpeg"):
    """Run analysis and return detailed trace of feature combination."""
    from services.deepfake_analyzer import analyze_deepfake

    result = analyze_deepfake(file_bytes, file_name, content_type)

    # Parse the detailed result
    trace = {
        'file_name': result.get('file_name'),
        'prediction': result.get('prediction'),
        'risk_score': result.get('risk_score'),
        'features': result.get('features', {}),
        'feedback': result.get('feedback'),
        'file_type': result.get('file_type'),
    }

    return trace

def test_case(name, file_bytes, file_name="test.jpg", expected_behavior=None):
    """Run a test case with detailed output."""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")

    file_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
    print(f"File hash: {file_hash}")
    print(f"File size: {len(file_bytes)} bytes")

    try:
        trace = trace_analysis(file_bytes, file_name)

        print(f"\n--- RESULT ---")
        print(f"Prediction: {trace['prediction']}")
        print(f"Risk Score: {trace['risk_score']}")
        print(f"\n--- FEATURES ---")
        for k, v in sorted(trace['features'].items()):
            print(f"  {k}: {v}")
        print(f"\n--- FEEDBACK ---")
        for fb in trace['feedback']:
            print(f"  - {fb}")

        if expected_behavior:
            print(f"\n--- EXPECTED ---")
            print(f"  {expected_behavior}")
            # Check if result matches expectation
            pred = trace['prediction']
            risk = trace['risk_score']
            if 'Authentic' in expected_behavior and pred == 'Authentic':
                print(f"  ✓ PASS: Result matches expected")
            elif 'Suspicious' in expected_behavior and pred == 'Suspicious':
                print(f"  ✓ PASS: Result matches expected")
            elif 'AI Generated' in expected_behavior and pred == 'AI Generated':
                print(f"  ✓ PASS: Result matches expected")
            else:
                print(f"  ⚠ Result differs from expectation")

        return trace

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_all_tests():
    print("\n" + "="*70)
    print("DEEPFAKE DETECTION ANALYSIS - FOCUSED TEST SUITE")
    print("="*70)

    results = {}

    # TEST 1: Low CNN risk + high forensic anomaly
    print("\n\n" + "="*70)
    print("TEST SET 1: LOW CNN RISK + HIGH FORENSIC ANOMALY")
    print("This tests the override behavior at lines 411-416")
    print("="*70)

    # Gradient image tends to trigger FFT and ELA anomalies
    grad_bytes, grad_img = create_gradient_image()
    trace1 = test_case(
        "Gradient Image (triggers forensic anomalies)",
        grad_bytes,
        "gradient.jpg",
        "Expected: May trigger forensic override if edge/bg scores > 80 and CNN < 50"
    )
    results['gradient'] = trace1

    # TEST 2: Genuine image WITHOUT EXIF
    print("\n\n" + "="*70)
    print("TEST SET 2: GENUINE IMAGE WITHOUT EXIF")
    print("This tests the metadata_score=45 penalty (lines 358-364)")
    print("="*70)

    solid_bytes, solid_img = create_solid_image(color=(100, 150, 200))
    trace2 = test_case(
        "Solid Color Image (NO EXIF)",
        solid_bytes,
        "photo_no_exif.jpg",
        "Expected: metadata_score=45 may push risk higher"
    )
    results['solid_no_exif'] = trace2

    # TEST 3: Genuine image WITH EXIF
    print("\n\n" + "="*70)
    print("TEST SET 3: GENUINE IMAGE WITH EXIF (camera metadata)")
    print("This tests the has_genuine_camera reduction (lines 363-364, 418-419)")
    print("="*70)

    solid_bytes_with_exif = add_exif_to_image(solid_img)
    trace3 = test_case(
        "Solid Color Image (WITH EXIF - Canon EOS R5)",
        solid_bytes_with_exif,
        "photo_with_exif.jpg",
        "Expected: metadata_score=5, may get camera reduction"
    )
    results['solid_with_exif'] = trace3

    # TEST 4: High noise image (likely fake pattern)
    print("\n\n" + "="*70)
    print("TEST SET 4: HIGH NOISE IMAGE")
    print("Triggers noise inconsistency features")
    print("="*70)

    noise_bytes, noise_img = create_high_noise_image()
    trace4 = test_case(
        "High Noise Image (random pixels)",
        noise_bytes,
        "noise_test.jpg",
        "Expected: May trigger forensic features high"
    )
    results['high_noise'] = trace4

    # TEST 5: Low noise image (smooth)
    print("\n\n" + "="*70)
    print("TEST SET 5: LOW NOISE IMAGE (smooth)")
    print("Triggers skin_smooth_score (inverted logic)")
    print("="*70)

    smooth_bytes, smooth_img = create_low_noise_image()
    trace5 = test_case(
        "Low Noise Image (smooth)",
        smooth_bytes,
        "smooth_test.jpg",
        "Expected: May trigger smooth texture detection"
    )
    results['low_noise'] = trace5

    # SUMMARY
    print("\n\n" + "="*70)
    print("SUMMARY - FEATURE COMBINATION ANALYSIS")
    print("="*70)

    print("\n--- Risk Score Breakdown ---")
    for name, trace in results.items():
        if trace:
            risk = trace['risk_score']
            pred = trace['prediction']
            features = trace.get('features', {})
            meta = features.get('Metadata Anomalies', 'N/A')
            edge = features.get('Edge Blending', 'N/A')
            bg = features.get('Background Warping', 'N/A')
            print(f"{name:20s}: Risk={risk:3d} [{pred:12s}] meta={meta:2d}, edge={edge:2d}, bg={bg:2d}")

    print("\n--- Key Observations ---")

    # Check for forensic override
    if results.get('gradient') and results['gradient']['features']:
        edge = results['gradient']['features'].get('Edge Blending', 0)
        bg = results['gradient']['features'].get('Background Warping', 0)
        forensics_avg = (edge + bg) / 2
        risk = results['gradient']['risk_score']
        print(f"1. Forensic Override Check:")
        print(f"   Gradient: edge={edge}, bg={bg}, avg={forensics_avg:.1f}, risk={risk}")
        if forensics_avg > 80 and risk < 50:
            print(f"   → Override WAS triggered (forensics boosted risk)")
        elif forensics_avg > 80:
            print(f"   → Forensics high but no override needed (CNN already high)")
        else:
            print(f"   → Forensics did not trigger override")

    # Check EXIF penalty
    if results.get('solid_no_exif') and results.get('solid_with_exif'):
        meta_no = results['solid_no_exif']['features'].get('Metadata Anomalies', 0)
        meta_with = results['solid_with_exif']['features'].get('Metadata Anomalies', 0)
        risk_no = results['solid_no_exif']['risk_score']
        risk_with = results['solid_with_exif']['risk_score']
        print(f"\n2. EXIF Penalty Check:")
        print(f"   No EXIF:  meta={meta_no:2d}, risk={risk_no}")
        print(f"   With EXIF: meta={meta_with:2d}, risk={risk_with}")
        print(f"   Impact: EXIF penalty adds {meta_no - meta_with} to metadata_score")
        print(f"   Risk difference: {risk_no - risk_with}")

    print("\n--- Recommended Fixes ---")
    print("1. REMOVE lines 411-416: Forensic override that can increase CNN risk")
    print("   Current: forensics_avg > 80 and raw_risk < 50 → boost risk")
    print("   Issue: Can create false positives on real images with natural noise")
    print()
    print("2. REDUCE EXIF penalty at lines 358-364:")
    print("   Current: metadata_score=45 when EXIF missing")
    print("   Proposed: metadata_score=20 (still penalizes, but less aggressive)")
    print("   Rationale: Many legitimate images lack EXIF (screenshots, edited photos)")
    print()
    print("3. DO NOT change thresholds yet - validate with more test cases first")
    print()
    print("4. Note: These changes reduce false positives but may slightly")
    print("   reduce precision on detecting actual deepfakes.")

    return results

if __name__ == "__main__":
    # Suppress excessive logging during tests
    import logging
    logging.getLogger().setLevel(logging.WARNING)

    results = run_all_tests()

    # Save detailed results
    with open('test_results.json', 'w') as f:
        json.dump({k: v for k, v in results.items() if v is not None}, f, indent=2, default=str)

    print(f"\n\nResults saved to: test_results.json")