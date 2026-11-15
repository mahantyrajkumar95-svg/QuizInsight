"""
Analytics Module - Performance Trend Analysis
Analyzes previous quiz scores using Python, Pandas, NumPy, and Matplotlib.
Classifies student performance as Improving, Declining, or Stable.
"""

import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import get_db_connection


def analyze_performance_trend(student_id):
    """
    Analyzes quiz scores over time for a given student using Pandas.
    Returns:
        dict containing:
        - avg_score: float
        - trend_status: 'Improving' | 'Declining' | 'Stable' | 'Baseline' | 'No Data'
        - improvement_delta: string (e.g. '+15.0%')
        - quiz_scores: list of dicts (quiz_num, quiz_title, score, submitted_at, vs_avg)
        - chart_base64: base64-encoded PNG chart or None
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT 
                qa.attempt_id,
                q.quiz_title,
                qa.score,
                qa.accuracy,
                qa.time_taken_seconds,
                qa.submitted_at
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.quiz_id
            WHERE qa.student_id = %s AND qa.submitted_at IS NOT NULL
            ORDER BY qa.submitted_at ASC, qa.attempt_id ASC
            """,
            (student_id,)
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not rows:
        return {
            "has_data": False,
            "avg_score": 0.0,
            "trend_status": "No Data",
            "improvement_delta": "N/A",
            "quiz_scores": [],
            "chart_base64": None
        }

    # Load into Pandas DataFrame
    df = pd.DataFrame(rows, columns=[
        "attempt_id", "quiz_title", "score", "accuracy", "time_taken", "submitted_at"
    ])
    df["score"] = df["score"].astype(float)
    df["quiz_num"] = range(1, len(df) + 1)

    avg_score = round(float(df["score"].mean()), 2)

    # Classify Performance Trend
    num_attempts = len(df)
    if num_attempts == 1:
        trend_status = "Baseline"
        improvement_delta = "Baseline (1 Quiz)"
    else:
        first_score = float(df["score"].iloc[0])
        last_score = float(df["score"].iloc[-1])
        delta = round(last_score - first_score, 2)
        improvement_delta = f"+{delta}%" if delta > 0 else f"{delta}%"

        # Fit linear trend line with NumPy
        x_vals = np.arange(num_attempts)
        y_vals = df["score"].values
        slope, _ = np.polyfit(x_vals, y_vals, 1)

        if slope > 1.0:
            trend_status = "Improving"
        elif slope < -1.0:
            trend_status = "Declining"
        else:
            trend_status = "Stable"

    # Build quiz score records with vs_avg indicator
    quiz_scores = []
    for _, row in df.iterrows():
        s = row["score"]
        vs_avg = "Above Average" if s > avg_score else ("Below Average" if s < avg_score else "Average")
        time_sec = int(row["time_taken"]) if pd.notnull(row["time_taken"]) else 0
        sub_at = row["submitted_at"]
        quiz_scores.append({
            "attempt_id": int(row["attempt_id"]),
            "quiz_num": int(row["quiz_num"]),
            "quiz_title": str(row["quiz_title"]),
            "score": round(s, 2),
            "submitted_at": sub_at,
            "submitted_at_formatted": sub_at.strftime('%d %b %Y, %I:%M %p') if sub_at else "Recent",
            "time_seconds": time_sec,
            "time_formatted": format_seconds(time_sec),
            "vs_avg": vs_avg
        })

    # Generate Performance Trend Chart via Matplotlib
    chart_base64 = None
    try:
        fig, ax = plt.subplots(figsize=(8, 4.2), dpi=100)
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#f8fafc')

        # Plot trend line and scatter points
        x = df["quiz_num"].values
        y = df["score"].values

        ax.plot(x, y, color="#2563eb", linewidth=2.5, marker='o', markersize=6,
                markerfacecolor="#3b82f6", markeredgecolor="#1d4ed8", markeredgewidth=1.5,
                label="Score (%)", zorder=3)

        # Plot average score reference line
        ax.axhline(avg_score, color="#10b981", linestyle="--", linewidth=1.5,
                   label=f"Average Score ({avg_score}%)", zorder=2)

        # Requirement: Remove permanent percentage labels from every data point to prevent overlapping
        # (ax.annotate removed)

        ax.set_title("Student Score Performance Trend", fontsize=13, fontweight='bold', color="#0f172a", pad=15)
        # Requirement: Keep the X-axis title as "Quiz Attempt"
        ax.set_xlabel("Quiz Attempt", fontsize=10, fontweight='bold', color="#475569")
        ax.set_ylabel("Score (%)", fontsize=10, fontweight='bold', color="#475569")
        ax.set_ylim(-5, 105)
        ax.set_xticks(x)
        # Requirement: Display 1, 2, 3, 4, 5, 6, 7... instead of repeated quiz names
        ax.set_xticklabels([str(i) for i in x], fontsize=9)

        # Ensure labels remain readable when students complete 50 or more quizzes
        if len(x) > 15:
            for i, tick in enumerate(ax.get_xticklabels()):
                if len(x) > 50 and i % 5 != 0:
                    tick.set_visible(False)
                elif len(x) > 25 and i % 2 != 0:
                    tick.set_visible(False)
                else:
                    tick.set_fontsize(8)

        ax.grid(True, linestyle=":", alpha=0.6, color="#cbd5e1", zorder=1)
        ax.legend(loc="lower right", frameon=True, facecolor="#ffffff", edgecolor="#e2e8f0", fontsize=9)

        # Despine
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color("#cbd5e1")
        ax.spines["bottom"].set_color("#cbd5e1")

        plt.tight_layout()

        # Save to buffer as PNG
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        plt.close(fig)
    except Exception as e:
        print("Error generating performance trend chart:", e)
        plt.close('all')

    return {
        "has_data": True,
        "avg_score": avg_score,
        "trend_status": trend_status,
        "improvement_delta": improvement_delta,
        "quiz_scores": quiz_scores,
        "chart_base64": chart_base64
    }


