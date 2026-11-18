"""
Automated Test Suite for Practice Recommendations Modification:
- Case 1: Newly registered student with zero quiz attempts sees the required empty-state message.
- Zero recommendations are generated or persisted in the database for students without quiz attempts.
- No default, foundational, or sample recommendations are generated.
- Case 2: Student with quiz attempts receives personalized practice recommendations based on actual performance.
- Cross-student isolation: One student's quiz attempts do not leak into another student's recommendations.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from analytics.recommendations import get_or_generate_recommendations

EXPECTED_EMPTY_MSG = (
    "No practice recommendations available yet. Attempt your first quiz to "
    "receive personalized practice recommendations based on your performance."
)

def test_practice_recommendations():
    print("=" * 70)
    print("TESTING PRACTICE RECOMMENDATIONS FOR NEW & EXISTING STUDENTS")
    print("=" * 70)

    app.config["TESTING"] = True
    client = app.test_client()

    conn = get_db_connection()
    cursor = conn.cursor()

    student_a_id = None
    student_b_id = None
    attempt_ids = []

    try:
        # -------------------------------------------------------------
        # STEP 1: Newly Registered Student A (Zero Quiz Attempts)
        # -------------------------------------------------------------
        print("\n[STEP 1] Testing Newly Registered Student (Zero Quiz Attempts)...")
        email_a = f"newbie_rec_a_{int(time.time())}@example.com"
        cursor.execute(
            """
            INSERT INTO students (name, email, password_hash)
            VALUES ('New Student Alpha', %s, 'dummy_hash')
            RETURNING student_id
            """,
            (email_a,)
        )
        student_a_id = cursor.fetchone()[0]
        conn.commit()
        print(f"  --> Created Student A (ID: {student_a_id}) with 0 quiz attempts.")

        # Backend function check
        rec_data_a = get_or_generate_recommendations(student_a_id)
        assert rec_data_a["has_attempts"] is False, "Expected has_attempts to be False for zero-attempt student"
        assert rec_data_a["total_attempts"] == 0, "Expected total_attempts == 0"
        assert rec_data_a["total_recommendations"] == 0, "Expected 0 total recommendations"
        assert len(rec_data_a["active_recommendations"]) == 0, "Expected empty active_recommendations"
        assert len(rec_data_a["completed_recommendations"]) == 0, "Expected empty completed_recommendations"
        print("  [PASS] Backend returned has_attempts=False and empty recommendation lists.")

        # Database verification: No recommendations were generated or inserted
        cursor.execute(
            "SELECT COUNT(*) FROM practice_recommendations WHERE student_id = %s",
            (student_a_id,)
        )
        db_rec_count = cursor.fetchone()[0]
        assert db_rec_count == 0, f"Expected 0 recommendations in DB, found {db_rec_count}"
        print("  [PASS] Confirmed 0 practice_recommendations records in PostgreSQL for Student A.")

        # HTTP Route Check
        with client.session_transaction() as sess:
            sess["student_id"] = student_a_id
            sess["student_name"] = "New Student Alpha"

        res_a = client.get("/recommendations")
        assert res_a.status_code == 200, f"Expected status 200, got {res_a.status_code}"
        html_a = res_a.get_data(as_text=True)

        # Verify the exact required message is present
        assert EXPECTED_EMPTY_MSG in html_a, "Required empty-state message missing from HTML"
        print("  [PASS] Exact required empty-state message rendered on /recommendations page.")

        # Verify no recommendation cards or misleading metric cards are shown
        assert "Active Practice Recommendations" not in html_a
        assert "rec-card rec-card-" not in html_a
        assert "Urgent Attention Recommended" not in html_a
        print("  [PASS] No recommendation cards or urgent banners displayed for Student A.")

        # -------------------------------------------------------------
        # STEP 2: Student A Attempts a Quiz (Transitions to Case 2)
        # -------------------------------------------------------------
        print("\n[STEP 2] Student A Completes a Quiz Attempt (Low accuracy in Topic 1)...")
        # Fetch question IDs for Quiz 1
        cursor.execute(
            """
            SELECT q.question_id, q.topic_id 
            FROM questions q 
            JOIN quiz_questions qq ON q.question_id = qq.question_id 
            WHERE qq.quiz_id = 1 
            ORDER BY q.question_id ASC
            LIMIT 5
            """
        )
        q_rows = cursor.fetchall()
        assert len(q_rows) > 0, "Quiz 1 must have questions"

        # Insert attempt: Score 20% (1/5 correct), creating a weak topic gap
        cursor.execute(
            """
            INSERT INTO quiz_attempts (student_id, quiz_id, started_at, submitted_at, time_taken_seconds, score, accuracy, total_questions, correct_answers)
            VALUES (%s, 1, CURRENT_TIMESTAMP - INTERVAL '15 minutes', CURRENT_TIMESTAMP, 120, 20.0, 20.0, 5, 1)
            RETURNING attempt_id
            """,
            (student_a_id,)
        )
        att_id = cursor.fetchone()[0]
        attempt_ids.append(att_id)

        # Insert student answers: 1 correct, 4 incorrect
        for i, (qid, _) in enumerate(q_rows):
            is_corr = (i == 0)
            cursor.execute(
                """
                INSERT INTO student_answers (attempt_id, question_id, selected_option, is_correct)
                VALUES (%s, %s, %s, %s)
                """,
                (att_id, qid, 'A' if is_corr else 'B', is_corr)
            )

        conn.commit()
        print(f"  --> Recorded Attempt #{att_id} with 20% accuracy for Student A.")

        # Backend check for Student A with attempts
        rec_data_a2 = get_or_generate_recommendations(student_a_id)
        assert rec_data_a2["has_attempts"] is True, "Expected has_attempts to be True after attempting a quiz"
        assert rec_data_a2["total_attempts"] == 1, "Expected total_attempts == 1"
        assert rec_data_a2["total_recommendations"] > 0, "Expected recommendations to be generated"
        print(f"  [PASS] Backend generated {rec_data_a2['total_recommendations']} personalized recommendation(s) for Student A.")

        # HTTP Route Check for Student A with attempts
        res_a2 = client.get("/recommendations")
        assert res_a2.status_code == 200
        html_a2 = res_a2.get_data(as_text=True)
        assert EXPECTED_EMPTY_MSG not in html_a2, "Empty state message should NOT be shown when attempts exist"
        assert "Active Practice Recommendations" in html_a2
        assert "Diagnostic Insight" in html_a2
        print("  [PASS] Recommendations page renders active recommendation cards and diagnostic insight.")

        # -------------------------------------------------------------
        # STEP 3: Student Isolation / Cross-Student Test
        # -------------------------------------------------------------
        print("\n[STEP 3] Testing Cross-Student Isolation with Student B...")
        email_b = f"newbie_rec_b_{int(time.time())}@example.com"
        cursor.execute(
            """
            INSERT INTO students (name, email, password_hash)
            VALUES ('New Student Beta', %s, 'dummy_hash')
            RETURNING student_id
            """,
            (email_b,)
        )
        student_b_id = cursor.fetchone()[0]
        conn.commit()
        print(f"  --> Created Student B (ID: {student_b_id}) with 0 quiz attempts while Student A has attempts.")

        # Log in as Student B
        with client.session_transaction() as sess:
            sess["student_id"] = student_b_id
            sess["student_name"] = "New Student Beta"

        # Verify Student B does NOT see Student A's recommendations
        rec_data_b = get_or_generate_recommendations(student_b_id)
        assert rec_data_b["has_attempts"] is False, "Student B must have has_attempts=False"
        assert rec_data_b["total_recommendations"] == 0, "Student B must have 0 recommendations"

        res_b = client.get("/recommendations")
        assert res_b.status_code == 200
        html_b = res_b.get_data(as_text=True)
        assert EXPECTED_EMPTY_MSG in html_b, "Student B must see empty-state message"
        assert "Active Practice Recommendations" not in html_b or "rec-card-high" not in html_b
        print("  [PASS] Student B is completely isolated from Student A's recommendations.")

        print("\n" + "=" * 70)
        print("ALL PRACTICE RECOMMENDATIONS VERIFICATION TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        # Cleanup
        try:
            if attempt_ids:
                cursor.execute("DELETE FROM student_answers WHERE attempt_id = ANY(%s)", (attempt_ids,))
                cursor.execute("DELETE FROM quiz_attempts WHERE attempt_id = ANY(%s)", (attempt_ids,))
            if student_a_id:
                cursor.execute("DELETE FROM practice_recommendations WHERE student_id = %s", (student_a_id,))
                cursor.execute("DELETE FROM students WHERE student_id = %s", (student_a_id,))
            if student_b_id:
                cursor.execute("DELETE FROM practice_recommendations WHERE student_id = %s", (student_b_id,))
                cursor.execute("DELETE FROM students WHERE student_id = %s", (student_b_id,))
            conn.commit()
            cursor.close()
            conn.close()
            print("  --> Test data cleaned up successfully.")
        except Exception as e:
            print(f"  --> Cleanup warning: {e}")

if __name__ == "__main__":
    test_practice_recommendations()
