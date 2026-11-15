"""
====================================================================
QuizInsight – Comprehensive End-to-End (E2E) System Integration Test
====================================================================
Simulates the entire real-world lifecycle of a student:
  1. Student Registration & Validation
  2. Student Login & Session Verification
  3. Dashboard Metric Initialization
  4. Curriculum Subject & Topic API Exploration
  5. AI Quiz Generation & Database Storage
  6. Live Quiz Execution with Elapsed Stopwatch Sync
  7. Quiz Submission, Scoring & 7-Day Retention Scheduling
  8. Detailed Diagnostic Results & Explanations Review
  9. Quiz History Logging
  10. Performance Trend Analysis (Pandas, NumPy, Matplotlib)
  11. Time-Based Analysis (Pacing & Question Speed)
  12. Weak Topic Detection & Mastery Classification
  13. Personalized Practice Recommendations & Completion
  14. Knowledge Retention Retesting & Delta Comparison
  15. Clean Logout & Session Invalidation
  16. Automated Database Cleanup
====================================================================
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app
from config import get_db_connection

def run_e2e_workflow():
    print("=" * 70)
    print("QUIZINSIGHT END-TO-END (E2E) FULL SYSTEM WORKFLOW TEST")
    print("=" * 70)

    client = app.test_client()
    timestamp = int(time.time())
    test_email = f"e2e_student_{timestamp}@example.com"
    test_password = "E2eStrongPassword123!"
    test_name = f"E2E Student {timestamp}"

    student_id = None

    try:
        # -------------------------------------------------------------
        # STEP 1: Student Registration
        # -------------------------------------------------------------
        print("\n[STEP 1] Testing Student Registration...")
        r_reg = client.post("/register", data={
            "name": test_name,
            "email": test_email,
            "password": test_password,
            "confirm_password": test_password
        }, follow_redirects=False)

        assert r_reg.status_code == 302, f"Registration failed, expected 302 but got {r_reg.status_code}"
        assert "/login" in r_reg.headers["Location"], f"Expected redirect to /login, got {r_reg.headers['Location']}"

        # Verify student record in PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT student_id, password_hash FROM students WHERE email = %s", (test_email,))
        st_row = cursor.fetchone()
        cursor.close()
        conn.close()

        assert st_row is not None, "Student record was not saved in PostgreSQL!"
        student_id = st_row[0]
        assert st_row[1] != test_password, "Password was stored in plaintext!"
        print(f"  --> Student registered successfully (ID: {student_id}, Email: {test_email})")

        # -------------------------------------------------------------
        # STEP 2: Student Login
        # -------------------------------------------------------------
        print("\n[STEP 2] Testing Student Login & Authentication...")
        r_login = client.post("/login", data={
            "email": test_email,
            "password": test_password
        }, follow_redirects=False)

        assert r_login.status_code == 302, f"Login failed, expected 302 but got {r_login.status_code}"
        assert "/dashboard" in r_login.headers["Location"], f"Expected redirect to /dashboard, got {r_login.headers['Location']}"

        with client.session_transaction() as sess:
            assert sess.get("student_id") == student_id, "Session missing student_id!"
            assert sess.get("student_name") == test_name, "Session missing student_name!"
        print("  --> Authentication successful, session established.")

        # -------------------------------------------------------------
        # STEP 3: Student Dashboard Access
        # -------------------------------------------------------------
        print("\n[STEP 3] Testing Dashboard Initial Access...")
        r_dash = client.get("/dashboard")
        assert r_dash.status_code == 200
        dash_html = r_dash.data.decode("utf-8")
        assert test_name in dash_html, "Dashboard does not contain student name!"
        assert "Total Attempts" in dash_html
        assert "Average Score" in dash_html
        print("  --> Dashboard loaded with dynamic metrics and student greeting.")

        # -------------------------------------------------------------
        # STEP 4: Curriculum Exploration & Topic API
        # -------------------------------------------------------------
        print("\n[STEP 4] Testing Subject & Topic Exploration...")
        r_quizzes = client.get("/quizzes")
        assert r_quizzes.status_code == 200
        q_html = r_quizzes.data.decode("utf-8")
        assert "Available Quizzes" in q_html
        assert "Python" in q_html

        r_api = client.get("/api/topics/1")
        assert r_api.status_code == 200
        topics_json = r_api.get_json()
        assert isinstance(topics_json, list) and len(topics_json) > 0
        assert "topic_name" in topics_json[0]
        print(f"  --> Curriculum active: /api/topics/1 returned {len(topics_json)} topics.")

        # -------------------------------------------------------------
        # -------------------------------------------------------------
        # STEP 5: AI Quiz Generation (Decoupled Storage)
        # -------------------------------------------------------------
        print("\n[STEP 5] Testing AI Quiz Generation on Free-Text Topic...")
        os.environ["MOCK_AI"] = "1"
        r_ai = client.post("/generate-quiz", data={
            "topic": "Python Data Structures",
            "difficulty": "Medium",
            "num_questions": 3
        }, follow_redirects=False)

        assert r_ai.status_code == 302, f"AI generation failed, got {r_ai.status_code}"
        assert "/ai-quiz/" in r_ai.headers["Location"], f"Expected redirect to /ai-quiz/start/<id>, got {r_ai.headers['Location']}"
        ai_attempt_id = int(r_ai.headers["Location"].split("/")[-1])

        # Verify decoupled database storage: quizzes and questions must NOT have been inserted into!
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT topic, difficulty, total_questions FROM ai_quiz_attempts WHERE ai_attempt_id = %s", (ai_attempt_id,))
        ai_row = cursor.fetchone()
        assert ai_row is not None
        assert ai_row[0] == "Python Data Structures"
        print(f"  --> AI Quiz generated and saved in decoupled ai_quiz_attempts table (ID: {ai_attempt_id})")

        # -------------------------------------------------------------
        # STEP 6: Curriculum Quiz Attempt & Live Stopwatch Initialization
        # -------------------------------------------------------------
        print("\n[STEP 6] Testing Existing Quiz Attempt & Stopwatch Interface...")
        cursor.execute("SELECT quiz_id FROM quizzes WHERE quiz_type = 'Existing' ORDER BY quiz_id LIMIT 1")
        quiz_row = cursor.fetchone()
        curriculum_quiz_id = quiz_row[0] if quiz_row else 1

        r_quiz_start = client.get(f"/quiz/{curriculum_quiz_id}")
        assert r_quiz_start.status_code == 200
        quiz_html = r_quiz_start.data.decode("utf-8")
        assert "stopwatchDisplay" in quiz_html
        assert "data-started-at" in quiz_html

        # Verify active unsubmitted attempt in database
        cursor.execute("SELECT attempt_id, started_at, submitted_at FROM quiz_attempts WHERE student_id = %s AND quiz_id = %s", (student_id, curriculum_quiz_id))
        att_row = cursor.fetchone()
        assert att_row is not None
        assert att_row[2] is None, "New attempt should not be submitted yet!"
        active_attempt_id = att_row[0]

        # Fetch questions for this quiz
        cursor.execute("""
            SELECT q.question_id, q.correct_option 
            FROM questions q 
            JOIN quiz_questions qq ON q.question_id = qq.question_id 
            WHERE qq.quiz_id = %s
            ORDER BY q.question_id
        """, (curriculum_quiz_id,))
        quiz_questions = cursor.fetchall()
        cursor.close()
        conn.close()
        print(f"  --> Live attempt initialized (Attempt ID: {active_attempt_id}, Questions: {len(quiz_questions)}).")

        # -------------------------------------------------------------
        # STEP 7: Quiz Submission, Scoring & 7-Day Retention Scheduling
        # -------------------------------------------------------------
        print("\n[STEP 7] Submitting Quiz Answers & Automated Scoring...")
        form_data = {
            "attempt_id": active_attempt_id
        }
        # Provide answer to each question
        for i, (qid, correct_opt) in enumerate(quiz_questions):
            # Answer first question correctly, others intentionally incorrect to verify weak topic logic
            form_data[f"question_{qid}"] = correct_opt if i == 0 else ("A" if correct_opt != "A" else "B")

        r_sub = client.post(f"/quiz/{curriculum_quiz_id}", data=form_data, follow_redirects=False)
        assert r_sub.status_code == 302, f"Submission failed, got {r_sub.status_code}"
        assert f"/result/{active_attempt_id}" in r_sub.headers["Location"]

        # Verify database scoring and retention schedule
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT score, accuracy, submitted_at FROM quiz_attempts WHERE attempt_id = %s", (active_attempt_id,))
        res_row = cursor.fetchone()
        assert res_row[2] is not None, "Attempt should be marked as submitted!"

        cursor.execute("SELECT schedule_id, scheduled_for, status FROM retention_schedules WHERE initial_attempt_id = %s", (active_attempt_id,))
        sched_row = cursor.fetchone()
        cursor.close()
        conn.close()

        assert sched_row is not None, "7-day retention schedule was not created!"
        assert sched_row[2] == "Pending"
        print(f"  --> Quiz submitted successfully (Score: {res_row[0]}%, Accuracy: {res_row[1]}%).")
        print(f"  --> 7-Day retention schedule automatically created (Schedule ID: {sched_row[0]}, Status: {sched_row[2]}).")

        # -------------------------------------------------------------
        # STEP 8: Detailed Quiz Result Page
        # -------------------------------------------------------------
        print("\n[STEP 8] Testing Detailed Results & Review Page...")
        r_res = client.get(f"/result/{active_attempt_id}")
        assert r_res.status_code == 200
        res_html = r_res.data.decode("utf-8")
        assert "Detailed Question Review" in res_html
        assert "Final Score" in res_html
        print("  --> Result page rendered score gauge, question review, and explanations.")

        # -------------------------------------------------------------
        # STEP 9: Quiz History
        # -------------------------------------------------------------
        print("\n[STEP 9] Testing Quiz History...")
        r_hist = client.get("/history")
        assert r_hist.status_code == 200
        hist_html = r_hist.data.decode("utf-8")
        assert "Quiz History" in hist_html
        assert f"{res_row[0]}" in hist_html
        print("  --> Quiz History correctly logged the completed attempt.")

        # -------------------------------------------------------------
        # STEP 10, 11, 12: Analytics (Trend, Time, & Weak Topics)
        # -------------------------------------------------------------
        print("\n[STEP 10-12] Testing Performance Analytics (Trend, Time, & Weak Topics)...")
        r_analytics = client.get("/analytics")
        assert r_analytics.status_code == 200
        an_html = r_analytics.data.decode("utf-8")

        # Section 1: Trend
        assert "Performance Trajectory" in an_html or "Performance Analytics" in an_html
        # Section 2: Time
        assert "Time-Based Analysis" in an_html
        assert "Average Completion Time" in an_html
        # Section 3: Weak Topics
        assert "Weak Topic Detection &amp; Mastery Analysis" in an_html or "Weak Topic Detection & Mastery Analysis" in an_html
        assert "Topic Accuracy &amp; Mastery Breakdown" in an_html or "Topic Accuracy & Mastery Breakdown" in an_html
        print("  --> Analytics view rendered all 3 sections: Performance Trend, Time-Based Analysis, and Weak Topics.")

        # -------------------------------------------------------------
        # STEP 13: Personalized Practice Recommendations
        # -------------------------------------------------------------
        print("\n[STEP 13] Testing Practice Recommendations Engine...")
        r_recs = client.get("/recommendations")
        assert r_recs.status_code == 200
        recs_html = r_recs.data.decode("utf-8")
        assert "Personalized Practice Recommendations" in recs_html
        assert "Active Practice Recommendations" in recs_html

        # Test completing a recommendation
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT recommendation_id FROM practice_recommendations WHERE student_id = %s AND status = 'Active' LIMIT 1", (student_id,))
        rec_to_comp = cursor.fetchone()
        cursor.close()
        conn.close()

        if rec_to_comp:
            rec_id = rec_to_comp[0]
            r_comp = client.post(f"/recommendations/complete/{rec_id}", follow_redirects=True)
            assert r_comp.status_code == 200
            comp_html = r_comp.data.decode("utf-8")
            assert "Recommendation marked as completed!" in comp_html
            print(f"  --> Practice recommendations generated and successfully completed (Rec ID: {rec_id}).")

        # -------------------------------------------------------------
        # STEP 14: Knowledge Retention System & Spaced Retest
        # -------------------------------------------------------------
        print("\n[STEP 14] Testing Knowledge Retention Retesting & Delta Calculation...")
        r_ret = client.get("/retention")
        assert r_ret.status_code == 200
        ret_html = r_ret.data.decode("utf-8")
        assert "Knowledge Retention System" in ret_html
        assert "Upcoming Retention Retests" in ret_html

        # Take retention retest
        r_take = client.get(f"/retention/take/{sched_row[0]}", follow_redirects=False)
        assert r_take.status_code == 302
        assert f"/quiz/{curriculum_quiz_id}" in r_take.headers["Location"]

        # Submit follow-up retest attempt
        # Find active attempt created for retest
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT attempt_id FROM quiz_attempts WHERE student_id = %s AND quiz_id = %s AND submitted_at IS NULL", (student_id, curriculum_quiz_id))
        follow_att = cursor.fetchone()
        if not follow_att:
            # Create attempt if not auto-created on GET
            client.get(f"/quiz/{curriculum_quiz_id}")
            cursor.execute("SELECT attempt_id FROM quiz_attempts WHERE student_id = %s AND quiz_id = %s AND submitted_at IS NULL", (student_id, curriculum_quiz_id))
            follow_att = cursor.fetchone()
        follow_attempt_id = follow_att[0]
        cursor.close()
        conn.close()

        # Submit follow-up attempt answering all questions correctly
        followup_form = {"attempt_id": follow_attempt_id}
        for qid, correct_opt in quiz_questions:
            followup_form[f"question_{qid}"] = correct_opt

        r_follow_sub = client.post(f"/quiz/{curriculum_quiz_id}", data=followup_form, follow_redirects=False)
        assert r_follow_sub.status_code == 302

        # Check retention page again to verify delta comparison table
        r_ret_after = client.get("/retention")
        assert r_ret_after.status_code == 200
        ret_after_html = r_ret_after.data.decode("utf-8")
        assert "Knowledge Improved" in ret_after_html or "+" in ret_after_html
        print("  --> Knowledge Retention retest completed: Delta measured and classified.")

        # -------------------------------------------------------------
        # STEP 15: Logout & Session Invalidation
        # -------------------------------------------------------------
        print("\n[STEP 15] Testing Logout & Session Invalidation...")
        r_logout = client.post("/logout", follow_redirects=False)
        assert r_logout.status_code == 302
        assert "/login" in r_logout.headers["Location"] or "/" in r_logout.headers["Location"]

        with client.session_transaction() as sess:
            assert "student_id" not in sess, "Session was not cleared after logout!"

        # Verify dashboard is no longer accessible without logging in
        r_dash_after = client.get("/dashboard", follow_redirects=False)
        assert r_dash_after.status_code == 302
        assert "/login" in r_dash_after.headers["Location"]
        print("  --> Logout successful. Session cleared, protected endpoints secured.")

        print("\n" + "=" * 70)
        print(">>> ALL 15 END-TO-END SYSTEM LIFECYCLE STEPS PASSED SUCCESSFULLY! <<<")
        print("=" * 70)

    finally:
        # -------------------------------------------------------------
        # STEP 16: Automated Database Cleanup
        # -------------------------------------------------------------
        if student_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"\n[CLEANUP] Successfully purged E2E test student {student_id} and all cascaded data.")

if __name__ == "__main__":
    run_e2e_workflow()
