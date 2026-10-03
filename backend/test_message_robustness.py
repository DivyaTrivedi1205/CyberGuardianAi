#!/usr/bin/env python3
"""
Robustness Testing for Message/SMS Spam Detection.

Tests the model's ability to handle various message patterns.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.message_analyzer import get_message_model


def get_model_proba(message: str) -> float:
    """Get spam probability from the model."""
    model = get_message_model()
    proba = model.predict_proba([message])[0][1]
    return proba


def run_test(test_name: str, messages: list, is_spam: bool = None):
    """Run a test and report results."""
    print("=" * 70)
    print(test_name)
    print("=" * 70)
    print(f"\nTesting {len(messages)} messages...")

    detected = 0
    missed = 0
    false_pos = 0

    for msg in messages:
        proba = get_model_proba(msg)
        risk_score = int(proba * 100)
        is_spam_msg = proba >= 0.5

        if is_spam_msg and is_spam is None:
            detected += 1
            status = "DETECTED"
        elif not is_spam_msg and is_spam is True:
            missed += 1
            status = "MISSED"
        elif not is_spam_msg and is_spam is None:
            false_pos += 1
            status = "FALSE_POS"
        else:
            status = "CORRECT"

        # Truncate for display
        display_msg = msg[:120] + "..." if len(msg) > 120 else msg
        print(f"[{status}] Risk: {risk_score:3d}/100 - {display_msg}")

    print()
    return detected, missed, false_pos


def main():
    """Run all robustness tests."""
    print()
    print("#" * 70)
    print("# CYBERGUARDIAN - MESSAGE SPAM DETECTION ROBUSTNESS TESTS")
    print("#" * 70)
    print()

    total_detected = 0
    total_missed = 0
    total_false_pos = 0

    # Test 1: Normal spam messages
    spam_msgs = [
        "FREE ENTRY into our prize draw! Text ENTER to 88015. T&C www.txtservice.co.uk",
        "Congratulations! You've won a free iPhone. Reply CLAIM to claim now!",
        "Your weekly mobile entertainment package ready. Reply STOP to unsubscribe.",
        "Win a gift card! Text WIN to 85023. www.free-prize-win.com",
    ]
    d, m, fp = run_test("NORMAL SPAM MESSAGES", spam_msgs, is_spam=True)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 2: Normal ham messages
    ham_msgs = [
        "Hey, are we still meeting for lunch at 12?",
        "Don't forget to bring the documents for tomorrow's meeting.",
        "The package has been delivered to the front desk.",
        "Can you call me back when you get this? Thanks!",
    ]
    d, m, fp = run_test("NORMAL HAM (LEGITIMATE) MESSAGES", ham_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 3: Short messages
    short_msgs = [
        "Call me",
        "On my way",
        "Sorry late",
        "Meeting cancelled",
        "Yes please",
    ]
    d, m, fp = run_test("SHORT MESSAGES", short_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 4: Long messages
    long_msgs = [
        "Dear customer, we are pleased to inform you that you have been selected as the winner of our grand prize draw. To claim your prize, please call our claims department immediately at 0871 230 1133.",
        "Hi there, I saw your listing on the marketplace and I'm interested in purchasing the item. I'm willing to pay full price and can pick it up immediately.",
    ]
    d, m, fp = run_test("LONG MESSAGES", long_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 5: Messages with URLs
    url_msgs = [
        "Click here to claim: http://bit.ly/free-gift-card",
        "Your order has shipped. Track it: https://www.amazon.com/dp/B001234567",
        "Important: Verify your account at https://secure-login-bank.com",
        "Check out our new products: www.shop-now.com/deals",
    ]
    d, m, fp = run_test("MESSAGES WITH URLS", url_msgs, is_spam=None)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 6: Messages with phone numbers
    phone_msgs = [
        "Text BACK to 80360 to claim your prize",
        "Call us at 0800 123 4567 for more info",
        "Reply YES to 85223 to opt out",
        "Your number: 07700 900123",
    ]
    d, m, fp = run_test("MESSAGES WITH PHONE NUMBERS", phone_msgs, is_spam=None)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 7: Monetary/scam messages
    scam_msgs = [
        "You've won 1000000! Transfer fees required. Call 0871 230 1133",
        "Free 500 gift card for you. Text CLAIM to 88015",
        "Your account has been credited with 100. Confirm details now!",
        "Claim your inheritance: 50000 waiting for you. Call now!",
    ]
    d, m, fp = run_test("MONETARY/SCAM MESSAGES", scam_msgs, is_spam=True)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 8: Urgency language
    urgency_msgs = [
        "URGENT: Your subscription expires in 24 hours!",
        "ACTION REQUIRED: Verify your account now or it will be suspended",
        "LAST CHANCE: This offer ends tonight at midnight!",
        "IMMEDIATELY: Your account needs verification",
    ]
    d, m, fp = run_test("URGENCY LANGUAGE MESSAGES", urgency_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 9: Obfuscated text
    obf_msgs = [
        "Fr33 500 gft crd! Txt CLM to 88015",
        "Cn yu call bck? Nmbr: 07700 900123",
        "V1s1t our w3b site: www.sh0p-n0w.c0m",
        "M3ss4g3 fr0m 4dm1n: V3r1fy n0w!",
    ]
    d, m, fp = run_test("OBFUSCATED TEXT MESSAGES", obf_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 10: Repeated characters
    repeat_msgs = [
        "FREEEEEEEE 500 gift card!!!",
        "URGENT!!! CALL IMMEDIATELY!!!",
        "YESSSSSSS I WON!!! CALL NOW!!!",
        "WOOOOOOHOOOOO Prizes waiting!!!",
    ]
    d, m, fp = run_test("REPEATED CHARACTER MESSAGES", repeat_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 11: Mixed case
    case_msgs = [
        "FrEe 500 GiFt cArD!!!",
        "CoNgRaTuLaTiOnS! YoU hAvE wOn!",
        "UrGeNt AcTiOn ReQuIrEd",
        "FrEe EnTrY iNtO oUr pRiZe dRaWh",
    ]
    d, m, fp = run_test("MIXED CASE MESSAGES", case_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 12: Excessive punctuation
    punct_msgs = [
        "FREE!!! 500!!! CALL NOW!!!",
        "WINNER!!! CALL IMMEDIATELY!!!",
        "URGENT!!! ACT NOW!!!",
        "HOT DEAL!!! Limited time!!!",
    ]
    d, m, fp = run_test("EXCESSIVE PUNCTUATION MESSAGES", punct_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 13: Benign promotional
    benign_msgs = [
        "Your Amazon order has shipped! Track it now.",
        "Reminder: Your appointment is tomorrow at 2pm.",
        "Your monthly statement is ready to view online.",
        "Welcome to our loyalty program! Here's your discount code.",
    ]
    d, m, fp = run_test("BENIGN PROMOTIONAL MESSAGES", benign_msgs, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    # Test 14: Scam-like legitimate
    scam_like = [
        "Congratulations! You've been selected for a free trial of our premium service.",
        "Your account has been credited with 10 bonus points.",
        "Important: Please verify your identity to continue using our services.",
        "Offer expires soon: Claim your exclusive discount code now!",
    ]
    d, m, fp = run_test("SCAM-LIKE LEGITIMATE MESSAGES", scam_like, is_spam=False)
    total_detected += d
    total_missed += m
    total_false_pos += fp

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Detected: {total_detected}")
    print(f"Total Missed: {total_missed}")
    print(f"Total False Positives: {total_false_pos}")
    print(f"Total Messages Tested: {total_detected + total_missed + total_false_pos}")
    print()
    print("=" * 70)
    print("ROBUSTNESS TESTING COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
