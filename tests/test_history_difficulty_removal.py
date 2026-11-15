"""
Automated Test Suite for Quiz History:
- Verify Difficulty column is completely removed from Existing Quizzes history tab.
- Verify Difficulty column is preserved in AI-Generated Quizzes history tab.
- Verify Easy, Medium, Hard values still display for AI quizzes.
- Verify other columns (Quiz Title, Subject, Topic, Score, Accuracy, Time Taken, Attempt Date) are preserved.
- Verify database records for difficulty are untouched.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection

def test_history_difficulty():
    print("=" * 70)
    print("TESTING QUIZ HISTORY DIFFICULTY COLUMN REMOVAL & PRESERVATION")
    print("=" * 70)

    app.config["TESTING"] = True
    client = app.test_client()

    conn = get_db_connection()
    cursor = conn.cursor()

    test_student_id = None
    existing_attempt_id = None
    ai_attempt_id = None

    try:
        # Create test student
        test_email = f"history_diff_test_{int(time.time())}@example.com"
        cursor.execute(
            """
            INSERT INTO students (name, email, password_hash)
            VALUES ('History Test Student', %s, 'dummy_hash')
            RETURNING student_id
            """,
            (test_email,)
        )
        test_student_id = cursor.fetchone()[0]

        # 1. Insert existing quiz attempt (Quiz 1 has difficulty 'Medium' in DB)
        cursor.execute(
            """
            INSERT INTO quiz_attempts (student_id, quiz_id, started_at, submitted_at, time_taken_seconds, score, accuracy, total_questions, correct_answers)
            VALUES (%s, 1, CURRENT_TIMESTAMP - INTERVAL '30 minutes', CURRENT_TIMESTAMP - INTERVAL '25 minutes', 72, 85.0, 85.0, 10, 8)
            RETURNING attempt_id
            """,
            (test_student_id,)
        )
        existing_attempt_id = cursor.fetchone()[0]

        # 2. Insert AI quiz attempt (with difficulty 'Hard')
        cursor.execute(
            """
            INSERT INTO ai_quiz_attempts (student_id, topic, difficulty, num_questions, total_questions, score, accuracy, correct_answers, time_taken_seconds, started_at, submitted_at, questions_data, student_answers)
            VALUES (%s, 'Distributed Systems', 'Hard', 5, 5, 80.0, 80.0, 4, 110, CURRENT_TIMESTAMP - INTERVAL '20 minutes', CURRENT_TIMESTAMP - INTERVAL '15 minutes', '[]', '{}')
            RETURNING ai_attempt_id
            """,
            (test_student_id,)
        )
        ai_attempt_id = cursor.fetchone()[0]

        conn.commit()
        print(f"  --> Seeded test student #{test_student_id} with Existing Attempt #{existing_attempt_id} and AI Attempt #{ai_attempt_id}.")

        # Log in student
        with client.session_transaction() as sess:
            sess["student_id"] = test_student_id
            sess["student_name"] = "History Test Student"

        print("\n[STEP 1] Fetching Quiz History Page...")
        res = client.get("/history")
        assert res.status_code == 200, f"Expected status 200, got {res.status_code}"
        html = res.get_data(as_text=True)

        # Split HTML by tab containers to inspect each separately
        assert 'id="existing-quizzes"' in html, "Existing quizzes tab container must exist"
        assert 'id="ai-quizzes"' in html, "AI quizzes tab container must exist"

        existing_tab_part = html.split('id="existing-quizzes"')[1].split('id="ai-quizzes"')[0]
        ai_tab_part = html.split('id="ai-quizzes"')[1]

        print("\n[STEP 2] Verifying Existing Quizzes History Tab...")
        # 1. Check Difficulty header is NOT present in Existing Quizzes table
        assert "<th>Difficulty</th>" not in existing_tab_part, "Difficulty column header must be REMOVED from Existing Quizzes table"
        print("  [PASS] Difficulty column header is completely absent from Existing Quizzes table.")

        # 2. Check Difficulty badge/label (e.g. Medium) is NOT rendered for existing quiz attempt
        assert ">Medium<" not in existing_tab_part, "Difficulty badge 'Medium' must NOT be rendered in Existing Quizzes table"
        assert ">Easy<" not in existing_tab_part, "Difficulty badge 'Easy' must NOT be rendered in Existing Quizzes table"
        assert ">Hard<" not in existing_tab_part, "Difficulty badge 'Hard' must NOT be rendered in Existing Quizzes table"
        print("  [PASS] No difficulty labels (Easy/Medium/Hard) appear in Existing Quizzes records.")

        # 3. Check all other columns are preserved in Existing Quizzes table
        assert "Quiz Title" in existing_tab_part
        assert "<th>Subject</th>" in existing_tab_part
        assert "<th>Topic</th>" in existing_tab_part
        assert "<th>Score</th>" in existing_tab_part
        assert "<th>Accuracy</th>" in existing_tab_part
        assert "<th>Time Taken</th>" in existing_tab_part
        assert "<th>Attempt Date</th>" in existing_tab_part
        assert "Action" in existing_tab_part

        # Check values for Attempt
        assert f"Attempt #{existing_attempt_id}" in existing_tab_part
        assert "85" in existing_tab_part
        assert "72s" in existing_tab_part or "1m 12s" in existing_tab_part
        assert "View Result" in existing_tab_part
        print("  [PASS] All other existing columns and values (Quiz Title, Subject, Topic, Score, Accuracy, Time Taken, Date, Action) are preserved.")

        print("\n[STEP 3] Verifying AI-Generated Quizzes History Tab...")
        # 1. Check Difficulty header IS present in AI Quizzes table
        assert "<th>Difficulty</th>" in ai_tab_part, "Difficulty column header must be PRESERVED in AI-Generated Quizzes table"
        print("  [PASS] Difficulty column header is present in AI-Generated Quizzes table.")

        # 2. Check Difficulty badge displays 'Hard' for our AI quiz attempt
        assert "Hard" in ai_tab_part and "bg-danger" in ai_tab_part, "Difficulty badge 'Hard' must be rendered in AI Quizzes table"
        assert "Distributed Systems" in ai_tab_part
        assert "80" in ai_tab_part
        assert "5 Items" in ai_tab_part
        print("  [PASS] AI-Generated Quizzes table correctly displays the difficulty badge ('Hard') and quiz details.")

        print("\n[STEP 4] Verifying Database Restrictions...")
        cursor.execute("SELECT difficulty FROM quizzes WHERE quiz_id = 1")
        db_diff = cursor.fetchone()[0]
        assert db_diff is not None, "Difficulty column in quizzes table must remain intact"
        print(f"  [PASS] Database difficulty records remain preserved: Quiz 1 difficulty is '{db_diff}'.")

        cursor.execute("SELECT difficulty FROM ai_quiz_attempts WHERE ai_attempt_id = %s", (ai_attempt_id,))
        ai_db_diff = cursor.fetchone()[0]
        assert ai_db_diff == "Hard"
        print(f"  [PASS] Database ai_quiz_attempts difficulty remains intact: '{ai_db_diff}'.")

        print("\n" + "=" * 70)
        print("ALL QUIZ HISTORY DIFFICULTY TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        # Cleanup
        try:
            if existing_attempt_id:
                cursor.execute("DELETE FROM quiz_attempts WHERE attempt_id = %s", (existing_attempt_id,))
            if ai_attempt_id:
                cursor.execute("DELETE FROM ai_quiz_attempts WHERE ai_attempt_id = %s", (ai_attempt_id,))
            if test_student_id:
                cursor.execute("DELETE FROM students WHERE student_id = %s", (test_student_id,))
            conn.commit()
            cursor.close()
            conn.close()
            print("  --> Test data cleaned up successfully.")
        except Exception as e:
            print(f"  --> Cleanup warning: {e}")

if __name__ == "__main__":
    test_history_difficulty()
