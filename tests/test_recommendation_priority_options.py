"""
Automated Test Suite for Practice Options Based on Priority:
- High Priority (<40% accuracy): Both 'Practice with Existing Quiz' and 'Practice with AI Quiz' visible.
- Medium Priority (40-59% accuracy): Both 'Practice with Existing Quiz' and 'Practice with AI Quiz' visible.
- Low Priority (60-79% accuracy): Only 'Practice with AI Quiz' visible; Existing Quiz option is NOT displayed.
- Topic Pre-fill: Opening AI Quiz Generator with ?topic=TopicName correctly passes topic to topicInput.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from analytics.recommendations import get_or_generate_recommendations

def test_recommendation_priority_options():
    print("=" * 70)
    print("TESTING PRACTICE OPTIONS BASED ON RECOMMENDATION PRIORITY")
    print("=" * 70)

    app.config["TESTING"] = True
    client = app.test_client()

    conn = get_db_connection()
    cursor = conn.cursor()

    student_id = None
    attempt_ids = []

    try:
        # Create test student
        test_email = f"priority_test_{int(time.time())}@example.com"
        cursor.execute(
            """
            INSERT INTO students (name, email, password_hash)
            VALUES ('Priority Options Student', %s, 'dummy_hash')
            RETURNING student_id
            """,
            (test_email,)
        )
        student_id = cursor.fetchone()[0]

        # Fetch 3 distinct topics with matching existing quizzes in DB
        cursor.execute(
            """
            SELECT t.topic_id, t.topic_name, MIN(q.quiz_id) AS quiz_id
            FROM topics t
            JOIN quizzes q ON t.topic_id = q.topic_id AND q.quiz_type = 'Existing'
            WHERE t.topic_id IN (1, 8, 3)
            GROUP BY t.topic_id, t.topic_name
            """
        )
        t_dict = {r[0]: r for r in cursor.fetchall()}
        assert 1 in t_dict and 8 in t_dict and 3 in t_dict, "Need topics 1, 8, 3 with quizzes in DB"

        topic_high = t_dict[1]   # Topic 1 (Variables, Quiz 1) for High Priority (<40%)
        topic_med = t_dict[8]    # Topic 8 (Percentage, Quiz 11) for Medium Priority (40-59%)
        topic_low = t_dict[3]    # Topic 3 (Conditional Statements, Quiz 8) for Low Priority (60-79%)

        print(f"  --> Selected Topics:")
        print(f"      High Priority Topic (<40%): {topic_high[1]} (ID: {topic_high[0]}, Quiz: {topic_high[2]})")
        print(f"      Medium Priority Topic (40-59%): {topic_med[1]} (ID: {topic_med[0]}, Quiz: {topic_med[2]})")
        print(f"      Low Priority Topic (60-79%): {topic_low[1]} (ID: {topic_low[0]}, Quiz: {topic_low[2]})")

        # Create 1 quiz attempt for each topic with corresponding accuracy:
        # 1. High Priority: 1/5 correct = 20.0% accuracy (Topic 1 has 60 questions)
        # 2. Medium Priority: 1/2 correct = 50.0% accuracy (Topic 8 has 7 questions)
        # 3. Low Priority: 2/3 correct = 66.7% accuracy (Topic 3 has 3 questions)
        test_scenarios = [
            (topic_high[0], topic_high[2], 1, 5, 20.0),
            (topic_med[0], topic_med[2], 1, 2, 50.0),
            (topic_low[0], topic_low[2], 2, 3, 66.7)
        ]

        for topic_id, quiz_id, correct, total, acc in test_scenarios:
            cursor.execute(
                """
                INSERT INTO quiz_attempts (student_id, quiz_id, started_at, submitted_at, time_taken_seconds, score, accuracy, total_questions, correct_answers)
                VALUES (%s, %s, CURRENT_TIMESTAMP - INTERVAL '30 minutes', CURRENT_TIMESTAMP, 60, %s, %s, %s, %s)
                RETURNING attempt_id
                """,
                (student_id, quiz_id, acc, acc, total, correct)
            )
            att_id = cursor.fetchone()[0]
            attempt_ids.append(att_id)

            # Get distinct questions for this topic
            cursor.execute(
                "SELECT question_id FROM questions WHERE topic_id = %s LIMIT %s",
                (topic_id, total)
            )
            q_ids = [r[0] for r in cursor.fetchall()]
            assert len(q_ids) == total, f"Topic {topic_id} must have at least {total} distinct questions"

            # Insert student answers without duplicate question_id
            for i in range(total):
                qid = q_ids[i]
                is_corr = (i < correct)
                cursor.execute(
                    """
                    INSERT INTO student_answers (attempt_id, question_id, selected_option, is_correct)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (att_id, qid, 'A' if is_corr else 'B', is_corr)
                )

        conn.commit()
        print(f"  --> Seeded attempts and answers for student #{student_id}.")

        # -------------------------------------------------------------
        # STEP 1: Verify Backend Recommendation Generation & Priorities
        # -------------------------------------------------------------
        print("\n[STEP 1] Testing Backend Recommendations Generation...")
        rec_data = get_or_generate_recommendations(student_id)
        assert rec_data["has_attempts"] is True
        assert rec_data["total_recommendations"] >= 3

        recs_by_topic = {r["topic_id"]: r for r in rec_data["active_recommendations"]}
        assert topic_high[0] in recs_by_topic, f"Topic {topic_high[1]} should have a recommendation"
        assert recs_by_topic[topic_high[0]]["priority"] == "High", "Topic should be High Priority"

        assert topic_med[0] in recs_by_topic, f"Topic {topic_med[1]} should have a recommendation"
        assert recs_by_topic[topic_med[0]]["priority"] == "Medium", "Topic should be Medium Priority"

        assert topic_low[0] in recs_by_topic, f"Topic {topic_low[1]} should have a recommendation"
        assert recs_by_topic[topic_low[0]]["priority"] == "Low", "Topic should be Low Priority"

        print("  [PASS] All 3 priority levels successfully generated: High, Medium, and Low.")

        # -------------------------------------------------------------
        # STEP 2: Verify Frontend /recommendations Page
        # -------------------------------------------------------------
        print("\n[STEP 2] Testing /recommendations HTML for Practice Options by Priority...")
        with client.session_transaction() as sess:
            sess["student_id"] = student_id
            sess["student_name"] = "Priority Options Student"

        res = client.get("/recommendations")
        assert res.status_code == 200
        html = res.get_data(as_text=True)

        # Split HTML by cards or inspect cards
        card_blocks = html.split('<div class="rec-card rec-card-')
        # card_blocks[0] is preamble; subsequent items are cards
        high_card = None
        med_card = None
        low_card = None

        for block in card_blocks[1:]:
            if topic_high[1] in block and "high" in block[:20]:
                high_card = block
            elif topic_med[1] in block and "medium" in block[:20]:
                med_card = block
            elif topic_low[1] in block and "low" in block[:20]:
                low_card = block

        assert high_card is not None, "High Priority card must be rendered"
        assert med_card is not None, "Medium Priority card must be rendered"
        assert low_card is not None, "Low Priority card must be rendered"

        # 1. High Priority: Both options present
        assert "Practice with Existing Quiz" in high_card, "High Priority MUST display Practice with Existing Quiz"
        assert "Practice with AI Quiz" in high_card, "High Priority MUST display Practice with AI Quiz"
        assert f"/quiz/{topic_high[2]}" in high_card, "High Priority must link to existing quiz"
        assert f"/ai-quiz?topic={topic_high[1].replace(' ', '+')}" in high_card
        print("  [PASS] High Priority displays BOTH: 'Practice with Existing Quiz' and 'Practice with AI Quiz'.")

        # 2. Medium Priority: Both options present
        assert "Practice with Existing Quiz" in med_card, "Medium Priority MUST display Practice with Existing Quiz"
        assert "Practice with AI Quiz" in med_card, "Medium Priority MUST display Practice with AI Quiz"
        assert f"/quiz/{topic_med[2]}" in med_card, "Medium Priority must link to existing quiz"
        assert f"/ai-quiz?topic={topic_med[1].replace(' ', '+')}" in med_card
        print("  [PASS] Medium Priority displays BOTH: 'Practice with Existing Quiz' and 'Practice with AI Quiz'.")

        # 3. Low Priority: ONLY AI Quiz option present, Existing Quiz is NOT displayed
        assert "Practice with Existing Quiz" not in low_card, "Low Priority MUST NOT display Practice with Existing Quiz"
        assert "Practice with AI Quiz" in low_card, "Low Priority MUST display Practice with AI Quiz"
        assert f"/ai-quiz?topic={topic_low[1].replace(' ', '+')}" in low_card
        print("  [PASS] Low Priority displays ONLY: 'Practice with AI Quiz' (Existing Quiz is completely omitted).")

        # -------------------------------------------------------------
        # STEP 3: Verify AI Quiz Topic Pre-fill
        # -------------------------------------------------------------
        print("\n[STEP 3] Testing AI Quiz Topic Pre-fill via URL Parameter...")
        res_ai = client.get(f"/ai-quiz?topic={topic_low[1]}")
        assert res_ai.status_code == 200
        ai_html = res_ai.get_data(as_text=True)

        assert f'value="{topic_low[1]}"' in ai_html, f"Topic '{topic_low[1]}' must be prefilled in #topicInput value attribute"
        assert 'id="topicInput"' in ai_html
        assert 'setTopic(topicParam)' in ai_html
        print(f"  [PASS] AI Quiz Generator correctly pre-filled #topicInput with '{topic_low[1]}'.")

        print("\n" + "=" * 70)
        print("ALL PRACTICE OPTIONS PRIORITY TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        # Cleanup
        try:
            if attempt_ids:
                cursor.execute("DELETE FROM student_answers WHERE attempt_id = ANY(%s)", (attempt_ids,))
                cursor.execute("DELETE FROM quiz_attempts WHERE attempt_id = ANY(%s)", (attempt_ids,))
            if student_id:
                cursor.execute("DELETE FROM practice_recommendations WHERE student_id = %s", (student_id,))
                cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            conn.commit()
            cursor.close()
            conn.close()
            print("  --> Test data cleaned up successfully.")
        except Exception as e:
            print(f"  --> Cleanup warning: {e}")

if __name__ == "__main__":
    test_recommendation_priority_options()
