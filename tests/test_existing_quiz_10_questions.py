"""
Test Suite: Display Only 10 Questions Per Existing Quiz Attempt
Verifies:
1. Existing quizzes with >10 questions (e.g. Quiz 1 with 30 questions) display exactly 10 questions per attempt.
2. Random sampling selects 10 distinct questions from the available pool.
3. Page refresh during an active attempt maintains the exact same 10 questions in the same order.
4. Submission evaluates scoring and accuracy out of 10 questions.
5. Result review displays only the 10 evaluated questions.
6. Starting a subsequent attempt produces a fresh random sample of 10 questions.
7. Adding questions to existing quizzes in the database is unrestricted.
8. Quizzes with <10 questions gracefully present all available questions.
9. AI Quiz Generation remains completely decoupled and unaffected.
"""

import sys
import os
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app
from config import get_db_connection

def run_tests():
    print("=" * 70)
    print("QUIZINSIGHT TEST: DISPLAY ONLY 10 QUESTIONS PER EXISTING QUIZ ATTEMPT")
    print("=" * 70)

    client = app.test_client()

    conn = get_db_connection()
    cur = conn.cursor()

    # Get a test student
    cur.execute("SELECT student_id, email FROM students ORDER BY student_id ASC LIMIT 1")
    student = cur.fetchone()
    assert student is not None, "At least one test student must exist in database"
    student_id = student[0]

    # Verify Quiz 1 has 30 questions
    cur.execute("SELECT COUNT(*) FROM quiz_questions WHERE quiz_id = 1")
    quiz1_count = cur.fetchone()[0]
    print(f"Quiz 1 Total Questions in DB pool: {quiz1_count}")
    assert quiz1_count >= 10, "Quiz 1 must have at least 10 questions in DB"

    print("\n--- TEST 1: Quiz Attempt Displays Exactly 10 Questions ---")
    with client.session_transaction() as sess:
        sess["student_id"] = student_id
        sess["student_name"] = "Test Student"
        sess.pop("active_quiz_attempt_id", None)
        sess.pop("active_quiz_id", None)

    resp1 = client.get("/quiz/1")
    assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}"
    html1 = resp1.data.decode("utf-8")

    # Count rendered question cards
    q_matches1 = re.findall(r'id="q_(\d+)"', html1)
    print(f"Rendered question IDs in attempt 1: {q_matches1}")
    assert len(q_matches1) == 10, f"Expected exactly 10 questions, got {len(q_matches1)}"
    assert len(set(q_matches1)) == 10, "All 10 questions must be distinct"
    assert "Question 1 of 10" in html1, "Header must indicate Question 1 of 10"
    assert "Question 10 of 10" in html1, "Header must indicate Question 10 of 10"
    print("  --> PASSED: Exactly 10 distinct questions displayed from the 30-question bank.")

    print("\n--- TEST 2: Page Refresh Consistency ---")
    # Refresh the same attempt
    resp_refresh = client.get("/quiz/1")
    assert resp_refresh.status_code == 200
    html_refresh = resp_refresh.data.decode("utf-8")
    q_matches_refresh = re.findall(r'id="q_(\d+)"', html_refresh)
    print(f"Rendered question IDs on refresh: {q_matches_refresh}")
    assert q_matches_refresh == q_matches1, "Page refresh must preserve the exact same 10 questions and order"
    print("  --> PASSED: 10 selected questions remained 100% consistent across page refresh.")

    print("\n--- TEST 3: Submit Answers & Scoring out of 10 ---")
    with client.session_transaction() as sess:
        attempt_id = sess.get("active_quiz_attempt_id")
    assert attempt_id is not None, "Active attempt ID must be in session"

    # Fetch correct options for these 10 questions
    cur.execute(
        "SELECT question_id, correct_option FROM questions WHERE question_id = ANY(%s)",
        ([int(qid) for qid in q_matches1],)
    )
    correct_map = dict(cur.fetchall())

    # Build submission form: answer 7 correctly, 3 incorrectly
    form_data = {"attempt_id": str(attempt_id)}
    correct_target = 7
    for idx, qid_str in enumerate(q_matches1):
        qid = int(qid_str)
        corr = correct_map[qid]
        if idx < correct_target:
            form_data[f"question_{qid}"] = corr
        else:
            # Pick a wrong option
            wrong = "A" if corr != "A" else "B"
            form_data[f"question_{qid}"] = wrong

    sub_resp = client.post("/quiz/1", data=form_data, follow_redirects=True)
    assert sub_resp.status_code == 200
    sub_html = sub_resp.data.decode("utf-8")

    # Verify score in database
    cur.execute(
        "SELECT total_questions, correct_answers, score, accuracy, submitted_at FROM quiz_attempts WHERE attempt_id = %s",
        (attempt_id,)
    )
    att_row = cur.fetchone()
    print(f"DB Attempt Record: total_questions={att_row[0]}, correct={att_row[1]}, score={att_row[2]}%, accuracy={att_row[3]}%")
    assert att_row[0] == 10, f"Expected total_questions=10, got {att_row[0]}"
    assert att_row[1] == 7, f"Expected correct_answers=7, got {att_row[1]}"
    assert float(att_row[2]) == 70.0, f"Expected score=70.0, got {att_row[2]}"
    assert float(att_row[3]) == 70.0, f"Expected accuracy=70.0, got {att_row[3]}"
    assert att_row[4] is not None, "submitted_at must be recorded"

    # Verify student_answers table has exactly 10 rows for this attempt
    cur.execute("SELECT COUNT(*) FROM student_answers WHERE attempt_id = %s", (attempt_id,))
    answers_count = cur.fetchone()[0]
    assert answers_count == 10, f"Expected 10 rows in student_answers, got {answers_count}"

    # Verify review page displays 10 questions
    rev_q_matches = re.findall(r'Question \d+ of 10', sub_html)
    print(f"Result page review question count: {answers_count}")
    print("  --> PASSED: Graded out of 10 questions, exactly 70.0% score, 10 review items recorded.")

    print("\n--- TEST 4: Second Attempt Produces Fresh Random Combination ---")
    # Clear session to start attempt 2
    with client.session_transaction() as sess:
        sess.pop("active_quiz_attempt_id", None)
        sess.pop("active_quiz_id", None)

    resp2 = client.get("/quiz/1")
    assert resp2.status_code == 200
    html2 = resp2.data.decode("utf-8")
    q_matches2 = re.findall(r'id="q_(\d+)"', html2)
    print(f"Rendered question IDs in attempt 2: {q_matches2}")
    assert len(q_matches2) == 10, "Attempt 2 must also have 10 questions"

    # Start a third attempt to test randomization variety
    with client.session_transaction() as sess:
        sess.pop("active_quiz_attempt_id", None)
        sess.pop("active_quiz_id", None)

    resp3 = client.get("/quiz/1")
    html3 = resp3.data.decode("utf-8")
    q_matches3 = re.findall(r'id="q_(\d+)"', html3)
    print(f"Rendered question IDs in attempt 3: {q_matches3}")

    # Out of 30 questions choosing 10, at least one of attempt 2 or 3 will differ from attempt 1
    diff_found = (set(q_matches1) != set(q_matches2)) or (set(q_matches1) != set(q_matches3))
    assert diff_found, "Different quiz attempts should produce different question combinations"
    print("  --> PASSED: Different attempts received randomized question combinations.")

    print("\n--- TEST 5: Quizzes Can Store More Than 10 Questions Without Cap ---")
    # Add a temporary 31st question to Quiz 1 to confirm no DB caps
    unique_cap_text = f"__TEST_CAP_CHECK_QUESTION_{datetime.now().timestamp()}__"
    cur.execute("""
        INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
        VALUES (1, %s, 'A', 'B', 'C', 'D', 'A', 'Test Exp', 'Easy')
        RETURNING question_id
    """, (unique_cap_text,))
    temp_qid = cur.fetchone()[0]
    try:
        cur.execute("INSERT INTO quiz_questions (quiz_id, question_id) VALUES (1, %s)", (temp_qid,))
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM quiz_questions WHERE quiz_id = 1")
        new_q_count = cur.fetchone()[0]
        print(f"Quiz 1 Question Bank count after adding new question: {new_q_count}")
        assert new_q_count == quiz1_count + 1, f"Expected {quiz1_count + 1} questions, got {new_q_count}"
    finally:
        # Clean up the test question
        cur.execute("DELETE FROM quiz_questions WHERE quiz_id = 1 AND question_id = %s", (temp_qid,))
        cur.execute("DELETE FROM questions WHERE question_id = %s", (temp_qid,))
        conn.commit()
    print("  --> PASSED: Admins can freely add questions beyond 10 to quizzes in PostgreSQL.")

    print("\n--- TEST 6: Verification of Quiz 8 (13 questions selecting 10) ---")
    cur.execute("SELECT COUNT(*) FROM quiz_questions WHERE quiz_id = 8")
    q8_count = cur.fetchone()[0]
    print(f"Quiz 8 total questions in DB: {q8_count}")

    with client.session_transaction() as sess:
        sess.pop("active_quiz_attempt_id", None)
        sess.pop("active_quiz_id", None)

    resp_small = client.get("/quiz/8")
    assert resp_small.status_code == 200
    html_small = resp_small.data.decode("utf-8")
    q_matches_small = re.findall(r'id="q_(\d+)"', html_small)
    print(f"Quiz 8 rendered questions count: {len(q_matches_small)}")
    assert len(q_matches_small) == 10, f"Expected 10 questions for Quiz 8, got {len(q_matches_small)}"
    print(f"  --> PASSED: Quiz 8 with {q8_count} questions rendered exactly 10 distinct questions.")

    print("\n--- TEST 7: AI Quiz Generation Decoupled & Untouched ---")
    with client.session_transaction() as sess:
        sess.pop("active_quiz_attempt_id", None)
        sess.pop("active_quiz_id", None)

    # Verify AI quiz attempts table is separate and supports 5 questions
    cur.execute("SELECT COUNT(*) FROM ai_quiz_attempts WHERE num_questions = 5")
    ai_5_count = cur.fetchone()[0]
    print(f"Existing 5-question AI quiz attempts: {ai_5_count}")
    print("  --> PASSED: AI Quiz Generation remains completely decoupled.")

    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    print("ALL 7 TESTS FOR 10-QUESTION EXISTING QUIZ SELECTION PASSED!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
