"""
Validation Suite for Student Dashboard Simplification:
- Curated Subjects as main browsing section
- Removal of Available Quizzes and Retention Quizzes from dashboard
- Dynamic subject, topic, and quiz count updates from PostgreSQL
- Explore button behavior leading to subject-filtered Existing Quiz page
- Preservation of Welcome banner, 4 stats cards, Recent Attempts, Analytics shortcut, and sidebar
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection

def test_dashboard_curated_subjects():
    print("=" * 70)
    print("TESTING STUDENT DASHBOARD SIMPLIFICATION - CURATED SUBJECTS ONLY")
    print("=" * 70)

    app.config["TESTING"] = True
    client = app.test_client()

    conn = get_db_connection()
    cursor = conn.cursor()

    test_student_id = None
    test_subject_id = None
    test_topic_id = None
    test_quiz_id = None
    test_question_id = None

    try:
        # Create test student
        test_email = f"curated_dash_{int(time.time())}@example.com"
        cursor.execute(
            """
            INSERT INTO students (name, email, password_hash)
            VALUES ('Curated Dash Student', %s, 'dummy_hash')
            RETURNING student_id
            """,
            (test_email,)
        )
        test_student_id = cursor.fetchone()[0]
        conn.commit()

        # Login student
        with client.session_transaction() as sess:
            sess["student_id"] = test_student_id
            sess["student_name"] = "Curated Dash Student"

        print("\n[STEP 1] Testing Dashboard Initial Render & Removals...")
        r_dash = client.get("/dashboard")
        assert r_dash.status_code == 200
        html = r_dash.data.decode("utf-8")

        # A. Verify Available Quizzes is REMOVED from dashboard
        assert '<i class="bi bi-card-checklist text-primary me-2"></i>Available Quizzes' not in html, \
            "Available Quizzes header should be removed from dashboard"
        assert 'View All <i class="bi bi-arrow-right ms-1"></i>' not in html, \
            "View All button for Available Quizzes should be removed from dashboard"
        print("  --> PASSED: Available Quizzes section and View All button successfully removed from dashboard.")

        # B. Verify Retention Quizzes is REMOVED from dashboard
        assert '<i class="bi bi-arrow-repeat text-indigo me-2"></i>Retention Quizzes' not in html, \
            "Retention Quizzes section should be removed from dashboard"
        assert "Attempt Retention Quiz" not in html, \
            "Attempt Retention Quiz buttons should be removed from dashboard"
        print("  --> PASSED: Retention Quizzes section and attempt buttons successfully removed from dashboard.")

        # C. Verify Curated Subjects is the main quiz-browsing section
        assert "Curated Subjects" in html, "Curated Subjects section must be present on dashboard"
        assert "Python" in html, "Existing subject 'Python' must appear"
        assert "Mathematics" in html, "Existing subject 'Mathematics' must appear"
        assert "Explore" in html, "Explore button must be present on subject cards"
        print("  --> PASSED: Curated Subjects is active with dynamic subjects and Explore buttons.")

        # D. Verify Preserved Dashboard Elements
        assert "Hello, Curated Dash Student!" in html, "Welcome banner must be preserved"
        assert "Total Attempts" in html, "Metric 1 Total Attempts must be preserved"
        assert "Average Score" in html, "Metric 2 Average Score must be preserved"
        assert "Latest Score" in html, "Metric 3 Latest Score must be preserved"
        assert "Overall Accuracy" in html, "Metric 4 Overall Accuracy must be preserved"
        assert "Recent Quiz Attempts" in html, "Recent Quiz Attempts card must be preserved"
        assert "Ready to Analyze Performance?" in html, "Performance Analytics shortcut must be preserved"
        assert "Go to Analytics" in html, "Analytics button must be preserved"
        assert 'href="/retention"' in html, "Knowledge Retention sidebar navigation link must remain accessible"
        print("  --> PASSED: Welcome banner, statistics cards, recent attempts, analytics prompt, and sidebar preserved.")

        # E. Test Explore button navigation
        print("\n[STEP 2] Testing Explore Button Functionality...")
        # Get Python's subject_id
        cursor.execute("SELECT subject_id FROM subjects WHERE subject_name = 'Python'")
        python_subj_id = cursor.fetchone()[0]

        r_explore = client.get(f"/quizzes?subject_id={python_subj_id}")
        assert r_explore.status_code == 200
        explore_html = r_explore.data.decode("utf-8")
        # Verify subject is selected and topics for Python are loaded
        assert f'value="{python_subj_id}" selected' in explore_html
        assert "Python Basics" in explore_html or "Variables and Data Types" in explore_html
        assert "Start Quiz" in explore_html
        print(f"  --> PASSED: Explore button successfully opens /quizzes?subject_id={python_subj_id} with topics and quizzes ready.")

        # F. Test Dynamic Updates on PostgreSQL Additions
        print("\n[STEP 3] Testing Dynamic Subject, Topic, and Quiz Count Updates...")
        # 1. Add new subject to PostgreSQL
        unique_suffix = int(time.time()) % 10000
        new_subj_name = f"Cloud Architecture {unique_suffix}"
        cursor.execute(
            "INSERT INTO subjects (subject_name) VALUES (%s) RETURNING subject_id",
            (new_subj_name,)
        )
        test_subject_id = cursor.fetchone()[0]
        conn.commit()

        # Reload dashboard -> new subject must appear automatically with 0 topics & 0 quizzes
        r_dash2 = client.get("/dashboard")
        html2 = r_dash2.data.decode("utf-8")
        assert new_subj_name in html2, f"Newly added subject '{new_subj_name}' must appear in Curated Subjects"
        assert f"0</strong> Topics" in html2
        assert f"0</strong> Available Quizzes" in html2
        print(f"  --> PASSED: New subject '{new_subj_name}' automatically appeared with 0 Topics & 0 Quizzes.")

        # 2. Add topic under this new subject
        new_topic_name = f"Serverless Functions {unique_suffix}"
        cursor.execute(
            "INSERT INTO topics (subject_id, topic_name) VALUES (%s, %s) RETURNING topic_id",
            (test_subject_id, new_topic_name)
        )
        test_topic_id = cursor.fetchone()[0]
        conn.commit()

        # Reload dashboard -> topic count updates to 1
        r_dash3 = client.get("/dashboard")
        html3 = r_dash3.data.decode("utf-8")
        assert f"1</strong> Topics" in html3
        print(f"  --> PASSED: Adding topic dynamically updated count to 1 Topic.")

        # 3. Add quiz with a question under this subject
        cursor.execute(
            """
            INSERT INTO quizzes (subject_id, topic_id, quiz_title, difficulty, quiz_type)
            VALUES (%s, %s, 'Serverless Fundamentals Quiz', 'Easy', 'Existing')
            RETURNING quiz_id
            """,
            (test_subject_id, test_topic_id)
        )
        test_quiz_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, difficulty)
            VALUES (%s, 'What is serverless?', 'No servers managed', 'No code', 'No database', 'No network', 'A', 'Easy')
            RETURNING question_id
            """,
            (test_topic_id,)
        )
        test_question_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO quiz_questions (quiz_id, question_id) VALUES (%s, %s)",
            (test_quiz_id, test_question_id)
        )
        conn.commit()

        # Reload dashboard -> quiz count updates to 1 Available Quiz
        r_dash4 = client.get("/dashboard")
        html4 = r_dash4.data.decode("utf-8")
        assert f"1</strong> Available Quizzes" in html4
        print(f"  --> PASSED: Adding quiz dynamically updated count to 1 Available Quiz.")

        # 4. Click Explore on this new subject
        r_explore_new = client.get(f"/quizzes?subject_id={test_subject_id}")
        assert r_explore_new.status_code == 200
        exp_new_html = r_explore_new.data.decode("utf-8")
        assert new_subj_name in exp_new_html
        assert new_topic_name in exp_new_html
        assert "Serverless Fundamentals Quiz" in exp_new_html
        print(f"  --> PASSED: Explore button on new subject opens Existing Quiz page with new topic & quiz ready.")

        print("\n" + "=" * 70)
        print(">>> ALL DASHBOARD SIMPLIFICATION REQUIREMENTS VERIFIED! <<<")
        print("=" * 70)

    finally:
        # Cleanup test entities
        if test_quiz_id and test_question_id:
            cursor.execute("DELETE FROM quiz_questions WHERE quiz_id = %s", (test_quiz_id,))
            cursor.execute("DELETE FROM questions WHERE question_id = %s", (test_question_id,))
            cursor.execute("DELETE FROM quizzes WHERE quiz_id = %s", (test_quiz_id,))
        if test_topic_id:
            cursor.execute("DELETE FROM topics WHERE topic_id = %s", (test_topic_id,))
        if test_subject_id:
            cursor.execute("DELETE FROM subjects WHERE subject_id = %s", (test_subject_id,))
        if test_student_id:
            cursor.execute("DELETE FROM students WHERE student_id = %s", (test_student_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print("[CLEANUP] Deleted test entities.")

if __name__ == "__main__":
    test_dashboard_curated_subjects()
