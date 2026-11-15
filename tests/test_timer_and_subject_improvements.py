"""
Comprehensive Automated Test Suite for:
1. Dynamic Subject and Topic Selection (including empty topics warning & DB additions)
2. Simplified "Start Quiz" button (Step 4 removed)
3. Quiz Timer Fix on Every Quiz (fresh 00:00 start, page refresh continuity, starting another quiz, submission stop)
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection

def test_dynamic_selection_and_timers():
    print("=" * 70)
    print("TESTING DYNAMIC SUBJECT/TOPIC SELECTION AND QUIZ TIMERS")
    print("=" * 70)

    app.config["TESTING"] = True
    client = app.test_client()

    conn = get_db_connection()
    cursor = conn.cursor()

    test_student_id = None
    test_subject_id = None
    test_topic_id = None

    try:
        # 1. Create a test student
        test_email = f"timer_test_{int(time.time())}@example.com"
        cursor.execute(
            """
            INSERT INTO students (name, email, password_hash)
            VALUES ('Timer Test Student', %s, 'dummy_hash')
            RETURNING student_id
            """,
            (test_email,)
        )
        test_student_id = cursor.fetchone()[0]
        conn.commit()

        # Login student
        with client.session_transaction() as sess:
            sess["student_id"] = test_student_id
            sess["student_name"] = "Timer Test Student"

        print(f"\n[PHASE 1] Dynamic Subject & Topic Selection...")
        # A. Check initial subjects & topics
        r = client.get("/quizzes")
        assert r.status_code == 200
        html = r.data.decode("utf-8")
        assert "Select Subject" in html
        assert "Select Topic" in html
        assert "Start Quiz" in html
        assert "Step 4: Start Quiz" not in html
        print("  --> Baseline selection page verified: 'Start Quiz' present, 'Step 4:' absent.")

        # B. Dynamically add a new subject to PostgreSQL (with NO topics yet)
        test_subj_name = f"Quantum Computing {int(time.time()) % 10000}"
        cursor.execute(
            "INSERT INTO subjects (subject_name) VALUES (%s) RETURNING subject_id",
            (test_subj_name,)
        )
        test_subject_id = cursor.fetchone()[0]
        conn.commit()

        # Check that new subject appears in dropdown
        r = client.get("/quizzes")
        html = r.data.decode("utf-8")
        assert test_subj_name in html, f"New subject {test_subj_name} should appear dynamically in dropdown"
        print(f"  --> Dynamic subject addition confirmed: '{test_subj_name}' appeared in dropdown.")

        # C. Select this new subject (which has 0 topics) -> verify no topics message
        r = client.get(f"/quizzes?subject_id={test_subject_id}")
        html = r.data.decode("utf-8")
        assert "No topics are currently available for this subject" in html, "Should display warning when no topics exist"
        assert "-- No Topics Available for this Subject --" in html, "Topic dropdown should show no topics available option"
        print("  --> Empty topics state verified: 'No topics are currently available' message and option displayed.")

        # D. Dynamically add a topic to this subject in PostgreSQL
        test_top_name = f"Qubits and Entanglement"
        cursor.execute(
            "INSERT INTO topics (subject_id, topic_name) VALUES (%s, %s) RETURNING topic_id",
            (test_subject_id, test_top_name)
        )
        test_topic_id = cursor.fetchone()[0]
        conn.commit()

        # Now load with subject selected -> topic should appear dynamically
        r = client.get(f"/quizzes?subject_id={test_subject_id}")
        html = r.data.decode("utf-8")
        assert test_top_name in html, f"New topic '{test_top_name}' should appear dynamically in dropdown"
        print(f"  --> Dynamic topic addition confirmed: '{test_top_name}' appeared under subject.")

        # E. Verify topic reset when changing subject
        # If student requests subject 1 with topic from the new subject, it resets topic
        r = client.get(f"/quizzes?subject_id=1&topic_id={test_topic_id}")
        html = r.data.decode("utf-8")
        # Topic should be reset because test_topic_id does not belong to subject 1
        assert f'value="{test_topic_id}" selected' not in html
        print("  --> Subject change topic reset confirmed: mismatching topic is safely reset.")

        print(f"\n[PHASE 2] Existing Quiz Timer Fix...")
        # 1. Insert an ancient unsubmitted attempt from 10 days ago for Quiz 1
        ten_days_ago = datetime.now() - timedelta(days=10)
        cursor.execute(
            """
            INSERT INTO quiz_attempts (student_id, quiz_id, started_at)
            VALUES (%s, 1, %s)
            RETURNING attempt_id
            """,
            (test_student_id, ten_days_ago)
        )
        old_attempt_id = cursor.fetchone()[0]
        conn.commit()
        print(f"  --> Seeded old abandoned attempt #{old_attempt_id} from 10 days ago.")

        # 2. When student clicks Start Quiz for Quiz 1 from selection page:
        # First visit selection page (which clears session attempt keys)
        client.get("/quizzes")
        r_start = client.get("/quiz/1")
        assert r_start.status_code == 200
        html_quiz = r_start.data.decode("utf-8")
        
        # Verify attempt ID is NOT the old 10-day-old attempt!
        with client.session_transaction() as sess:
            new_attempt_id = sess.get("active_quiz_attempt_id")
        
        assert new_attempt_id is not None
        assert new_attempt_id != old_attempt_id, f"Should NOT resume 10-day old attempt {old_attempt_id}!"
        print(f"  --> Ancient attempt ignored! Created brand new attempt #{new_attempt_id}.")

        # Check elapsed_seconds passed to template is 0
        assert 'data-initial-elapsed="0"' in html_quiz
        assert 'id="stopwatchDisplay"' in html_quiz
        assert f'data-attempt-id="existing_{new_attempt_id}"' in html_quiz
        print("  --> Fresh attempt initialized at 00:00 with data-initial-elapsed='0'.")

        # 3. Test page refresh resilience:
        # Refresh the quiz page (GET /quiz/1 with active session)
        time.sleep(1.2)  # small pause
        r_refresh = client.get("/quiz/1")
        assert r_refresh.status_code == 200
        with client.session_transaction() as sess:
            refreshed_attempt_id = sess.get("active_quiz_attempt_id")
        assert refreshed_attempt_id == new_attempt_id, "Page refresh must maintain the same attempt ID"
        print(f"  --> Page refresh maintained attempt #{new_attempt_id} without creating duplicate attempts.")

        # 4. Submit the quiz
        # Fetch question IDs for quiz 1
        cursor.execute("SELECT question_id FROM quiz_questions WHERE quiz_id = 1 ORDER BY question_id")
        q_ids = [row[0] for row in cursor.fetchall()]
        form_data = {"attempt_id": str(new_attempt_id)}
        for qid in q_ids:
            form_data[f"question_{qid}"] = "A"

        r_sub = client.post("/quiz/1", data=form_data, follow_redirects=True)
        assert r_sub.status_code == 200
        res_html = r_sub.data.decode("utf-8")
        assert "Time Elapsed" in res_html
        with client.session_transaction() as sess:
            assert sess.get("active_quiz_attempt_id") is None, "active_quiz_attempt_id should be cleared after submit"
        print(f"  --> Quiz submitted successfully. Active attempt session cleared, time recorded on result page.")

        # 5. Starting another quiz starts a brand new attempt at 00:00
        r_start2 = client.get("/quiz/1")
        assert r_start2.status_code == 200
        with client.session_transaction() as sess:
            second_attempt_id = sess.get("active_quiz_attempt_id")
        assert second_attempt_id != new_attempt_id, "Starting another quiz must generate a brand new attempt"
        html_start2 = r_start2.data.decode("utf-8")
        assert 'data-initial-elapsed="0"' in html_start2
        print(f"  --> Starting another quiz initialized fresh attempt #{second_attempt_id} with 00:00 elapsed.")

        print(f"\n[PHASE 3] AI Quiz Timer Fix...")
        # 1. Create an AI quiz attempt
        questions_payload = [
            {
                "question_id": 1,
                "question_text": "What is Python?",
                "options": {"A": "A language", "B": "A snake", "C": "A database", "D": "An OS"},
                "correct_option": "A",
                "explanation": "Python is a high-level programming language."
            }
        ]
        cursor.execute(
            """
            INSERT INTO ai_quiz_attempts 
            (student_id, topic, difficulty, num_questions, total_questions, questions_data, started_at)
            VALUES (%s, 'Python', 'Easy', 1, 1, %s, %s)
            RETURNING ai_attempt_id
            """,
            (test_student_id, json.dumps(questions_payload), ten_days_ago)
        )
        ai_attempt_id = cursor.fetchone()[0]
        conn.commit()

        # 2. Open the AI quiz runner
        r_ai = client.get(f"/ai-quiz/start/{ai_attempt_id}")
        assert r_ai.status_code == 200
        ai_html = r_ai.data.decode("utf-8")
        assert 'data-initial-elapsed="0"' in ai_html, "AI Quiz timer must start fresh at 00:00"
        assert f'data-attempt-id="ai_{ai_attempt_id}"' in ai_html
        with client.session_transaction() as sess:
            assert sess.get("active_ai_attempt_id") == ai_attempt_id
        print(f"  --> AI Quiz #{ai_attempt_id} opened fresh: timer starts at 00:00 (old started_at updated to NOW).")

        # 3. Refresh AI Quiz runner
        time.sleep(1.2)
        r_ai_ref = client.get(f"/ai-quiz/start/{ai_attempt_id}")
        assert r_ai_ref.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get("active_ai_attempt_id") == ai_attempt_id
        print(f"  --> AI Quiz refresh preserved attempt #{ai_attempt_id}.")

        # 4. Submit AI quiz
        ai_sub = client.post(
            f"/ai-quiz/submit/{ai_attempt_id}",
            data={"question_1": "A"},
            follow_redirects=True
        )
        assert ai_sub.status_code == 200
        ai_res_html = ai_sub.data.decode("utf-8")
        assert "Time Elapsed" in ai_res_html
        with client.session_transaction() as sess:
            assert sess.get("active_ai_attempt_id") is None, "active_ai_attempt_id should be cleared after submit"
        print(f"  --> AI Quiz submitted. Stopwatch stopped, elapsed recorded and displayed on result.")

        print("\n" + "=" * 70)
        print(">>> ALL VERIFICATION TESTS PASSED SUCCESSFULLY! <<<")
        print("=" * 70)

    finally:
        # Cleanup test data
        if test_student_id:
            cursor.execute("DELETE FROM student_answers WHERE attempt_id IN (SELECT attempt_id FROM quiz_attempts WHERE student_id = %s)", (test_student_id,))
            cursor.execute("DELETE FROM retention_schedules WHERE student_id = %s", (test_student_id,))
            cursor.execute("DELETE FROM quiz_attempts WHERE student_id = %s", (test_student_id,))
            cursor.execute("DELETE FROM ai_quiz_attempts WHERE student_id = %s", (test_student_id,))
            cursor.execute("DELETE FROM students WHERE student_id = %s", (test_student_id,))
        if test_topic_id:
            cursor.execute("DELETE FROM topics WHERE topic_id = %s", (test_topic_id,))
        if test_subject_id:
            cursor.execute("DELETE FROM subjects WHERE subject_id = %s", (test_subject_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print("[CLEANUP] Purged temporary test entities.")

if __name__ == "__main__":
    test_dynamic_selection_and_timers()
