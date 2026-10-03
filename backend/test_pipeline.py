import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routes.security import get_url_model
from services.url_feature_extractor import extract_features_from_url
from services.message_analyzer import analyze_message_text
from services.deepfake_analyzer import analyze_deepfake
import numpy as np
from PIL import Image
import io

def test_url_analysis():
    print("=" * 60)
    print("TESTING URL PHISHING DETECTION")
    print("=" * 60)

    model_data = get_url_model()
    model = model_data['model']
    feature_names = model_data['features']

    test_urls = [
        ("https://www.google.com", "Legitimate"),
        ("https://github.com", "Legitimate"),
        ("http://paypal-security-update.fake-site.com/login", "Phishing"),
        ("http://192.168.1.1/admin", "Phishing"),
        ("https://www.amazon.com", "Legitimate"),
        ("http://secure-login-bank-verify.tk/account", "Phishing"),
    ]

    for url, expected in test_urls:
        features, explanations = extract_features_from_url(url)
        vector = [features[feat] for feat in feature_names]
        prob = model.predict_proba([vector])[0][1]
        risk_score = int(prob * 100)

        if risk_score >= 70:
            prediction = "Phishing"
        elif risk_score >= 35:
            prediction = "Suspicious"
        else:
            prediction = "Legitimate"

        status = "PASS" if prediction == expected or (expected == "Phishing" and prediction in ["Phishing", "Suspicious"]) else "FAIL"
        print(f"\n[{status}] URL: {url}")
        print(f"   Expected: {expected}, Got: {prediction} (Risk: {risk_score})")
        if explanations:
            for exp in explanations[:2]:
                print(f"   - {exp}")

def test_message_analysis():
    print("\n" + "=" * 60)
    print("TESTING MESSAGE/SPAM DETECTION")
    print("=" * 60)

    test_messages = [
        ("Hey, are we still meeting for lunch today?", "Legitimate"),
        ("URGENT: Your account has been suspended! Text back bank details to verify or claim your free $1000 prize now!", "Phishing/Spam"),
        ("Your Amazon package has been delayed. Click here to reschedule: http://fake-amazon.com/track", "Phishing/Spam"),
        ("Meeting reminder: Team standup at 10am tomorrow", "Legitimate"),
    ]

    for msg, expected in test_messages:
        analysis = analyze_message_text(msg)
        status = "PASS" if analysis['prediction'] == expected or (expected == "Phishing/Spam" and analysis['prediction'] in ["Phishing/Spam", "Suspicious"]) else "FAIL"
        print(f"\n[{status}] Message: {msg[:60]}...")
        print(f"   Expected: {expected}, Got: {analysis['prediction']} (Risk: {analysis['risk_score']})")
        for fb in analysis['feedback'][:2]:
            print(f"   - {fb}")

def test_deepfake_analysis():
    print("\n" + "=" * 60)
    print("TESTING DEEPFAKE DETECTION")
    print("=" * 60)

    # Test case 1: Standard camera photo with genuine EXIF
    print("\nTest 1: Camera Photo with Genuine EXIF")
    img1 = Image.new("RGB", (128, 128), (150, 180, 200))
    exif1 = img1.getexif()
    exif1[271] = "Sony"
    exif1[272] = "ILCE-7RM3"
    buf1 = io.BytesIO()
    img1.save(buf1, format="JPEG", exif=exif1)
    result1 = analyze_deepfake(buf1.getvalue(), "vacation_photo.jpg", "image/jpeg")
    print(f"   Prediction: {result1['prediction']} (Risk: {result1['risk_score']}%)")
    for fb in result1['feedback']:
        print(f"   - {fb}")

    # Test case 2: Image with AI signature in EXIF
    print("\nTest 2: AI Generated Image (DALL-E Signature)")
    img2 = Image.new("RGB", (128, 128), (100, 100, 100))
    exif2 = img2.getexif()
    exif2[305] = "dall-e generator v3"
    buf2 = io.BytesIO()
    img2.save(buf2, format="JPEG", exif=exif2)
    payload2 = buf2.getvalue() + b" creator: dall-e"
    result2 = analyze_deepfake(payload2, "fantasy_landscape.png", "image/png")
    print(f"   Prediction: {result2['prediction']} (Risk: {result2['risk_score']}%)")
    for fb in result2['feedback']:
        print(f"   - {fb}")

    # Test case 3: Screenshot (missing EXIF)
    print("\nTest 3: Screenshot/Web Image (Missing EXIF)")
    img3 = Image.new("RGB", (128, 128), (120, 120, 120))
    buf3 = io.BytesIO()
    img3.save(buf3, format="PNG")
    result3 = analyze_deepfake(buf3.getvalue(), "screenshot.png", "image/png")
    print(f"   Prediction: {result3['prediction']} (Risk: {result3['risk_score']}%)")
    for fb in result3['feedback']:
        print(f"   - {fb}")

    # Test case 4: Suspect video
    print("\nTest 4: Suspect Video (FFmpeg)")
    dummy_video = b"Video container block. ftyp mp42. software: Lavf58.29.100 (ffmpeg conversion tool)."
    result4 = analyze_deepfake(dummy_video, "deepfake_swap.mp4", "video/mp4")
    print(f"   Prediction: {result4['prediction']} (Risk: {result4['risk_score']}%)")
    for fb in result4['feedback']:
        print(f"   - {fb}")

if __name__ == "__main__":
    test_url_analysis()
    test_message_analysis()
    test_deepfake_analysis()
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)