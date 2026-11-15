"""
====================================================================
QuizInsight – Verification Test Suite for New Architectural Changes:
  1. AI Quiz Generator (Decoupled Storage & Free-Text Topic)
  2. Existing Quiz Selection (4-Step Simplified Workflow without Difficulty)
  3. Preservation of all 16 Core Features
====================================================================
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app
from config import get_db_connection
from modules.ai_generator import generate_ai_questions, AIGenerationError

def test_all_modifications():
    print("=" * 70)
    print("STARTING QUIZINSIGHT MODIFICATIONS VALIDATION")
    print("=" * 70)

    # Enable mock AI mode for offline deterministic test execution
    os.environ["MOCK_AI"] = "1"
    app.config["TESTING"] = True
    client = app.test_client()

    timestamp = int(time.time())
    test_email = f"mod_student_{timestamp}@example.com"
    test_password = "ModPassword123!"
    test_name = f"Mod Student {timestamp}"

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # -----------------------------------------------------------------
        # TEST 1: Register and Log In
        # -----------------------------------------------------------------
        print("\n[TEST 1] Registering and authenticating student...")
        r_reg = client.post("/register", data={
            "name": test_name,
            "email": test_email,
            "password": test_password,
            "confirm_password": test_password
        }, follow_redirects=False)
        assert r_reg.status_code == 302, f"Expected 302, got {r_reg.status_code}"

        cur.execute("SELECT student_id FROM students WHERE email = %s", (test_email,))
        row = cur.fetchone()
        assert row is not None, "Student record not found in PostgreSQL"
        student_id = row[0]

        r_login = client.post("/login", data={
            "email": test_email,
            "password": test_password
        }, follow_redirects=False)
        assert r_login.status_code == 302
        print(f"  --> Student logged in successfully (student_id={student_id})")

        # -----------------------------------------------------------------
        # TEST 2: Existing Quiz Selection (4-Step, No Difficulty Filter)
        # -----------------------------------------------------------------
        print("\n[TEST 2] Verifying Existing Quiz Selection (4-step, no difficulty)...")
        r_selection = client.get("/quizzes")
        assert r_selection.status_code == 200
        html = r_selection.data.decode("utf-8")
        
        # Verify difficulty dropdown and filtering are removed
        assert "difficultySelect" not in html, "difficultySelect element should be removed from quiz selection"
        assert "Select Difficulty" not in html, "'Select Difficulty' should not be present in existing quiz selection"
        assert "Step 1" in html or "1</span> Select Subject" in html
        assert "Step 2" in html or "2</span> Select Topic" in html
        assert "Start Quiz" in html
        assert "Step 4: Start Quiz" not in html, "'Step 4:' should be removed from Start Quiz button"
        print("  --> Existing quiz page confirmed: 'Start Quiz' button simplified, difficulty removed.")

        # Test selecting Subject and Topic filters
        r_filter = client.get("/quizzes?subject_id=1&topic_id=1")
        assert r_filter.status_code == 200
        filter_html = r_filter.data.decode("utf-8")
        assert "Python" in filter_html
        print("  --> Subject and Topic filtering works properly.")

        # -----------------------------------------------------------------
        # TEST 3: AI Quiz Generator Module Unit Validation
        # -----------------------------------------------------------------
        print("\n[TEST 3] Testing AI Quiz Generator Unit Logic...")
        # Test free-text topic generation
        sample_topics = [
            "Machine Learning",
            "Operating Systems",
            "Computer Networks",
            "Database Management System",
            "Statistics"
        ]
        for top in sample_topics:
            qs, source = generate_ai_questions(top, difficulty="Hard", num_questions=4)
            assert len(qs) == 4, f"Expected 4 questions for {top}, got {len(qs)}"
            for q in qs:
                assert top in q["question_text"] or "In " in q["question_text"]
                assert q["option_a"] and q["option_b"] and q["option_c"] and q["option_d"]
                assert q["correct_option"] in ["A", "B", "C", "D"]
                assert q["explanation"]
                assert q["difficulty"] == "Hard"
            print(f"  --> Generated & validated 4 questions for '{top}' (Difficulty: Hard)")

        # Verify error handling for empty topic
        try:
            generate_ai_questions("", difficulty="Easy", num_questions=3)
            assert False, "Should raise AIGenerationError for empty topic"
        except AIGenerationError as e:
            assert "cannot be empty" in str(e).lower()
            print("  --> Proper AIGenerationError caught for empty topic.")

        # Verify error handling when no API key exists (disable mock temporarily)
        os.environ.pop("MOCK_AI", None)
        try:
            generate_ai_questions("Artificial Intelligence", difficulty="Medium", num_questions=3)
            assert False, "Should raise AIGenerationError when no API keys are configured"
        except AIGenerationError as e:
            assert "No AI API key found" in str(e)
            print("  --> Clear diagnostic error displayed when no API keys are configured.")
        # Restore mock mode for remaining test flow
        os.environ["MOCK_AI"] = "1"

        # -----------------------------------------------------------------
        # TEST 4: Decoupled Database Storage (Critical Requirement)
        # -----------------------------------------------------------------
        print("\n[TEST 4] Verifying Decoupled Database Storage (Zero Bank Contamination)...")
        # Count existing quizzes and questions before AI generation
        cur.execute("SELECT COUNT(*) FROM quizzes")
        quizzes_count_before = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM questions")
        questions_count_before = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM quiz_questions")
        quiz_questions_count_before = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM ai_quiz_attempts")
        ai_attempts_count_before = cur.fetchone()[0]

        # Student generates an AI quiz on a brand new free-text topic
        test_topic = "Quantum Computing Principles"
        r_gen = client.post("/generate-quiz", data={
            "topic": test_topic,
            "difficulty": "Hard",
            "num_questions": 3
        }, follow_redirects=False)

        assert r_gen.status_code == 302
        redirect_url = r_gen.headers["Location"]
        assert "/ai-quiz/start/" in redirect_url or "/ai-quiz/attempt/" in redirect_url
        ai_attempt_id = int(redirect_url.split("/")[-1])
        print(f"  --> AI Quiz generated, redirected to attempt #{ai_attempt_id}")

        # Check DB counts after AI generation
        cur.execute("SELECT COUNT(*) FROM quizzes")
        quizzes_count_after = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM questions")
        questions_count_after = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM quiz_questions")
        quiz_questions_count_after = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM ai_quiz_attempts")
        ai_attempts_count_after = cur.fetchone()[0]

        # ASSERT: Core quiz banks must have ZERO changes!
        assert quizzes_count_before == quizzes_count_after, "AI generation must NOT insert into quizzes table!"
        assert questions_count_before == questions_count_after, "AI generation must NOT insert into questions table!"
        assert quiz_questions_count_before == quiz_questions_count_after, "AI generation must NOT insert into quiz_questions table!"
        assert ai_attempts_count_after == ai_attempts_count_before + 1, "AI quiz attempt must be saved in ai_quiz_attempts table!"
        print("  --> PASSED: quizzes, questions, and quiz_questions are completely untouched! AI stored separately.")

        # Verify ai_quiz_attempts record structure
        cur.execute("""
            SELECT topic, difficulty, num_questions, total_questions, questions_data, student_answers, submitted_at
            FROM ai_quiz_attempts WHERE ai_attempt_id = %s
        """, (ai_attempt_id,))
        ai_row = cur.fetchone()
        assert ai_row[0] == test_topic
        assert ai_row[1] == "Hard"
        assert ai_row[2] == 3
        assert ai_row[3] == 3
        qs_snapshot = json.loads(ai_row[4]) if isinstance(ai_row[4], str) else ai_row[4]
        assert len(qs_snapshot) == 3
        assert ai_row[6] is None, "submitted_at must be NULL before submission"
        print("  --> ai_quiz_attempts record verified with complete question snapshot.")

        # -----------------------------------------------------------------
        # TEST 5: Attempting the AI Quiz with Elapsed Stopwatch
        # -----------------------------------------------------------------
        print("\n[TEST 5] Testing AI Quiz Runner & Stopwatch Display...")
        r_attempt = client.get(f"/ai-quiz/start/{ai_attempt_id}")
        assert r_attempt.status_code == 200
        attempt_html = r_attempt.data.decode("utf-8")
        assert "stopwatchDisplay" in attempt_html, "Stopwatch timer display element missing!"
        assert "data-started-at" in attempt_html, "Stopwatch start timestamp attribute missing!"
        assert test_topic in attempt_html, "Topic name missing from attempt page!"
        assert "Question 1 of 3" in attempt_html
        print("  --> AI Quiz runner rendered with visible count-up stopwatch timer and 3 questions.")

        # -----------------------------------------------------------------
        # TEST 6: Submitting the AI Quiz & Score Calculation
        # -----------------------------------------------------------------
        print("\n[TEST 6] Testing AI Quiz Submission & Scoring...")
        # Submit answers: answering A (correct for mock question 1 & 2), and B (incorrect for question 3)
        q1_id = qs_snapshot[0]["question_id"]
        q2_id = qs_snapshot[1]["question_id"]
        q3_id = qs_snapshot[2]["question_id"]

        r_sub = client.post(f"/ai-quiz/submit/{ai_attempt_id}", data={
            f"question_{q1_id}": "A",
            f"question_{q2_id}": "A",
            f"question_{q3_id}": "B"
        }, follow_redirects=False)

        assert r_sub.status_code == 302
        assert f"/ai-quiz/result/{ai_attempt_id}" in r_sub.headers["Location"]
        print(f"  --> AI Quiz submitted, redirected to result #{ai_attempt_id}")

        # Verify DB calculation
        cur.execute("""
            SELECT score, accuracy, correct_answers, total_questions, time_taken_seconds, submitted_at, student_answers
            FROM ai_quiz_attempts WHERE ai_attempt_id = %s
        """, (ai_attempt_id,))
        res_row = cur.fetchone()
        assert float(res_row[0]) == 66.67, f"Expected 66.67%, got {res_row[0]}"
        assert float(res_row[1]) == 66.67, f"Expected 66.67%, got {res_row[1]}"
        assert res_row[2] == 2, f"Expected 2 correct, got {res_row[2]}"
        assert res_row[3] == 3
        assert res_row[4] >= 0, "Time taken should be non-negative"
        assert res_row[5] is not None, "submitted_at should be recorded"
        ans_dict = json.loads(res_row[6]) if isinstance(res_row[6], str) else res_row[6]
        assert ans_dict[str(q1_id)]["is_correct"] is True
        assert ans_dict[str(q3_id)]["is_correct"] is False
        print("  --> Score, accuracy, time taken, and per-question diagnostic answers verified in PostgreSQL.")

        # -----------------------------------------------------------------
        # TEST 7: AI Quiz Result Review Page
        # -----------------------------------------------------------------
        print("\n[TEST 7] Testing AI Quiz Result Review Page...")
        r_res = client.get(f"/ai-quiz/result/{ai_attempt_id}")
        assert r_res.status_code == 200
        res_html = r_res.data.decode("utf-8")
        assert "66.67%" in res_html
        assert test_topic in res_html
        assert "Question Review &amp; Explanations" in res_html or "Question Review & Explanations" in res_html
        assert "Explanation &amp; Learning Rationale" in res_html or "Explanation & Learning Rationale" in res_html
        assert "CORRECT" in res_html
        assert "INCORRECT" in res_html
        print("  --> AI Result review page rendered with score, accuracy, questions, and explanations.")

        # -----------------------------------------------------------------
        # TEST 8: History Page with Separate Tabs
        # -----------------------------------------------------------------
        print("\n[TEST 8] Testing Quiz History Page with Separate AI and Existing Quizzes...")
        r_hist = client.get("/history")
        assert r_hist.status_code == 200
        hist_html = r_hist.data.decode("utf-8")
        assert "Existing Quizzes" in hist_html
        assert "AI-Generated Quizzes" in hist_html
        assert test_topic in hist_html
        assert f"/ai-quiz/result/{ai_attempt_id}" in hist_html
        print("  --> Quiz History page verified: contains separate AI quiz tab and links to result.")

        # -----------------------------------------------------------------
        # TEST 9: Existing Quiz Taking & Preservation of Existing Flow
        # -----------------------------------------------------------------
        print("\n[TEST 9] Testing Existing Quiz Attempt & Submission...")
        # Get an existing quiz id
        cur.execute("SELECT quiz_id FROM quizzes WHERE quiz_type = 'Existing' LIMIT 1")
        existing_quiz_id = cur.fetchone()[0]

        r_ex_start = client.get(f"/quiz/{existing_quiz_id}")
        assert r_ex_start.status_code == 200
        ex_html = r_ex_start.data.decode("utf-8")
        assert "stopwatchDisplay" in ex_html

        # Find existing attempt id
        cur.execute("""
            SELECT attempt_id FROM quiz_attempts
            WHERE student_id = %s AND quiz_id = %s AND submitted_at IS NULL
        """, (student_id, existing_quiz_id))
        ex_attempt_id = cur.fetchone()[0]

        # Get questions for existing quiz
        cur.execute("SELECT q.question_id, q.correct_option FROM questions q JOIN quiz_questions qq ON q.question_id = qq.question_id WHERE qq.quiz_id = %s", (existing_quiz_id,))
        ex_questions = cur.fetchall()

        submit_data = {"attempt_id": str(ex_attempt_id)}
        for eq in ex_questions:
            submit_data[f"question_{eq[0]}"] = eq[1]  # all correct

        r_ex_sub = client.post(f"/quiz/{existing_quiz_id}", data=submit_data, follow_redirects=False)
        assert r_ex_sub.status_code == 302
        assert f"/result/{ex_attempt_id}" in r_ex_sub.headers["Location"]
        print(f"  --> Existing quiz submitted successfully, redirected to /result/{ex_attempt_id}")

        # Check existing result review
        r_ex_res = client.get(f"/result/{ex_attempt_id}")
        assert r_ex_res.status_code == 200
        assert "100.0%" in r_ex_res.data.decode("utf-8")
        print("  --> Existing quiz result review rendered successfully.")

        # -----------------------------------------------------------------
        # TEST 10: Retention, Analytics, Recommendations Preservation
        # -----------------------------------------------------------------
        print("\n[TEST 10] Testing Retention, Analytics, and Recommendations...")
        r_dash = client.get("/dashboard")
        assert r_dash.status_code == 200

        r_ana = client.get("/analytics")
        assert r_ana.status_code == 200

        r_rec = client.get("/recommendations")
        assert r_rec.status_code == 200

        r_ret = client.get("/retention")
        assert r_ret.status_code == 200
        print("  --> Dashboard, Analytics, Recommendations, and Retention are all working seamlessly!")

        print("\n" + "=" * 70)
        print("ALL ARCHITECTURAL MODIFICATIONS & EXISTING FEATURES VERIFIED!")
        print("=" * 70)

    finally:
        # Cleanup test student
        if conn and not conn.closed:
            conn.rollback()
            if student_id:
                try:
                    cur.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
                    conn.commit()
                    print(f"\n[CLEANUP] Deleted test student ID {student_id}")
                except Exception as e:
                    print(f"\n[CLEANUP ERROR] {e}")
            cur.close()
            conn.close()

if __name__ == "__main__":
    test_all_modifications()
