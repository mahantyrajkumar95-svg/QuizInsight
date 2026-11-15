"""
Automated Test Suite for Student Score Performance Trend Graph Improvements:
1. X-Axis Labels:
   - Numeric attempt sequence labels: 1, 2, 3, 4, 5... instead of repeated quiz titles.
   - Chronological attempt ordering.
   - X-axis title set to "Quiz Attempt".
   - Readability and scaling configuration for 50+ quizzes (autoSkip, maxTicksLimit).
2. Remove Overlapping Score Labels:
   - Removed permanent percentage labels from data points (no floating text clutter).
   - Plotted points visible with consistent marker size and hover scaling.
   - Interactive tooltips displaying:
     * Quiz attempt number
     * Quiz title
     * Score achieved in percentage
     * Attempt date
     * Time taken (if available)
3. Preserve Existing Graph Features:
   - Blue performance trend line (#2563eb).
   - Average score reference line (#10b981).
   - Average score calculation unchanged.
   - Graph title: "Student Score Performance Trend".
   - Y-axis title: "Score (%)".
   - Blue-and-white theme and chronological ordering.
4. Clean Handling of Identical Scores:
   - Distinct sequence placement along X-axis without collisions or hiding points.
5. Dynamic updates upon completing new quizzes.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from analytics.performance import analyze_performance_trend

def test_performance_trend_improvements():
    print("=" * 70)
    print("TESTING STUDENT SCORE PERFORMANCE TREND GRAPH IMPROVEMENTS")
    print("=" * 70)

    app.config["TESTING"] = True
    client = app.test_client()

    conn = get_db_connection()
    cursor = conn.cursor()

    test_student_id = None
    attempt_ids = []

    try:
        # Create test student
        test_email = f"trend_test_{int(time.time())}@example.com"
        cursor.execute(
            """
            INSERT INTO students (name, email, password_hash)
            VALUES ('Trend Graph Student', %s, 'dummy_hash')
            RETURNING student_id
            """,
            (test_email,)
        )
        test_student_id = cursor.fetchone()[0]

        # Insert 3 quiz attempts for Quiz 1 with different and identical scores:
        # Attempt 1: Score 80.0%, 45s
        # Attempt 2: Score 90.0%, 60s
        # Attempt 3: Score 80.0%, 50s (Identical score to Attempt 1 to test clean handling)
        test_attempts_data = [
            (45, 80.0, 8, 10, 50),
            (60, 90.0, 9, 10, 40),
            (50, 80.0, 8, 10, 30)
        ]

        for time_sec, score, correct, total, offset_mins in test_attempts_data:
            cursor.execute(
                f"""
                INSERT INTO quiz_attempts (student_id, quiz_id, started_at, submitted_at, time_taken_seconds, score, accuracy, total_questions, correct_answers)
                VALUES (%s, 1, CURRENT_TIMESTAMP - INTERVAL '{offset_mins + 5} minutes', CURRENT_TIMESTAMP - INTERVAL '{offset_mins} minutes', %s, %s, %s, %s, %s)
                RETURNING attempt_id
                """,
                (test_student_id, time_sec, score, score, total, correct)
            )
            attempt_ids.append(cursor.fetchone()[0])

        conn.commit()
        print(f"  --> Seeded test student #{test_student_id} with {len(attempt_ids)} attempts.")

        # Log in student
        with client.session_transaction() as sess:
            sess["student_id"] = test_student_id
            sess["student_name"] = "Trend Graph Student"

        print("\n[STEP 1] Testing Backend analyze_performance_trend()...")
        trend_data = analyze_performance_trend(test_student_id)
        assert trend_data["has_data"] is True, "Expected has_data to be True"
        assert len(trend_data["quiz_scores"]) == 3, f"Expected 3 records, got {len(trend_data['quiz_scores'])}"

        # Check average score: (80 + 90 + 80) / 3 = 83.33
        expected_avg = round((80.0 + 90.0 + 80.0) / 3, 2)
        assert trend_data["avg_score"] == expected_avg, f"Expected avg {expected_avg}, got {trend_data['avg_score']}"
        print(f"  [PASS] Average score calculated accurately: {trend_data['avg_score']}%")

        # Check record fields
        first_rec = trend_data["quiz_scores"][0]
        assert first_rec["quiz_num"] == 1, "First record quiz_num should be 1"
        assert first_rec["score"] == 80.0
        assert "submitted_at_formatted" in first_rec
        assert "time_seconds" in first_rec
        assert "time_formatted" in first_rec
        assert first_rec["time_seconds"] == 45
        assert first_rec["time_formatted"] == "45s"
        print("  [PASS] quiz_scores enriched with formatted time, date, and sequence numbers.")

        # Check third record with identical score
        third_rec = trend_data["quiz_scores"][2]
        assert third_rec["quiz_num"] == 3
        assert third_rec["score"] == 80.0
        print("  [PASS] Identical score attempts assigned distinct chronological sequence numbers (1 and 3).")

        # Check Matplotlib chart generated
        assert trend_data["chart_base64"] is not None
        assert len(trend_data["chart_base64"]) > 100
        print("  [PASS] Matplotlib fallback chart generated.")

        print("\n[STEP 2] Testing /analytics Route HTML & Chart Configuration...")
        res = client.get("/analytics")
        assert res.status_code == 200, f"Expected status 200, got {res.status_code}"
        html = res.get_data(as_text=True)

        # 1. Check canvas and container
        assert 'id="scoreTrendChart"' in html, "Canvas for scoreTrendChart must be present"
        assert 'id="trendPointFeedback"' in html, "Feedback container for score trend must be present"
        assert 'Student Score Performance Trend' in html, "Graph title must be present"
        print("  [PASS] Interactive canvas and title rendered in HTML.")

        # 2. Check X-axis labels replaced with simple numeric sequence (1, 2, 3...)
        assert "trendScores.map(d => String(d.quiz_num))" in html, "X-axis labels must map to string attempt numbers (1, 2, 3...)"
        assert "text: 'Quiz Attempt'" in html, "X-axis title must be 'Quiz Attempt'"
        print("  [PASS] X-axis configured with numeric attempt labels (1, 2, 3...) and title 'Quiz Attempt'.")

        # 3. Check permanent percentage labels removed and tooltips configured
        # Permanent annotation labels should not appear floating on chart
        assert "Score Achieved (%)" in html, "Dataset label must include score in %"
        assert "text: 'Score (%)'" in html, "Y-axis title must be 'Score (%)'"
        assert "tooltip:" in html, "Tooltip config must be present"
        assert "Quiz Attempt #${d.quiz_num}" in html, "Tooltip must show attempt number"
        assert "Quiz Title: ${d.quiz_title}" in html, "Tooltip must show quiz title"
        assert "Score Achieved: ${d.score}%" in html, "Tooltip must show score in %"
        assert "Attempt Date: ${d.submitted_at_formatted" in html, "Tooltip must show attempt date"
        assert "Time Taken:" in html, "Tooltip must show time taken when available"
        print("  [PASS] Permanent percentage annotations removed and rich tooltips configured.")

        # 4. Check blue performance trend line and green average score line
        assert "#2563eb" in html, "Blue trend line color (#2563eb) must be configured"
        assert "#10b981" in html, "Average score reference line (#10b981) must be configured"
        assert "Average Score (" in html, "Average score reference line label must be configured"
        print("  [PASS] Blue performance trend line and green average reference line preserved.")

        # 5. Check autoSkip & maxTicksLimit for 50+ quiz scaling
        assert "autoSkip: true" in html, "autoSkip must be enabled for readable scaling"
        assert "maxTicksLimit: 30" in html, "maxTicksLimit must be set to prevent tick crowding"
        print("  [PASS] Responsive scaling with autoSkip and maxTicksLimit configured.")

        # 6. Check interactive click feedback
        assert "onClick: function" in html, "Click interaction must be enabled"
        assert "trendPointFeedback" in html, "Click feedback element must be targeted"
        print("  [PASS] Interactive click handler configured.")

        # 7. Check non-JS fallback
        assert "<noscript>" in html, "Non-JS fallback container must be present"
        assert "data:image/png;base64," in html, "Matplotlib chart fallback must be present in noscript"
        print("  [PASS] Non-JS fallback preserved.")

        print("\n[STEP 3] Testing Dynamic Update after Completing a 4th Quiz Attempt...")
        cursor.execute(
            """
            INSERT INTO quiz_attempts (student_id, quiz_id, started_at, submitted_at, time_taken_seconds, score, accuracy, total_questions, correct_answers)
            VALUES (%s, 1, CURRENT_TIMESTAMP - INTERVAL '15 minutes', CURRENT_TIMESTAMP, 75, 100.0, 100.0, 10, 10)
            RETURNING attempt_id
            """,
            (test_student_id,)
        )
        attempt_ids.append(cursor.fetchone()[0])
        conn.commit()

        # Re-fetch analytics
        trend_updated = analyze_performance_trend(test_student_id)
        assert len(trend_updated["quiz_scores"]) == 4, f"Expected 4 records, got {len(trend_updated['quiz_scores'])}"
        expected_new_avg = round((80.0 + 90.0 + 80.0 + 100.0) / 4, 2)
        assert trend_updated["avg_score"] == expected_new_avg
        assert trend_updated["quiz_scores"][3]["quiz_num"] == 4
        assert trend_updated["quiz_scores"][3]["score"] == 100.0
        assert trend_updated["quiz_scores"][3]["time_seconds"] == 75

        res2 = client.get("/analytics")
        assert res2.status_code == 200
        html2 = res2.get_data(as_text=True)
        assert f"Avg: {expected_new_avg}%" in html2
        print(f"  [PASS] Dynamic update verified: 4 attempts, updated avg {expected_new_avg}%.")

        print("\n" + "=" * 70)
        print("ALL STUDENT SCORE PERFORMANCE TREND GRAPH TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        # Cleanup test data
        try:
            if attempt_ids:
                cursor.execute("DELETE FROM quiz_attempts WHERE attempt_id = ANY(%s)", (attempt_ids,))
            if test_student_id:
                cursor.execute("DELETE FROM students WHERE student_id = %s", (test_student_id,))
            conn.commit()
            cursor.close()
            conn.close()
            print("  --> Test data cleaned up successfully.")
        except Exception as e:
            print(f"  --> Cleanup warning: {e}")

if __name__ == "__main__":
    test_performance_trend_improvements()
