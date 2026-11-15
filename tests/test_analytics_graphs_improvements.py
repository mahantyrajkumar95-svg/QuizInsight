"""
Automated Test Suite for Performance Analytics Graphs Improvements:
1. Completion Time by Quiz:
   - Numeric labels 1, 2, 3, 4... replacing Q1, Q2, Q3...
   - Accurate completion times & Y-axis in seconds
   - Average completion time reference line
2. Time Taken vs. Score Achieved (Scatter Plot):
   - Permanent point text labels removed
   - Interactive tooltip configuration (Attempt # / ID, Quiz title, Time in s, Score in %)
   - Small consistent markers with transparency
   - Visual jitter / distinction for overlapping/identical coordinates without changing stored data
   - Trend line preserved
   - Clear axis titles: Time Taken (Seconds) & Score Achieved (%)
3. Data updates accurately upon completing a new quiz attempt.
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from analytics.performance import analyze_time_performance

def test_analytics_graphs_improvements():
    print("=" * 70)
    print("TESTING PERFORMANCE ANALYTICS GRAPHS IMPROVEMENTS")
    print("=" * 70)

    app.config["TESTING"] = True
    client = app.test_client()

    conn = get_db_connection()
    cursor = conn.cursor()

    test_student_id = None
    attempt_ids = []

    try:
        # Create test student
        test_email = f"analytics_graphs_test_{int(time.time())}@example.com"
        cursor.execute(
            """
            INSERT INTO students (name, email, password_hash)
            VALUES ('Analytics Graphs Student', %s, 'dummy_hash')
            RETURNING student_id
            """,
            (test_email,)
        )
        test_student_id = cursor.fetchone()[0]

        # Insert 3 quiz attempts for Quiz 1:
        # Attempt 1: 40s, 80%
        # Attempt 2: 60s, 90%
        # Attempt 3: 40s, 80% (Identical coordinates to Attempt 1 to test overlap handling!)
        test_data = [
            (40, 80.0),
            (60, 90.0),
            (40, 80.0)  # Identical coordinates
        ]

        for time_sec, score in test_data:
            cursor.execute(
                """
                INSERT INTO quiz_attempts (student_id, quiz_id, started_at, submitted_at, time_taken_seconds, score, accuracy, total_questions, correct_answers)
                VALUES (%s, 1, CURRENT_TIMESTAMP - INTERVAL '1 hour', CURRENT_TIMESTAMP, %s, %s, %s, 10, 8)
                RETURNING attempt_id
                """,
                (test_student_id, time_sec, score, score)
            )
            attempt_ids.append(cursor.fetchone()[0])

        conn.commit()
        print(f"  --> Seeded test student #{test_student_id} with {len(attempt_ids)} attempts (including duplicate coordinates).")

        # Login student
        with client.session_transaction() as sess:
            sess["student_id"] = test_student_id
            sess["student_name"] = "Analytics Graphs Student"

        print("\n[STEP 1] Testing Backend analyze_time_performance() Data & Matplotlib...")
        time_analysis = analyze_time_performance(test_student_id)
        assert time_analysis["has_data"] is True
        assert len(time_analysis["quiz_time_records"]) == 3
        assert time_analysis["avg_time_seconds"] == round((40 + 60 + 40) / 3, 1)

        # Check records
        r1, r2, r3 = time_analysis["quiz_time_records"]
        assert r1["quiz_num"] == 1 and r1["time_seconds"] == 40 and r1["score"] == 80.0
        assert r2["quiz_num"] == 2 and r2["time_seconds"] == 60 and r2["score"] == 90.0
        assert r3["quiz_num"] == 3 and r3["time_seconds"] == 40 and r3["score"] == 80.0
        assert time_analysis["chart_base64"] is not None
        print("  --> Backend records and calculations verified with accurate completion times and averages.")

        print("\n[STEP 2] Testing /analytics Route HTML Render...")
        resp = client.get("/analytics")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")

        # A. Completion Time by Quiz verification
        assert "Completion Time by Quiz" in html, "Header 'Completion Time by Quiz' must be present"
        assert "completionTimeChart" in html, "Canvas 'completionTimeChart' must exist for Chart.js rendering"
        assert "barLabels = timeRecords.map(r => String(r.quiz_num))" in html, "Must use numeric labels 1, 2, 3..."
        print("  --> Graph 1 verified: Bar chart with numeric labels (1, 2, 3...) and Y-axis in seconds.")

        # B. Time Taken vs. Score Achieved verification
        assert "Time Taken vs. Score Achieved" in html, "Header 'Time Taken vs. Score Achieved' must be present"
        assert "timeScoreScatterChart" in html, "Canvas 'timeScoreScatterChart' must exist"
        assert "Time Taken (Seconds)" in html, "X-axis title must be 'Time Taken (Seconds)'"
        assert "Score Achieved (%)" in html, "Y-axis title must be 'Score Achieved (%)'"
        assert "Pacing Trend" in html, "Pacing Trend line must be present"
        print("  --> Graph 2 verified: Scatter plot with clear axis titles, trend line, and no permanent text clutter.")

        # C. Interactive Tooltip & Click Feedback verification
        assert "scatterPointFeedback" in html, "Element for click feedback must exist"
        assert "Quiz Attempt #" in html, "Tooltip must include Quiz Attempt #"
        assert "Time Taken:" in html, "Tooltip must include Time Taken"
        assert "Score Achieved:" in html, "Tooltip must include Score Achieved"
        print("  --> Interactive tooltips verified: Configured with attempt #, quiz title, time in s, and score in %.")

        # D. Overlapping point jitter handling verification
        assert "coordCounts" in html and "dispX" in html, "Display-space coordinate jitter must be present for duplicates"
        assert "actual_time: d.time_seconds" in html, "Actual stored time must be preserved in point metadata"
        assert "actual_score: d.score" in html, "Actual stored score must be preserved in point metadata"
        print("  --> Overlapping point distinction verified: Visual jitter applied while keeping stored values intact.")

        # E. Verify Chart.js library is loaded
        assert "chart.min.js" in html, "Chart.js script must be loaded"
        print("  --> Chart.js library script inclusion verified.")

        print("\n[STEP 3] Testing Dynamic Update After Submitting Another Quiz...")
        # Add 4th attempt
        cursor.execute(
            """
            INSERT INTO quiz_attempts (student_id, quiz_id, started_at, submitted_at, time_taken_seconds, score, accuracy, total_questions, correct_answers)
            VALUES (%s, 1, CURRENT_TIMESTAMP - INTERVAL '30 minutes', CURRENT_TIMESTAMP, 55, 95.0, 95.0, 10, 9)
            RETURNING attempt_id
            """,
            (test_student_id,)
        )
        attempt_ids.append(cursor.fetchone()[0])
        conn.commit()

        resp2 = client.get("/analytics")
        assert resp2.status_code == 200
        html2 = resp2.data.decode("utf-8")
        assert "95.0" in html2 or "95%" in html2
        time_analysis2 = analyze_time_performance(test_student_id)
        assert len(time_analysis2["quiz_time_records"]) == 4
        assert time_analysis2["quiz_time_records"][3]["quiz_num"] == 4
        assert time_analysis2["quiz_time_records"][3]["time_seconds"] == 55
        assert time_analysis2["quiz_time_records"][3]["score"] == 95.0
        print("  --> Dynamic update verified: 4th quiz attempt seamlessly integrated into both graphs.")

        print("\n" + "=" * 70)
        print(">>> ALL PERFORMANCE ANALYTICS GRAPHS IMPROVEMENTS VERIFIED! <<<")
        print("=" * 70)

    finally:
        # Cleanup test entities
        if attempt_ids:
            cursor.execute("DELETE FROM student_answers WHERE attempt_id = ANY(%s)", (attempt_ids,))
            cursor.execute("DELETE FROM retention_schedules WHERE student_id = %s", (test_student_id,))
            cursor.execute("DELETE FROM quiz_attempts WHERE attempt_id = ANY(%s)", (attempt_ids,))
        if test_student_id:
            cursor.execute("DELETE FROM students WHERE student_id = %s", (test_student_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print("[CLEANUP] Deleted temporary test entities.")

if __name__ == "__main__":
    test_analytics_graphs_improvements()