def format_seconds(seconds):
    """Formats an integer number of seconds into human-readable string."""
    if seconds is None:
        return "N/A"
    sec = int(seconds)
    if sec >= 60:
        m = sec // 60
        s = sec % 60
        return f"{m}m {s}s"
    return f"{sec}s"


def analyze_time_performance(student_id):
    """
    Analyzes quiz completion times using Python, Pandas, NumPy, and Matplotlib.
    Calculates total time, average completion time, fastest and slowest attempts,
    and generates a dual Time versus Score visualization.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT 
                qa.attempt_id,
                q.quiz_title,
                qa.time_taken_seconds,
                qa.score,
                qa.total_questions,
                qa.submitted_at
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.quiz_id
            WHERE qa.student_id = %s AND qa.submitted_at IS NOT NULL
            ORDER BY qa.submitted_at ASC, qa.attempt_id ASC
            """,
            (student_id,)
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not rows:
        return {
            "has_data": False,
            "total_time_seconds": 0,
            "total_time_formatted": "0s",
            "avg_time_seconds": 0.0,
            "avg_time_formatted": "0s",
            "fastest": None,
            "slowest": None,
            "quiz_time_records": [],
            "chart_base64": None
        }

    # Load into Pandas DataFrame
    df = pd.DataFrame(rows, columns=[
        "attempt_id", "quiz_title", "time_taken", "score", "total_questions", "submitted_at"
    ])
    df["time_taken"] = df["time_taken"].fillna(0).astype(int)
    df["score"] = df["score"].fillna(0).astype(float)
    df["total_questions"] = df["total_questions"].fillna(0).astype(int)
    df["quiz_num"] = range(1, len(df) + 1)

    total_time_seconds = int(df["time_taken"].sum())
    avg_time_seconds = round(float(df["time_taken"].mean()), 1)

    # Fastest and Slowest attempts
    min_idx = df["time_taken"].idxmin()
    max_idx = df["time_taken"].idxmax()

    fastest = {
        "quiz_title": str(df.loc[min_idx, "quiz_title"]),
        "time_seconds": int(df.loc[min_idx, "time_taken"]),
        "time_formatted": format_seconds(df.loc[min_idx, "time_taken"]),
        "score": float(df.loc[min_idx, "score"]),
        "date": df.loc[min_idx, "submitted_at"]
    }

    slowest = {
        "quiz_title": str(df.loc[max_idx, "quiz_title"]),
        "time_seconds": int(df.loc[max_idx, "time_taken"]),
        "time_formatted": format_seconds(df.loc[max_idx, "time_taken"]),
        "score": float(df.loc[max_idx, "score"]),
        "date": df.loc[max_idx, "submitted_at"]
    }

    # Record breakdown
    quiz_time_records = []
    for _, r in df.iterrows():
        total_q = int(r["total_questions"])
        time_sec = int(r["time_taken"])
        sec_per_q = round(time_sec / total_q, 1) if total_q > 0 else 0.0

        quiz_time_records.append({
            "attempt_id": int(r["attempt_id"]),
            "quiz_num": int(r["quiz_num"]),
            "quiz_title": str(r["quiz_title"]),
            "time_seconds": time_sec,
            "time_formatted": format_seconds(time_sec),
            "score": round(float(r["score"]), 1),
            "total_questions": total_q,
            "sec_per_question": sec_per_q,
            "submitted_at": r["submitted_at"]
        })

    # Generate Time vs. Score Matplotlib Chart
    chart_base64 = None
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=100)
        fig.patch.set_facecolor('#ffffff')

        # 1. Replace Q1, Q2, Q3, Q4... with simple numeric labels: 1, 2, 3, 4, 5, 6...
        labels = [str(i) for i in df["quiz_num"]]
        times = df["time_taken"].values
        scores = df["score"].values

        # Subplot 1: Completion Time by Quiz (Bar Chart)
        ax1.set_facecolor('#f8fafc')
        bars = ax1.bar(labels, times, color="#0ea5e9", edgecolor="#0284c7", width=0.55, zorder=3)
        ax1.axhline(avg_time_seconds, color="#f59e0b", linestyle="--", linewidth=1.5,
                    label=f"Avg: {format_seconds(avg_time_seconds)}", zorder=2)

        for bar in bars:
            height = bar.get_height()
            ax1.annotate(f"{int(height)}s",
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 4), textcoords="offset points",
                         ha='center', va='bottom', fontsize=8, fontweight='bold', color="#1e293b")

        ax1.set_title("Completion Time by Quiz", fontsize=11, fontweight='bold', color="#0f172a", pad=12)
        ax1.set_xlabel("Quiz Attempt", fontsize=9, fontweight='bold', color="#475569")
        ax1.set_ylabel("Time Taken (Seconds)", fontsize=9, fontweight='bold', color="#475569")
        ax1.grid(True, linestyle=":", alpha=0.5, color="#cbd5e1", zorder=1)
        ax1.legend(loc="upper right", fontsize=8, frameon=True, facecolor="#ffffff")

        # Spacing and readability for many attempts
        if len(labels) > 15:
            for i, tick in enumerate(ax1.get_xticklabels()):
                if len(labels) > 25 and i % 2 != 0:
                    tick.set_visible(False)
                else:
                    tick.set_fontsize(8)

        for spine in ["top", "right"]:
            ax1.spines[spine].set_visible(False)
        ax1.spines["left"].set_color("#cbd5e1")
        ax1.spines["bottom"].set_color("#cbd5e1")

        # Subplot 2: Time Taken vs. Score Achieved (Scatter Plot)
        ax2.set_facecolor('#f8fafc')

        # Slight display jitter for identical coordinates to distinguish multiple overlapping points
        coords = list(zip(times, scores))
        coord_counts = {}
        for c in coords:
            coord_counts[c] = coord_counts.get(c, 0) + 1

        seen_counts = {}
        plot_times = []
        plot_scores = []
        for t, s in coords:
            idx = seen_counts.get((t, s), 0)
            seen_counts[(t, s)] = idx + 1
            if coord_counts[(t, s)] > 1:
                angle = (2 * np.pi / coord_counts[(t, s)]) * idx
                plot_times.append(t + 0.4 * np.cos(angle))
                plot_scores.append(s + 0.4 * np.sin(angle))
            else:
                plot_times.append(t)
                plot_scores.append(s)

        scatter = ax2.scatter(plot_times, plot_scores, color="#8b5cf6", edgecolor="#6d28d9",
                              s=70, alpha=0.75, linewidths=1.2, zorder=3, label="Quiz Attempt")

        # Requirement: Remove permanent text labels from every data point to prevent overlapping

        # Add trend line if >= 2 points
        if len(times) >= 2:
            try:
                poly_slope, poly_intercept = np.polyfit(times, scores, 1)
                x_line = np.linspace(min(times), max(times), 50)
                y_line = poly_slope * x_line + poly_intercept
                ax2.plot(x_line, y_line, color="#ec4899", linestyle=":", linewidth=2, label="Pacing Trend", zorder=2)
                ax2.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#ffffff")
            except Exception:
                pass

        ax2.set_title("Time Taken vs. Score Achieved", fontsize=11, fontweight='bold', color="#0f172a", pad=12)
        ax2.set_xlabel("Time Taken (Seconds)", fontsize=9, fontweight='bold', color="#475569")
        ax2.set_ylabel("Score Achieved (%)", fontsize=9, fontweight='bold', color="#475569")
        ax2.set_ylim(-5, 110)
        ax2.grid(True, linestyle=":", alpha=0.5, color="#cbd5e1", zorder=1)

        for spine in ["top", "right"]:
            ax2.spines[spine].set_visible(False)
        ax2.spines["left"].set_color("#cbd5e1")
        ax2.spines["bottom"].set_color("#cbd5e1")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        plt.close(fig)
    except Exception as e:
        print("Error generating time analysis chart:", e)
        plt.close('all')

    return {
        "has_data": True,
        "total_time_seconds": total_time_seconds,
        "total_time_formatted": format_seconds(total_time_seconds),
        "avg_time_seconds": avg_time_seconds,
        "avg_time_formatted": format_seconds(avg_time_seconds),
        "fastest": fastest,
        "slowest": slowest,
        "quiz_time_records": quiz_time_records,
        "chart_base64": chart_base64
    }


