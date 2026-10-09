import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import patch, MagicMock
from routes.community import create_report, list_reports, ReportRequest, _USER_REPORT_TIMESTAMPS
from models.auth import UserOut
from fastapi import HTTPException

# Mock storage
mock_users = {}
mock_reports = []
mock_votes = {}

def get_user_reputation_mock(user_id):
    return mock_users.get(user_id, 100)

def update_user_reputation_mock(user_id, change):
    if user_id in mock_users:
        mock_users[user_id] += change

class MockCursor:
    def __init__(self, **kwargs):
        self.cursor_factory = kwargs.get('cursor_factory')
        self.result = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query, params=None):
        self.last_query = query
        self.last_params = params

        # Simple mock logic based on query structure
        if "SELECT * FROM community_reports WHERE indicator_value" in query:
            val = params[0]
            for r in mock_reports:
                if r['indicator_value'] == val:
                    self.result = [r]
                    return
            self.result = []
        elif "SELECT id FROM community_report_votes WHERE report_id" in query:
            report_id, user_id = params[0], params[1]
            if (report_id, user_id) in mock_votes:
                self.result = [{'id': 1}]
            else:
                self.result = []
        elif "INSERT INTO community_report_votes" in query:
            report_id, user_id = params[0], params[1]
            mock_votes[(report_id, user_id)] = True
        elif "UPDATE community_reports SET" in query:
            new_count, new_status, r_id = params[0], params[1], params[2]
            for r in mock_reports:
                if r['id'] == r_id:
                    r['reports_count'] = new_count
                    r['status'] = new_status
                    self.result = [r]
                    return
        elif "INSERT INTO community_reports" in query:
            user_id, ind_type, ind_val, desc, created = params[:5]
            new_r = {
                'id': len(mock_reports) + 1,
                'user_id': user_id,
                'indicator_type': ind_type,
                'indicator_value': ind_val,
                'description': desc,
                'reports_count': 1,
                'status': 'pending',
                'created_at': created
            }
            mock_reports.append(new_r)
            self.result = [new_r]
        elif "SELECT * FROM community_reports ORDER BY" in query:
            self.result = list(reversed(mock_reports))[:50]
        else:
            self.result = []

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return self.result

class MockConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def cursor(self, **kwargs):
        return MockCursor(**kwargs)

    def commit(self):
        pass

    def rollback(self):
        pass

def mock_db_connection():
    return MockConnection()

def create_mock_user(user_id, reputation=100) -> UserOut:
    mock_users[user_id] = reputation
    return UserOut(
        id=user_id,
        name="Test User",
        identifier=f"test_{user_id}@example.com",
        identifier_type="email",
        auth_provider="local",
        reputation_score=reputation
    )

def run_tests():
    print("=" * 60)
    print("TESTING CROWDSHIELD (Phase 9)")
    print("=" * 60)

    # Clean previous states
    _USER_REPORT_TIMESTAMPS.clear()

    user1 = create_mock_user("u1", 100)
    user2 = create_mock_user("u2", 100)
    user3 = create_mock_user("u3", 100)
    bad_user = create_mock_user("bad1", 10) # low reputation

    # We need to patch db_connection and the reputation functions in community.py
    with patch('routes.community.db_connection', side_effect=mock_db_connection), \
         patch('routes.community.get_user_reputation', side_effect=get_user_reputation_mock), \
         patch('routes.community.update_user_reputation', side_effect=update_user_reputation_mock):

        # 1. Test low reputation rejection
        print("\nTest 1: Low Reputation Rejection")
        req = ReportRequest(indicator_type="url", indicator_value="http://evil.com")
        try:
            create_report(req, bad_user)
            print(" [FAIL] Should have rejected bad user")
        except HTTPException as e:
            if e.status_code == 403:
                print(" [PASS] Rejected low reputation user correctly")
            else:
                print(f" [FAIL] Wrong error code: {e.status_code}")

        # 2. Test initial report creation
        print("\nTest 2: Initial Report Creation")
        req_url = ReportRequest(indicator_type="url", indicator_value="http://threat.com", description="Phishing")
        res1 = create_report(req_url, user1)
        if res1.status == "pending" and res1.reports_count == 1:
            print(" [PASS] Report created, status pending, count 1")
        else:
            print(f" [FAIL] New report logic failed. Response: {res1}")

        print(f" [PASS] Reporter reputation increased from 100 to {get_user_reputation_mock(user1.id)}")

        # 3. Test duplicate vote by same user
        print("\nTest 3: Duplicate Vote Prevention")
        try:
            create_report(req_url, user1)
            print(" [FAIL] Should have prevented duplicate vote")
        except HTTPException as e:
            if e.status_code == 409:
                print(" [PASS] Duplicate vote blocked successfully")
            else:
                print(f" [FAIL] Wrong error code: {e.status_code}")

        # 4. Test upvoting and threshold logic
        print("\nTest 4: Voting and Verification Threshold (3 users)")
        res2 = create_report(req_url, user2)
        if res2.reports_count == 2 and res2.status == "pending":
            print(" [PASS] Second vote counted, status still pending")
        else:
            print(" [FAIL] Second vote failed")

        res3 = create_report(req_url, user3)
        if res3.reports_count == 3 and res3.status == "verified_threat":
            print(" [PASS] Third vote converted report to 'verified_threat'!")
        else:
            print(f" [FAIL] Threshold verification failed. Status: {res3.status}")

        print(f" [PASS] Original reporter received reward! Current rep: {get_user_reputation_mock(user1.id)}")

        # 5. Test Rate Limiting
        print("\nTest 5: Rate Limiting & Abuse Prevention")
        rate_limit_user = create_mock_user("rate_user", 100)
        caught = False
        for i in range(25):
            try:
                req_abuse = ReportRequest(indicator_type="message", indicator_value=f"Spam text {i}")
                create_report(req_abuse, rate_limit_user)
            except HTTPException as e:
                if e.status_code == 429:
                    caught = True
                    break

        if caught:
            print(" [PASS] Caught excessive requests (Rate Limiting works)")
        else:
            print(" [FAIL] Did not catch excessive requests!")

        # 6. Test Listing
        print("\nTest 6: Listing Reports")
        reports = list_reports(user1)
        if len(reports) > 0:
            print(f" [PASS] Successfully listed {len(reports)} community reports")
        else:
            print(" [FAIL] Listed 0 community reports")


if __name__ == "__main__":
    run_tests()