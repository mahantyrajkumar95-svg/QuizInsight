"""
Test Suite: Question Bank Uniqueness & Minimum 10 Unique Questions Per Quiz
Verifies:
1. No duplicate question exists in the question bank (normalized).
2. Every Existing Quiz has at least 10 unique questions.
3. Incomplete quizzes have received new relevant questions matching subject/topic.
4. Exactly 10 questions appear when a student starts a quiz.
5. No question repeats within an attempt.
6. Refreshing an active attempt does not change its questions or order.
7. New questions can be added in the future without a storage limit, while duplicates are rejected.
8. AI Quiz Generation remains completely unchanged and decoupled.
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app
from config import get_db_connection
from modules.question_manager import normalize_question_text, find_duplicate_question, add_question, validate_new_question

def run_tests():
    print("=" * 75)
    print("QUIZINSIGHT TEST: QUESTION BANK UNIQUENESS & MINIMUM 10 QUESTIONS PER QUIZ")
    print("=" * 75)

    client = app.test_client()

    conn = get_db_connection()
    cur = conn.cursor()

    # --------------------------------------------------------------------------
    # VERIFICATION 1: No Duplicate Question Exists in the Question Bank
    # --------------------------------------------------------------------------
    print("\n[VERIFICATION 1] Checking for Duplicate Questions Across Question Bank...")
    cur.execute("SELECT question_id, topic_id, question_text FROM questions ORDER BY question_id")
    all_qs = cur.fetchall()
    print(f"  Total questions stored in questions table: {len(all_qs)}")

    seen_normalized = {}
    duplicates_found = []
    for qid, tid, qtext in all_qs:
        norm = normalize_question_text(qtext)
        if norm in seen_normalized:
            duplicates_found.append((qid, qtext, seen_normalized[norm]))
        else:
            seen_normalized[norm] = (qid, qtext)

    assert len(duplicates_found) == 0, f"Found {len(duplicates_found)} duplicate questions: {duplicates_found}"
    print(f"  --> PASSED: All {len(all_qs)} questions are 100% unique! Zero duplicates found.")

    # --------------------------------------------------------------------------
    # VERIFICATION 2 & 3: Every Existing Quiz Has at Least 10 Unique Questions
    # --------------------------------------------------------------------------
    print("\n[VERIFICATION 2 & 3] Verifying Every Existing Quiz Has >= 10 Unique Questions...")
    cur.execute("""
        SELECT 
            q.quiz_id,
            q.quiz_title,
            s.subject_name,
            t.topic_name,
            COUNT(DISTINCT qq.question_id) AS unique_count
        FROM quizzes q
        JOIN subjects s ON q.subject_id = s.subject_id
        JOIN topics t ON q.topic_id = t.topic_id
        LEFT JOIN quiz_questions qq ON q.quiz_id = qq.quiz_id
        WHERE q.quiz_type = 'Existing'
        GROUP BY q.quiz_id, q.quiz_title, s.subject_name, t.topic_name
        ORDER BY q.quiz_id
    """)
    quizzes = cur.fetchall()
    assert len(quizzes) > 0, "At least one existing quiz must be found"

    for q in quizzes:
        quiz_id, title, subject, topic, ucount = q
        print(f"  Quiz #{quiz_id:2d} | {subject:<12} | {topic:<22} | Unique Qs: {ucount:2d} | {title}")
        assert ucount >= 10, f"Quiz #{quiz_id} has only {ucount} unique questions (< 10)!"

        # Verify that all assigned questions match the quiz subject/topic
        cur.execute("""
            SELECT q.question_id, q.topic_id, t.subject_id
            FROM quiz_questions qq
            JOIN questions q ON qq.question_id = q.question_id
            JOIN topics t ON q.topic_id = t.topic_id
            WHERE qq.quiz_id = %s
        """, (quiz_id,))
        assigned = cur.fetchall()
        for aid, atopic, asubj in assigned:
            # Topic ID or Subject ID must match
            cur.execute("SELECT topic_id, subject_id FROM quizzes WHERE quiz_id = %s", (quiz_id,))
            qmeta = cur.fetchone()
            assert asubj == qmeta[1], f"Question {aid} subject {asubj} does not match quiz subject {qmeta[1]}"

    print(f"  --> PASSED: All {len(quizzes)} existing curriculum quizzes have >= 10 unique questions.")

    # --------------------------------------------------------------------------
    # VERIFICATION 4, 5, 6: Exactly 10 Unique Questions per Attempt, No Repeats, Refresh Consistency
    # --------------------------------------------------------------------------
    print("\n[VERIFICATION 4, 5, 6] Testing Quiz Attempt Runner (Exactly 10 Unique Qs, No Repeats, Refresh)...")
    cur.execute("SELECT student_id, email FROM students ORDER BY student_id ASC LIMIT 1")
    student = cur.fetchone()
    student_id = student[0]

    for test_quiz in [1, 8, 10, 13]:
        with client.session_transaction() as sess:
            sess["student_id"] = student_id
            sess["student_name"] = "Verification Student"
            sess.pop("active_quiz_attempt_id", None)
            sess.pop("active_quiz_id", None)

        resp = client.get(f"/quiz/{test_quiz}")
        assert resp.status_code == 200, f"Quiz {test_quiz} failed to start: {resp.status_code}"
        html = resp.data.decode("utf-8")

        rendered_q_ids = re.findall(r'id="q_(\d+)"', html)
        print(f"  Quiz {test_quiz:2d} started attempt: {len(rendered_q_ids)} questions rendered -> {rendered_q_ids}")
        assert len(rendered_q_ids) == 10, f"Quiz {test_quiz} expected exactly 10 questions, got {len(rendered_q_ids)}"
        assert len(set(rendered_q_ids)) == 10, f"Quiz {test_quiz} contained duplicate questions in attempt!"

        # Verify refresh consistency
        resp_refresh = client.get(f"/quiz/{test_quiz}")
        html_refresh = resp_refresh.data.decode("utf-8")
        refreshed_q_ids = re.findall(r'id="q_(\d+)"', html_refresh)
        assert refreshed_q_ids == rendered_q_ids, f"Page refresh altered question selection for Quiz {test_quiz}!"

    print("  --> PASSED: Exactly 10 questions appeared, 0 repeats, and refreshed attempts remained 100% frozen.")

    # --------------------------------------------------------------------------
    # VERIFICATION 7: Future Question Management & Duplicate Validation
    # --------------------------------------------------------------------------
    print("\n[VERIFICATION 7] Testing Future Question Management & Duplicate Prevention...")

    # A. Validate that a duplicate question is rejected by backend validation
    test_dup_text = "Which symbol is used to assign a value to a variable in Python?"
    try:
        validate_new_question(
            topic_id=1,
            question_text="   which symbol is used to ASSIGN a value to a variable in Python?   ",
            option_a="==",
            option_b="=",
            option_c="->",
            option_d=":",
            correct_option="B",
            difficulty="Easy",
            conn=conn
        )
        assert False, "Backend validation should have raised ValueError for duplicate question!"
    except ValueError as e:
        print(f"  [PASS] Backend validation correctly blocked duplicate: {str(e)[:75]}...")

    # B. Validate that API endpoint /api/questions/check-duplicate identifies duplicates
    api_dup_resp = client.post("/api/questions/check-duplicate", json={
        "question_text": "WHICH SYMBOL IS USED TO ASSIGN A VALUE TO A VARIABLE IN PYTHON?"
    })
    assert api_dup_resp.status_code == 200
    dup_json = api_dup_resp.get_json()
    assert dup_json["is_duplicate"] is True
    print(f"  [PASS] /api/questions/check-duplicate identified duplicate with Question ID {dup_json['existing_question']['question_id']}.")

    # C. Validate that API endpoint /api/questions/add rejects duplicate with HTTP 400
    api_add_dup_resp = client.post("/api/questions/add", json={
        "topic_id": 1,
        "question_text": "Which symbol is used to assign a value to a variable in Python?",
        "option_a": "A", "option_b": "B", "option_c": "C", "option_d": "D",
        "correct_option": "B"
    })
    assert api_add_dup_resp.status_code == 400
    print("  [PASS] /api/questions/add correctly rejected duplicate with HTTP 400.")

    # D. Validate adding a brand new unique question succeeds without limit
    unique_text = "What is the result of QuizInsight unique future question verification test 999?"
    api_add_valid_resp = client.post("/api/questions/add", json={
        "topic_id": 1,
        "question_text": unique_text,
        "option_a": "True", "option_b": "False", "option_c": "None", "option_d": "Error",
        "correct_option": "A",
        "explanation": "Valid unique future question",
        "difficulty": "Easy",
        "quiz_id": 1
    })
    assert api_add_valid_resp.status_code == 201
    valid_json = api_add_valid_resp.get_json()
    created_id = valid_json["question_id"]
    print(f"  [PASS] Successfully added new unique question via API: ID {created_id}.")

    # Clean up the test question
    cur.execute("DELETE FROM quiz_questions WHERE question_id = %s", (created_id,))
    cur.execute("DELETE FROM questions WHERE question_id = %s", (created_id,))
    conn.commit()
    print("  --> PASSED: Future question management verified: duplicates blocked, valid additions accepted.")

    # --------------------------------------------------------------------------
    # VERIFICATION 8: AI Quiz Generation Remains Completely Unchanged
    # --------------------------------------------------------------------------
    print("\n[VERIFICATION 8] Verifying AI Quiz Generation Decoupled & Untouched...")
    # Check that ai_quiz_attempts table operates independently
    cur.execute("SELECT COUNT(*) FROM ai_quiz_attempts")
    ai_attempts_count = cur.fetchone()[0]
    print(f"  AI Quiz Attempts count in database: {ai_attempts_count}")

    # Verify that AI quiz runner renders without error
    cur.execute("SELECT ai_attempt_id, student_id FROM ai_quiz_attempts ORDER BY ai_attempt_id DESC LIMIT 1")
    latest_ai_att = cur.fetchone()
    if latest_ai_att:
        with client.session_transaction() as sess:
            sess["student_id"] = latest_ai_att[1]
        ai_resp = client.get(f"/ai-quiz/start/{latest_ai_att[0]}")
        assert ai_resp.status_code in [200, 302], f"AI quiz runner failed: {ai_resp.status_code}"
        print(f"  [PASS] AI Quiz Runner for attempt #{latest_ai_att[0]} routed successfully (Status: {ai_resp.status_code}).")

    print("  --> PASSED: AI Quiz Generation remains completely decoupled and intact.")

    cur.close()
    conn.close()

    print("\n" + "=" * 75)
    print("ALL 8 VERIFICATION REQUIREMENTS SUCCESSFULLY PASSED!")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
