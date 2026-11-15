"""
Analytics Module - Knowledge Retention System
Tracks scheduled 7-day retention follow-up quizzes, evaluates performance differences
between initial and follow-up attempts, and calculates memory retention / decay rates.
"""

from datetime import datetime
from config import get_db_connection


def get_retention_analytics(student_id):
    """
    Fetches and computes knowledge retention analytics for a student.
    Returns:
        dict containing:
        - due_now: list of overdue or currently due retention quizzes
        - upcoming: list of future scheduled retention quizzes
        - completed: list of completed retention comparisons with deltas and status
        - due_now_count: int
        - upcoming_count: int
        - completed_count: int
        - retained_count: int
        - retention_rate: float or None
        - avg_delta: float
        - has_data: bool
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT 
                rs.schedule_id,
                rs.student_id,
                rs.initial_attempt_id,
                rs.quiz_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                rs.scheduled_for,
                rs.status,
                rs.followup_attempt_id,
                rs.created_at,
                init_qa.score AS initial_score,
                init_qa.accuracy AS initial_accuracy,
                init_qa.submitted_at AS initial_submitted_at,
                follow_qa.score AS followup_score,
                follow_qa.accuracy AS followup_accuracy,
                follow_qa.submitted_at AS followup_submitted_at
            FROM retention_schedules rs
            JOIN quizzes q ON rs.quiz_id = q.quiz_id
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            JOIN quiz_attempts init_qa ON rs.initial_attempt_id = init_qa.attempt_id
            LEFT JOIN quiz_attempts follow_qa ON rs.followup_attempt_id = follow_qa.attempt_id
            WHERE rs.student_id = %s
            ORDER BY 
                CASE rs.status WHEN 'Pending' THEN 1 ELSE 2 END,
                rs.scheduled_for ASC
            """,
            (student_id,)
        )
        rows = cursor.fetchall()

        now = datetime.now()
        due_now = []
        upcoming = []
        completed = []

        for r in rows:
            schedule_id = r[0]
            student_id = r[1]
            initial_attempt_id = r[2]
            quiz_id = r[3]
            quiz_title = r[4]
            subject_name = r[5]
            topic_name = r[6]
            scheduled_for = r[7]
            status = r[8]
            followup_attempt_id = r[9]
            created_at = r[10]
            initial_score = float(r[11]) if r[11] is not None else 0.0
            initial_accuracy = float(r[12]) if r[12] is not None else 0.0
            initial_submitted_at = r[13]
            followup_score = float(r[14]) if r[14] is not None else None
            followup_accuracy = float(r[15]) if r[15] is not None else None
            followup_submitted_at = r[16]

            item = {
                "schedule_id": schedule_id,
                "student_id": student_id,
                "initial_attempt_id": initial_attempt_id,
                "quiz_id": quiz_id,
                "quiz_title": quiz_title,
                "subject_name": subject_name,
                "topic_name": topic_name,
                "scheduled_for": scheduled_for,
                "status": status,
                "followup_attempt_id": followup_attempt_id,
                "created_at": created_at,
                "initial_score": initial_score,
                "initial_accuracy": initial_accuracy,
                "initial_submitted_at": initial_submitted_at,
                "followup_score": followup_score,
                "followup_accuracy": followup_accuracy,
                "followup_submitted_at": followup_submitted_at
            }

            if status == "Completed" and followup_attempt_id is not None:
                # Compute retention delta
                delta = round(followup_score - initial_score, 1)
                item["delta"] = delta
                item["delta_formatted"] = f"+{delta:.1f}%" if delta > 0 else f"{delta:.1f}%"

                # Classify retention status
                if delta > 0:
                    item["retention_status"] = "Knowledge Improved"
                    item["badge_class"] = "success"
                    item["icon"] = "bi-arrow-up-right"
                elif delta == 0:
                    item["retention_status"] = "Knowledge Retained"
                    item["badge_class"] = "primary"
                    item["icon"] = "bi-dash"
                elif delta >= -10.0:
                    item["retention_status"] = "Slight Decay"
                    item["badge_class"] = "warning text-dark"
                    item["icon"] = "bi-arrow-down-right"
                else:
                    item["retention_status"] = "Significant Decay"
                    item["badge_class"] = "danger"
                    item["icon"] = "bi-arrow-down"

                # Time between attempts
                if followup_submitted_at and initial_submitted_at:
                    diff = followup_submitted_at - initial_submitted_at
                    days = diff.days
                    if days > 0:
                        item["interval_formatted"] = f"{days} day{'s' if days > 1 else ''} later"
                    else:
                        hours = max(1, int(diff.total_seconds() // 3600))
                        item["interval_formatted"] = f"{hours} hour{'s' if hours > 1 else ''} later"
                else:
                    item["interval_formatted"] = "Same Day"

                completed.append(item)
            else:
                # Pending schedule: evaluate if due now or in future
                time_diff = scheduled_for - now
                if time_diff.total_seconds() <= 0:
                    item["is_due"] = True
                    item["due_label"] = "Due Now"
                    due_now.append(item)
                else:
                    item["is_due"] = False
                    days_left = time_diff.days
                    if days_left >= 1:
                        item["due_label"] = f"In {days_left} day{'s' if days_left > 1 else ''}"
                    else:
                        hours_left = max(1, int(time_diff.total_seconds() // 3600))
                        item["due_label"] = f"In {hours_left} hour{'s' if hours_left > 1 else ''}"
                    upcoming.append(item)

        completed_count = len(completed)
        retained_count = sum(1 for c in completed if c["delta"] >= 0)
        retention_rate = round((retained_count / completed_count) * 100, 1) if completed_count > 0 else None
        avg_delta = round(sum(c["delta"] for c in completed) / completed_count, 1) if completed_count > 0 else 0.0

        return {
            "due_now": due_now,
            "upcoming": upcoming,
            "completed": completed,
            "due_now_count": len(due_now),
            "upcoming_count": len(upcoming),
            "completed_count": completed_count,
            "retained_count": retained_count,
            "retention_rate": retention_rate,
            "avg_delta": avg_delta,
            "avg_delta_formatted": f"+{avg_delta:.1f}%" if avg_delta > 0 else f"{avg_delta:.1f}%",
            "has_data": (len(due_now) + len(upcoming) + len(completed)) > 0
        }

    finally:
        cursor.close()
        conn.close()