def analyze_weak_topics(student_id):
    """
    Analyzes student answer performance by topic using SQL, Pandas, and Matplotlib.
    Calculates accuracy per topic: (correct answers / total questions answered) * 100.
    Classifies topics into mastery tiers:
      - Strong Mastery (>= 80%)
      - Good Understanding (60% - 79%)
      - Needs Practice (40% - 59%)
      - Weak Topic (< 40%)
    Generates a color-coded horizontal bar chart of topic performance.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT 
                t.topic_id,
                t.topic_name,
                s.subject_name,
                COUNT(sa.answer_id) AS total_questions,
                SUM(CASE WHEN sa.is_correct THEN 1 ELSE 0 END) AS correct_answers
            FROM student_answers sa
            JOIN quiz_attempts qa ON sa.attempt_id = qa.attempt_id
            JOIN questions q ON sa.question_id = q.question_id
            JOIN topics t ON q.topic_id = t.topic_id
            JOIN subjects s ON t.subject_id = s.subject_id
            WHERE qa.student_id = %s AND qa.submitted_at IS NOT NULL
            GROUP BY t.topic_id, t.topic_name, s.subject_name
            ORDER BY t.topic_name ASC
            """,
            (student_id,)
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    if not rows:
        return {
            "has_data": False,
            "total_topics_analyzed": 0,
            "weak_topics_count": 0,
            "needs_practice_count": 0,
            "good_topics_count": 0,
            "strong_topics_count": 0,
            "weak_topics": [],
            "needs_practice_topics": [],
            "all_topics": [],
            "chart_base64": None
        }

    # Load into Pandas DataFrame
    df = pd.DataFrame(rows, columns=[
        "topic_id", "topic_name", "subject_name", "total_questions", "correct_answers"
    ])
    df["total_questions"] = df["total_questions"].astype(int)
    df["correct_answers"] = df["correct_answers"].astype(int)
    df["incorrect_answers"] = df["total_questions"] - df["correct_answers"]
    df["accuracy"] = ((df["correct_answers"] / df["total_questions"]) * 100.0).round(1)

    # Classify mastery levels
    def classify_mastery(acc):
        if acc >= 80.0:
            return "Strong Mastery", "success", "#10b981"
        elif acc >= 60.0:
            return "Good Understanding", "primary", "#3b82f6"
        elif acc >= 40.0:
            return "Needs Practice", "warning", "#f59e0b"
        else:
            return "Weak Topic", "danger", "#ef4444"

    mastery_info = df["accuracy"].apply(classify_mastery)
    df["mastery_level"] = [m[0] for m in mastery_info]
    df["badge_class"] = [m[1] for m in mastery_info]
    df["bar_color"] = [m[2] for m in mastery_info]

    # Sort topics by accuracy ascending (weakest topics first)
    df_sorted = df.sort_values(by=["accuracy", "total_questions"], ascending=[True, False]).reset_index(drop=True)

    all_topics = df_sorted.to_dict(orient="records")
    weak_topics = [t for t in all_topics if t["mastery_level"] == "Weak Topic"]
    needs_practice_topics = [t for t in all_topics if t["mastery_level"] == "Needs Practice"]
    good_topics = [t for t in all_topics if t["mastery_level"] == "Good Understanding"]
    strong_topics = [t for t in all_topics if t["mastery_level"] == "Strong Mastery"]

    # Matplotlib Horizontal Bar Chart
    chart_base64 = None
    try:
        fig_height = max(3.8, len(df_sorted) * 0.6 + 1.2)
        fig, ax = plt.subplots(figsize=(9, fig_height), dpi=100)
        fig.patch.set_facecolor('#ffffff')
        ax.set_facecolor('#f8fafc')

        y_positions = np.arange(len(df_sorted))
        labels = [f"{r['topic_name']} ({r['subject_name']})" for _, r in df_sorted.iterrows()]
        accuracies = df_sorted["accuracy"].values
        colors = df_sorted["bar_color"].values

        bars = ax.barh(y_positions, accuracies, color=colors, height=0.55, edgecolor="#ffffff", linewidth=1.5, zorder=3)
        ax.set_yticks(y_positions)
        ax.set_yticklabels(labels, fontsize=10, fontweight='bold', color="#1e293b")
        ax.invert_yaxis()  # Weakest topics at the top

        # Annotate each bar with accuracy and fraction
        for i, (bar, acc, r) in enumerate(zip(bars, accuracies, df_sorted.to_dict(orient='records'))):
            text_x = acc + 1.5 if acc < 82 else acc - 1.5
            text_color = "#334155" if acc < 82 else "#ffffff"
            ha = "left" if acc < 82 else "right"
            ax.text(
                text_x,
                bar.get_y() + bar.get_height() / 2,
                f"{acc:.1f}% ({r['correct_answers']}/{r['total_questions']})",
                va="center",
                ha=ha,
                fontsize=9,
                fontweight="bold",
                color=text_color,
                zorder=4
            )

        # Baseline threshold lines
        ax.axvline(60, color="#64748b", linestyle="--", linewidth=1.5, alpha=0.75, label="Proficiency Baseline (60%)", zorder=2)
        ax.axvline(80, color="#10b981", linestyle=":", linewidth=1.5, alpha=0.6, label="Mastery Baseline (80%)", zorder=2)

        ax.set_xlim(0, 108)
        ax.set_xlabel("Topic Accuracy (%)", fontsize=10, fontweight="bold", color="#475569", labelpad=8)
        ax.set_title("Topic Mastery & Accuracy Breakdown (Weakest to Strongest)", fontsize=12, fontweight="bold", color="#0f172a", pad=14)
        ax.grid(True, axis="x", linestyle=":", alpha=0.5, color="#cbd5e1", zorder=1)
        ax.legend(loc="lower right", fontsize=8, frameon=True, facecolor="#ffffff")

        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color("#cbd5e1")
        ax.spines["bottom"].set_color("#cbd5e1")

        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        plt.close(fig)
    except Exception as e:
        print("Error generating weak topics chart:", e)
        plt.close('all')

    return {
        "has_data": True,
        "total_topics_analyzed": len(all_topics),
        "weak_topics_count": len(weak_topics),
        "needs_practice_count": len(needs_practice_topics),
        "good_topics_count": len(good_topics),
        "strong_topics_count": len(strong_topics),
        "weak_topics": weak_topics,
        "needs_practice_topics": needs_practice_topics,
        "all_topics": all_topics,
        "chart_base64": chart_base64
    }


