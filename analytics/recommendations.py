"""
Analytics Module - Personalized Practice Recommendations Engine
Analyzes weak topics and performance gaps to generate tailored recommendations,
assign priority levels (High, Medium, Low), and link matching practice quizzes.
Persists recommendations to the PostgreSQL practice_recommendations table.
"""

from config import get_db_connection
from analytics.performance import analyze_weak_topics


def get_or_generate_recommendations(student_id):
    """
    Evaluates student performance using weak topic detection and synchronizes
    personalized recommendations with the PostgreSQL database.
    Returns:
        dict containing:
        - total_recommendations: int
        - high_priority_count: int
        - medium_priority_count: int
        - low_priority_count: int
        - active_recommendations: list of dicts
        - completed_recommendations: list of dicts
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check whether the currently logged-in student has attempted at least one quiz
        cursor.execute(
            """
            SELECT 
                (SELECT COUNT(*) FROM quiz_attempts WHERE student_id = %s AND submitted_at IS NOT NULL) +
                (SELECT COUNT(*) FROM ai_quiz_attempts WHERE student_id = %s AND submitted_at IS NOT NULL)
            """,
            (student_id, student_id)
        )
        attempt_count = cursor.fetchone()[0]

        # Case 1: Newly registered student with zero quiz attempts
        if attempt_count == 0:
            return {
                "has_attempts": False,
                "total_attempts": 0,
                "total_recommendations": 0,
                "high_priority_count": 0,
                "medium_priority_count": 0,
                "low_priority_count": 0,
                "active_recommendations": [],
                "completed_recommendations": [],
                "empty_message": "No practice recommendations available yet. Attempt your first quiz to receive personalized practice recommendations based on your performance."
            }

        # Case 2: Student with Quiz Attempts
        # Clean up any legacy starter/foundational records so only real performance recommendations remain
        cursor.execute(
            """
            DELETE FROM practice_recommendations
            WHERE student_id = %s AND reason LIKE 'Foundational Topic%%'
            """,
            (student_id,)
        )

        # 1. Fetch current topic analysis
        weak_data = analyze_weak_topics(student_id)

        if weak_data["has_data"] and weak_data["all_topics"]:
            for topic in weak_data["all_topics"]:
                topic_id = topic["topic_id"]
                acc = topic["accuracy"]
                topic_name = topic["topic_name"]
                correct = topic["correct_answers"]
                total = topic["total_questions"]

                # Find a matching existing practice quiz for this topic if available
                cursor.execute(
                    """
                    SELECT quiz_id FROM quizzes 
                    WHERE topic_id = %s AND quiz_type = 'Existing'
                    ORDER BY quiz_id ASC LIMIT 1
                    """,
                    (topic_id,)
                )
                q_row = cursor.fetchone()
                matching_quiz_id = q_row[0] if q_row else None

                if acc >= 80.0:
                    # Topic has reached mastery: mark any active recommendation as completed
                    cursor.execute(
                        """
                        UPDATE practice_recommendations
                        SET status = 'Completed'
                        WHERE student_id = %s AND topic_id = %s AND status = 'Active'
                        """,
                        (student_id, topic_id)
                    )
                else:
                    if acc < 40.0:
                        priority = "High"
                        reason = (
                            f"Critical Knowledge Gap: Accuracy is {acc}% ({correct}/{total} correct). "
                            f"Targeted review of core {topic_name} concepts is urgently advised."
                        )
                    elif acc < 60.0:
                        priority = "Medium"
                        reason = (
                            f"Concept Reinforcement: Accuracy is {acc}% ({correct}/{total} correct). "
                            f"Practicing {topic_name} exercises will strengthen problem solving."
                        )
                    else:
                        priority = "Low"
                        reason = (
                            f"Mastery Refinement: Solid foundation at {acc}% ({correct}/{total} correct). "
                            f"Further practice on {topic_name} will push your score to full mastery."
                        )

                    # Check if an active recommendation already exists
                    cursor.execute(
                        """
                        SELECT recommendation_id FROM practice_recommendations
                        WHERE student_id = %s AND topic_id = %s AND status = 'Active'
                        """,
                        (student_id, topic_id)
                    )
                    existing_rec = cursor.fetchone()

                    if existing_rec:
                        cursor.execute(
                            """
                            UPDATE practice_recommendations
                            SET priority = %s, reason = %s, quiz_id = %s
                            WHERE recommendation_id = %s
                            """,
                            (priority, reason, matching_quiz_id, existing_rec[0])
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO practice_recommendations
                            (student_id, topic_id, quiz_id, reason, priority, status)
                            VALUES (%s, %s, %s, %s, %s, 'Active')
                            """,
                            (student_id, topic_id, matching_quiz_id, reason, priority)
                        )

        conn.commit()

        # 2. Fetch all recommendations for the student
        cursor.execute(
            """
            SELECT 
                pr.recommendation_id,
                pr.student_id,
                pr.topic_id,
                t.topic_name,
                s.subject_id,
                s.subject_name,
                pr.quiz_id,
                q.quiz_title,
                pr.reason,
                pr.priority,
                pr.status,
                pr.created_at
            FROM practice_recommendations pr
            JOIN topics t ON pr.topic_id = t.topic_id
            JOIN subjects s ON t.subject_id = s.subject_id
            LEFT JOIN quizzes q ON pr.quiz_id = q.quiz_id
            WHERE pr.student_id = %s
            ORDER BY 
                CASE pr.status WHEN 'Active' THEN 1 ELSE 2 END,
                CASE pr.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END,
                pr.created_at DESC
            """,
            (student_id,)
        )
        rows = cursor.fetchall()

        active_recs = []
        completed_recs = []

        for r in rows:
            item = {
                "recommendation_id": r[0],
                "student_id": r[1],
                "topic_id": r[2],
                "topic_name": r[3],
                "subject_id": r[4],
                "subject_name": r[5],
                "quiz_id": r[6],
                "quiz_title": r[7],
                "reason": r[8],
                "priority": r[9],
                "status": r[10],
                "created_at": r[11],
                "badge_class": "danger" if r[9] == "High" else ("warning" if r[9] == "Medium" else "info")
            }
            if r[10] == "Active":
                active_recs.append(item)
            else:
                completed_recs.append(item)

        high_count = sum(1 for r in active_recs if r["priority"] == "High")
        med_count = sum(1 for r in active_recs if r["priority"] == "Medium")
        low_count = sum(1 for r in active_recs if r["priority"] == "Low")

        return {
            "has_attempts": True,
            "total_attempts": attempt_count,
            "total_recommendations": len(active_recs),
            "high_priority_count": high_count,
            "medium_priority_count": med_count,
            "low_priority_count": low_count,
            "active_recommendations": active_recs,
            "completed_recommendations": completed_recs,
            "empty_message": ""
        }
    finally:
        cursor.close()
        conn.close()


def complete_recommendation(recommendation_id, student_id):
    """
    Marks an active recommendation as Completed for a student.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE practice_recommendations
            SET status = 'Completed'
            WHERE recommendation_id = %s AND student_id = %s
            """,
            (recommendation_id, student_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()
