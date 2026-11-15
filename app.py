from datetime import datetime
from functools import wraps
import os
import re

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, jsonify
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import json
from config import get_db_connection
from modules.ai_generator import generate_ai_questions, AIGenerationError
from analytics.performance import (
    analyze_performance_trend,
    analyze_time_performance,
    analyze_weak_topics
)
from analytics.recommendations import (
    get_or_generate_recommendations,
    complete_recommendation
)
from analytics.retention import get_retention_analytics

load_dotenv()

app = Flask(
    __name__,
    template_folder="frontend/templates",
    static_folder="frontend/static"
)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is missing from .env")


def login_required(f):
    """Decorator to require login for protected student routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "student_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    is_logged_in = "student_id" in session
    student_name = session.get("student_name", "")
    return render_template(
        "index.html",
        is_logged_in=is_logged_in,
        student_name=student_name,
        year=datetime.now().year
    )


# Student Registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if "student_id" in session:
        return redirect(url_for("dashboard"))

    name = ""
    email = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not name:
            flash("Please enter your full name.", "danger")
        elif not email or "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "danger")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT student_id FROM students WHERE email = %s",
                    (email,)
                )
                existing_student = cursor.fetchone()

                if existing_student:
                    flash("An account with this email already exists. Please log in.", "warning")
                    cursor.close()
                    return redirect(url_for("login"))
                else:
                    password_hash = generate_password_hash(password)
                    cursor.execute(
                        """
                        INSERT INTO students (name, email, password_hash)
                        VALUES (%s, %s, %s)
                        """,
                        (name, email, password_hash)
                    )
                    conn.commit()
                    cursor.close()

                    flash("Registration successful! You can now log in.", "success")
                    return redirect(url_for("login"))

            except Exception as e:
                if conn:
                    conn.rollback()
                print("Registration error:", e)
                flash("Something went wrong during registration. Please try again.", "danger")
            finally:
                if conn:
                    conn.close()

    return render_template("register.html", name=name, email=email)


# Student Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if "student_id" in session:
        return redirect(url_for("dashboard"))

    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html", email=email)

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT student_id, name, email, password_hash
                FROM students
                WHERE email = %s
                """,
                (email,)
            )
            student = cursor.fetchone()
            cursor.close()

            if student and check_password_hash(student[3], password):
                session.clear()
                session["student_id"] = student[0]
                session["student_name"] = student[1]
                session["student_email"] = student[2]

                flash(f"Welcome back, {student[1]}!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid email or password. Please try again.", "danger")

        except Exception as e:
            print("Login error:", e)
            flash("Unable to connect or log in. Please try again.", "danger")
        finally:
            if conn:
                conn.close()

    return render_template("login.html", email=email)


# Student Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    # Clear any active quiz attempt session tracking
    session.pop("active_quiz_attempt_id", None)
    session.pop("active_quiz_id", None)
    session.pop("active_ai_attempt_id", None)

    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Total Quizzes Attempted, Average Score, Overall Accuracy
        cursor.execute(
            """
            SELECT 
                COUNT(*),
                COALESCE(ROUND(AVG(score), 1), 0),
                COALESCE(ROUND(AVG(accuracy), 1), 0)
            FROM quiz_attempts
            WHERE student_id = %s AND submitted_at IS NOT NULL
            """,
            (student_id,)
        )
        stats = cursor.fetchone()
        total_attempts = stats[0] if stats else 0
        avg_score = float(stats[1]) if stats else 0.0
        overall_accuracy = float(stats[2]) if stats else 0.0

        # 2. Latest Quiz Score & Performance Improvement
        cursor.execute(
            """
            SELECT score
            FROM quiz_attempts
            WHERE student_id = %s AND submitted_at IS NOT NULL
            ORDER BY submitted_at DESC
            LIMIT 2
            """,
            (student_id,)
        )
        recent_scores = cursor.fetchall()
        latest_score = float(recent_scores[0][0]) if recent_scores else None

        improvement = None
        improvement_status = "No attempts yet"
        if len(recent_scores) >= 2:
            current_s = float(recent_scores[0][0])
            prev_s = float(recent_scores[1][0])
            diff = round(current_s - prev_s, 1)
            if diff > 0:
                improvement = f"+{diff}%"
                improvement_status = "Improving"
            elif diff < 0:
                improvement = f"{diff}%"
                improvement_status = "Declining"
            else:
                improvement = "0.0%"
                improvement_status = "Stable"
        elif len(recent_scores) == 1:
            improvement = "Baseline"
            improvement_status = "First quiz completed"

        # 3. Available Subjects (Curated Subjects with topics and available existing quiz counts)
        cursor.execute(
            """
            SELECT 
                s.subject_id, 
                s.subject_name, 
                COUNT(DISTINCT t.topic_id) AS topic_count,
                COUNT(DISTINCT q.quiz_id) AS quiz_count
            FROM subjects s
            LEFT JOIN topics t ON s.subject_id = t.subject_id
            LEFT JOIN quizzes q ON s.subject_id = q.subject_id 
                AND q.quiz_type = 'Existing'
                AND EXISTS (SELECT 1 FROM quiz_questions qq WHERE qq.quiz_id = q.quiz_id)
            GROUP BY s.subject_id, s.subject_name
            ORDER BY s.subject_name
            """
        )
        available_subjects = cursor.fetchall()

        # 4. Available Quizzes (quizzes with questions)
        cursor.execute(
            """
            SELECT 
                q.quiz_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                q.difficulty,
                q.quiz_type,
                COUNT(qq.question_id) AS question_count
            FROM quizzes q
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            LEFT JOIN quiz_questions qq ON q.quiz_id = qq.quiz_id
            GROUP BY q.quiz_id, q.quiz_title, s.subject_name, t.topic_name, q.difficulty, q.quiz_type
            HAVING COUNT(qq.question_id) > 0
            ORDER BY q.quiz_id
            LIMIT 6
            """
        )
        available_quizzes_list = cursor.fetchall()

        # 5. Recent Quiz Attempts
        cursor.execute(
            """
            SELECT 
                qa.attempt_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                qa.score,
                qa.accuracy,
                qa.time_taken_seconds,
                qa.submitted_at
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.quiz_id
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            WHERE qa.student_id = %s AND qa.submitted_at IS NOT NULL
            ORDER BY qa.submitted_at DESC
            LIMIT 5
            """,
            (student_id,)
        )
        recent_attempts = cursor.fetchall()

        # 6. Upcoming Retention Quizzes
        cursor.execute(
            """
            SELECT 
                rs.schedule_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                rs.scheduled_for,
                rs.status,
                q.quiz_id
            FROM retention_schedules rs
            JOIN quizzes q ON rs.quiz_id = q.quiz_id
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            WHERE rs.student_id = %s AND rs.status = 'Pending'
            ORDER BY rs.scheduled_for ASC
            LIMIT 5
            """,
            (student_id,)
        )
        upcoming_retention = cursor.fetchall()

        cursor.close()

        return render_template(
            "dashboard.html",
            name=session["student_name"],
            total_attempts=total_attempts,
            avg_score=avg_score,
            latest_score=latest_score,
            overall_accuracy=overall_accuracy,
            improvement=improvement,
            improvement_status=improvement_status,
            subjects=available_subjects,
            quizzes=available_quizzes_list,
            recent_attempts=recent_attempts,
            upcoming_retention=upcoming_retention
        )

    except Exception as e:
        print("Dashboard error:", e)
        flash("Could not load full dashboard statistics.", "danger")
        return render_template(
            "dashboard.html",
            name=session.get("student_name", "Student"),
            total_attempts=0,
            avg_score=0.0,
            latest_score=None,
            overall_accuracy=0.0,
            improvement=None,
            improvement_status="Error loading stats",
            subjects=[],
            quizzes=[],
            recent_attempts=[],
            upcoming_retention=[]
        )
    finally:
        if conn:
            conn.close()


# API endpoint to fetch topics for a selected subject dynamically
@app.route("/api/topics/<int:subject_id>")
@login_required
def get_topics_by_subject(subject_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT topic_id, topic_name FROM topics WHERE subject_id = %s ORDER BY topic_name",
            (subject_id,)
        )
        topics = [{"topic_id": r[0], "topic_name": r[1]} for r in cursor.fetchall()]
        cursor.close()
        return jsonify(topics)
    except Exception as e:
        print("Error fetching topics:", e)
        return jsonify([]), 500
    finally:
        if conn:
            conn.close()


# Subject, Topic, and Quiz Selection Route (Existing Curriculum Quizzes)
@app.route("/quizzes")
@app.route("/select-quiz")
@login_required
def available_quizzes():
    # Clear any active quiz attempt session tracking when viewing quiz selection
    session.pop("active_quiz_attempt_id", None)
    session.pop("active_quiz_id", None)
    session.pop("active_ai_attempt_id", None)

    subject_id = request.args.get("subject_id", type=int)
    topic_id = request.args.get("topic_id", type=int)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Step 1: All available subjects dynamically from database
        cursor.execute("SELECT subject_id, subject_name FROM subjects ORDER BY subject_name")
        subjects = cursor.fetchall()

        # Step 2: Topics belonging strictly to the selected subject dynamically from database
        if subject_id:
            cursor.execute(
                "SELECT topic_id, subject_id, topic_name FROM topics WHERE subject_id = %s ORDER BY topic_name",
                (subject_id,)
            )
            topics = cursor.fetchall()
            valid_topic_ids = {t[0] for t in topics}
            if topic_id and topic_id not in valid_topic_ids:
                topic_id = None
        else:
            topics = []
            topic_id = None

        # Step 3: Quizzes matching subject and topic
        query = """
            SELECT 
                q.quiz_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                q.difficulty,
                q.quiz_type,
                COUNT(qq.question_id) AS question_count
            FROM quizzes q
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            LEFT JOIN quiz_questions qq ON q.quiz_id = qq.quiz_id
            WHERE q.quiz_type = 'Existing'
        """
        params = []
        if subject_id:
            query += " AND q.subject_id = %s"
            params.append(subject_id)
        if topic_id:
            query += " AND q.topic_id = %s"
            params.append(topic_id)

        query += """
            GROUP BY q.quiz_id, q.quiz_title, s.subject_name, t.topic_name, q.difficulty, q.quiz_type
            HAVING COUNT(qq.question_id) > 0
            ORDER BY q.quiz_id
        """
        cursor.execute(query, tuple(params))
        quizzes = cursor.fetchall()
        cursor.close()

        return render_template(
            "quiz_selection.html",
            subjects=subjects,
            topics=topics,
            quizzes=quizzes,
            selected_subject_id=subject_id,
            selected_topic_id=topic_id
        )
    except Exception as e:
        print("Error in available_quizzes:", e)
        flash("Unable to load quizzes. Please try again.", "danger")
        return redirect(url_for("dashboard"))
    finally:
        if conn:
            conn.close()


# AI Quiz Generator Route
@app.route("/generate-quiz", methods=["GET", "POST"])
@app.route("/ai-quiz", methods=["GET", "POST"])
@login_required
def generate_ai_quiz():
    # Clear any active quiz attempt session tracking
    session.pop("active_quiz_attempt_id", None)
    session.pop("active_quiz_id", None)
    session.pop("active_ai_attempt_id", None)

    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == "POST":
            topic = request.form.get("topic", "").strip()
            difficulty = request.form.get("difficulty", "Medium").strip()
            num_questions = request.form.get("num_questions", type=int, default=5)

            if not topic:
                flash("Please enter an educational topic for AI quiz generation.", "danger")
                return redirect(url_for("generate_ai_quiz"))

            if difficulty not in ["Easy", "Medium", "Hard"]:
                difficulty = "Medium"

            try:
                num_questions = max(1, min(20, int(num_questions)))
            except (ValueError, TypeError):
                num_questions = 5

            # Generate questions via decoupled AI generator module
            try:
                questions, source = generate_ai_questions(
                    topic=topic,
                    difficulty=difficulty,
                    num_questions=num_questions
                )
            except AIGenerationError as age:
                flash(f"AI Generation Notice: {str(age)}", "warning")
                return redirect(url_for("generate_ai_quiz"))
            except Exception as e:
                print("Unexpected AI generation error:", e)
                flash(f"AI Generation Error: {str(e)}", "danger")
                return redirect(url_for("generate_ai_quiz"))

            if not questions:
                flash("AI generation failed to produce valid questions for this topic. Please try again or specify a different topic.", "danger")
                return redirect(url_for("generate_ai_quiz"))

            # Save attempt strictly into ai_quiz_attempts table (NEVER in quizzes or questions)
            cursor.execute(
                """
                INSERT INTO ai_quiz_attempts 
                (student_id, topic, difficulty, num_questions, total_questions, questions_data, started_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING ai_attempt_id
                """,
                (
                    student_id,
                    topic,
                    difficulty,
                    len(questions),
                    len(questions),
                    json.dumps(questions)
                )
            )
            ai_attempt_id = cursor.fetchone()[0]
            conn.commit()

            flash(f"Successfully generated {len(questions)} verified questions on '{topic}'", "success")
            return redirect(url_for("start_ai_quiz", ai_attempt_id=ai_attempt_id))

        # GET Request: Render generation form and student's recent AI quiz attempts
        cursor.execute(
            """
            SELECT ai_attempt_id, student_id, topic, difficulty, total_questions, score, submitted_at
            FROM ai_quiz_attempts
            WHERE student_id = %s AND submitted_at IS NOT NULL
            ORDER BY submitted_at DESC
            LIMIT 5
            """,
            (student_id,)
        )
        recent_ai_attempts = cursor.fetchall()
        cursor.close()

        return render_template(
            "ai_quiz.html",
            recent_ai_attempts=recent_ai_attempts
        )

    except Exception as e:
        print("Error in generate_ai_quiz:", e)
        flash("An error occurred during AI quiz configuration.", "danger")
        return redirect(url_for("dashboard"))
    finally:
        if conn:
            conn.close()


# AI Quiz Runner Route (Elapsed Stopwatch and Question Answering)
@app.route("/ai-quiz/attempt/<int:ai_attempt_id>", methods=["GET"])
@app.route("/ai-quiz/start/<int:ai_attempt_id>", methods=["GET"])
@login_required
def start_ai_quiz(ai_attempt_id):
    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT topic, difficulty, num_questions, questions_data, started_at, submitted_at
            FROM ai_quiz_attempts
            WHERE ai_attempt_id = %s AND student_id = %s
            """,
            (ai_attempt_id, student_id)
        )
        row = cursor.fetchone()

        if not row:
            cursor.close()
            flash("AI quiz attempt not found or unauthorized.", "danger")
            return redirect(url_for("generate_ai_quiz"))

        topic, difficulty, num_questions, questions_raw, started_at, submitted_at = row

        if submitted_at is not None:
            flash("This AI quiz attempt has already been submitted.", "info")
            return redirect(url_for("view_ai_quiz_result", ai_attempt_id=ai_attempt_id))

        active_ai_id = session.get("active_ai_attempt_id")

        if active_ai_id == ai_attempt_id:
            # Student is refreshing an active ongoing attempt: continue elapsed time
            elapsed_seconds = max(0, int((datetime.now() - started_at).total_seconds()))
            if elapsed_seconds > 7200:
                cursor.execute(
                    "UPDATE ai_quiz_attempts SET started_at = CURRENT_TIMESTAMP WHERE ai_attempt_id = %s",
                    (ai_attempt_id,)
                )
                conn.commit()
                started_at = datetime.now()
                elapsed_seconds = 0
        else:
            # Fresh opening of this attempt: start brand-new timer at 00:00
            cursor.execute(
                "UPDATE ai_quiz_attempts SET started_at = CURRENT_TIMESTAMP WHERE ai_attempt_id = %s AND submitted_at IS NULL",
                (ai_attempt_id,)
            )
            conn.commit()
            started_at = datetime.now()
            elapsed_seconds = 0
            session["active_ai_attempt_id"] = ai_attempt_id

        cursor.close()

        questions = json.loads(questions_raw) if isinstance(questions_raw, str) else questions_raw

        return render_template(
            "ai_quiz_runner.html",
            ai_attempt_id=ai_attempt_id,
            topic=topic,
            difficulty=difficulty,
            questions=questions,
            elapsed_seconds=elapsed_seconds,
            started_at_iso=started_at.isoformat()
        )
    except Exception as e:
        print("Error in start_ai_quiz:", e)
        flash("Unable to load the AI quiz.", "danger")
        return redirect(url_for("generate_ai_quiz"))
    finally:
        if conn:
            conn.close()


# AI Quiz Submission Handler
@app.route("/ai-quiz/submit/<int:ai_attempt_id>", methods=["POST"])
@login_required
def submit_ai_quiz(ai_attempt_id):
    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT topic, difficulty, total_questions, questions_data, started_at, submitted_at
            FROM ai_quiz_attempts
            WHERE ai_attempt_id = %s AND student_id = %s
            """,
            (ai_attempt_id, student_id)
        )
        attempt = cursor.fetchone()
        if not attempt:
            flash("AI quiz attempt could not be verified.", "danger")
            return redirect(url_for("generate_ai_quiz"))

        if attempt[5] is not None:
            flash("This AI quiz attempt was already submitted.", "info")
            return redirect(url_for("view_ai_quiz_result", ai_attempt_id=ai_attempt_id))

        topic = attempt[0]
        started_at = attempt[4]
        questions_raw = attempt[3]
        questions = json.loads(questions_raw) if isinstance(questions_raw, str) else questions_raw

        answers = {}
        correct_count = 0

        for q in questions:
            qid = q["question_id"]
            selected = request.form.get(f"question_{qid}")
            if selected not in ["A", "B", "C", "D"]:
                flash("Please select an answer for every question before submitting.", "danger")
                return redirect(url_for("start_ai_quiz", ai_attempt_id=ai_attempt_id))

            is_correct = (selected == q["correct_option"])
            if is_correct:
                correct_count += 1

            answers[str(qid)] = {
                "selected": selected,
                "correct": q["correct_option"],
                "is_correct": is_correct
            }

        total_q = len(questions)
        score = round((correct_count / total_q) * 100, 2) if total_q else 0.0
        accuracy = score
        time_taken = max(0, int((datetime.now() - started_at).total_seconds()))

        cursor.execute(
            """
            UPDATE ai_quiz_attempts
            SET submitted_at = CURRENT_TIMESTAMP,
                student_answers = %s,
                correct_answers = %s,
                score = %s,
                accuracy = %s,
                time_taken_seconds = %s
            WHERE ai_attempt_id = %s
            """,
            (
                json.dumps(answers),
                correct_count,
                score,
                accuracy,
                time_taken,
                ai_attempt_id
            )
        )
        conn.commit()
        cursor.close()

        # Stop timer tracking for this submitted AI attempt
        session.pop("active_ai_attempt_id", None)

        flash(f"AI Quiz submitted successfully! You scored {correct_count}/{total_q} ({score}%).", "success")
        return redirect(url_for("view_ai_quiz_result", ai_attempt_id=ai_attempt_id))

    except Exception as e:
        if conn:
            conn.rollback()
        print("Error in submit_ai_quiz:", e)
        flash("An error occurred during AI quiz submission.", "danger")
        return redirect(url_for("generate_ai_quiz"))
    finally:
        if conn:
            conn.close()


# Detailed AI Quiz Result Route
@app.route("/ai-quiz/result/<int:ai_attempt_id>")
@login_required
def view_ai_quiz_result(ai_attempt_id):
    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT 
                topic,
                difficulty,
                total_questions,
                questions_data,
                student_answers,
                score,
                accuracy,
                correct_answers,
                time_taken_seconds,
                submitted_at
            FROM ai_quiz_attempts
            WHERE ai_attempt_id = %s AND student_id = %s
            """,
            (ai_attempt_id, student_id)
        )
        attempt = cursor.fetchone()
        cursor.close()

        if not attempt:
            flash("AI quiz result not found or access denied.", "danger")
            return redirect(url_for("generate_ai_quiz"))

        topic = attempt[0]
        difficulty = attempt[1]
        total_questions = attempt[2]
        questions_raw = attempt[3]
        answers_raw = attempt[4]
        score = float(attempt[5]) if attempt[5] is not None else 0.0
        accuracy = float(attempt[6]) if attempt[6] is not None else 0.0
        correct_answers = attempt[7] or 0
        incorrect_answers = total_questions - correct_answers
        time_taken_seconds = attempt[8] or 0
        submitted_at = attempt[9]

        questions = json.loads(questions_raw) if isinstance(questions_raw, str) else questions_raw
        answers = json.loads(answers_raw) if isinstance(answers_raw, str) else (answers_raw or {})

        questions_review = []
        for q in questions:
            qid_str = str(q["question_id"])
            ans_info = answers.get(qid_str, {})
            questions_review.append({
                "question_text": q.get("question_text", ""),
                "option_a": q.get("option_a", ""),
                "option_b": q.get("option_b", ""),
                "option_c": q.get("option_c", ""),
                "option_d": q.get("option_d", ""),
                "correct_option": q.get("correct_option", ""),
                "selected_option": ans_info.get("selected", "N/A"),
                "is_correct": ans_info.get("is_correct", False),
                "explanation": q.get("explanation", "")
            })

        return render_template(
            "ai_result.html",
            ai_attempt_id=ai_attempt_id,
            topic=topic,
            difficulty=difficulty,
            total_questions=total_questions,
            correct_answers=correct_answers,
            incorrect_answers=incorrect_answers,
            score=score,
            accuracy=accuracy,
            time_taken_seconds=time_taken_seconds,
            submitted_at=submitted_at,
            questions_review=questions_review
        )
    except Exception as e:
        print("Error in view_ai_quiz_result:", e)
        flash("Unable to load AI quiz results.", "danger")
        return redirect(url_for("generate_ai_quiz"))
    finally:
        if conn:
            conn.close()


# Quiz History Route (Combined Curriculum Quizzes & AI Quizzes)
@app.route("/history")
@login_required
def quiz_history():
    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Existing curriculum quiz attempts
        cursor.execute(
            """
            SELECT 
                qa.attempt_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                q.difficulty,
                qa.score,
                qa.accuracy,
                qa.total_questions,
                qa.correct_answers,
                qa.time_taken_seconds,
                qa.submitted_at
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.quiz_id
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            WHERE qa.student_id = %s AND qa.submitted_at IS NOT NULL
            ORDER BY qa.submitted_at DESC
            """,
            (student_id,)
        )
        attempts = cursor.fetchall()

        # 2. Separate AI quiz attempts
        cursor.execute(
            """
            SELECT 
                ai_attempt_id,
                student_id,
                topic,
                difficulty,
                total_questions,
                score,
                accuracy,
                correct_answers,
                time_taken_seconds,
                submitted_at
            FROM ai_quiz_attempts
            WHERE student_id = %s AND submitted_at IS NOT NULL
            ORDER BY submitted_at DESC
            """,
            (student_id,)
        )
        ai_attempts = cursor.fetchall()
        cursor.close()

        # Compute combined summary metrics
        total_attempts_count = len(attempts) + len(ai_attempts)
        all_scores = [float(a[5]) for a in attempts if a[5] is not None] + [float(a[5]) for a in ai_attempts if a[5] is not None]
        all_times = [int(a[9]) for a in attempts if a[9] is not None] + [int(a[8]) for a in ai_attempts if a[8] is not None]

        avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
        best_score = max(all_scores) if all_scores else None
        total_time_seconds = sum(all_times) if all_times else 0

        return render_template(
            "history.html",
            attempts=attempts,
            ai_attempts=ai_attempts,
            total_attempts_count=total_attempts_count,
            avg_score=avg_score,
            best_score=best_score,
            total_time_seconds=total_time_seconds
        )
    except Exception as e:
        print("Error in quiz_history:", e)
        flash("Unable to load quiz history.", "danger")
        return redirect(url_for("dashboard"))
    finally:
        if conn:
            conn.close()



@app.route("/analytics")
@login_required
def analytics_view():
    student_id = session["student_id"]
    try:
        trend_data = analyze_performance_trend(student_id)
        time_data = analyze_time_performance(student_id)
        weak_data = analyze_weak_topics(student_id)
        return render_template(
            "analytics.html",
            trend=trend_data,
            time_analysis=time_data,
            weak_analysis=weak_data
        )
    except Exception as e:
        print("Error in analytics_view:", e)
        flash("Unable to load performance analytics.", "danger")
        return redirect(url_for("dashboard"))



@app.route("/recommendations")
@login_required
def recommendations_view():
    student_id = session["student_id"]
    try:
        rec_data = get_or_generate_recommendations(student_id)
        return render_template(
            "recommendations.html",
            recommendations=rec_data
        )
    except Exception as e:
        print("Error in recommendations_view:", e)
        flash("Unable to load recommendations. Please try again.", "danger")
        return redirect(url_for("dashboard"))


@app.route("/recommendations/complete/<int:recommendation_id>", methods=["POST"])
@login_required
def complete_recommendation_route(recommendation_id):
    student_id = session["student_id"]
    try:
        success = complete_recommendation(recommendation_id, student_id)
        if success:
            flash("Recommendation marked as completed!", "success")
        else:
            flash("Unable to update recommendation.", "warning")
    except Exception as e:
        print("Error in complete_recommendation_route:", e)
        flash("An error occurred while updating recommendation.", "danger")
    return redirect(url_for("recommendations_view"))


@app.route("/retention")
@login_required
def retention_view():
    student_id = session["student_id"]
    try:
        retention_data = get_retention_analytics(student_id)
        return render_template(
            "retention.html",
            retention=retention_data
        )
    except Exception as e:
        print("Error in retention_view:", e)
        flash("Unable to load retention analytics. Please try again.", "danger")
        return redirect(url_for("dashboard"))


@app.route("/retention/take/<int:schedule_id>")
@login_required
def take_retention_quiz(schedule_id):
    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT quiz_id FROM retention_schedules
            WHERE schedule_id = %s AND student_id = %s AND status = 'Pending'
            """,
            (schedule_id, student_id)
        )
        row = cursor.fetchone()
        cursor.close()

        if not row:
            flash("Scheduled retention quiz not found or already completed.", "warning")
            return redirect(url_for("retention_view"))

        quiz_id = row[0]
        session["active_retention_schedule_id"] = schedule_id
        flash("Starting scheduled retention follow-up quiz. Do your best to measure your knowledge retention!", "info")
        return redirect(url_for("start_quiz", quiz_id=quiz_id))
    except Exception as e:
        print("Error in take_retention_quiz:", e)
        flash("Unable to initiate retention quiz.", "danger")
        return redirect(url_for("retention_view"))
    finally:
        if conn:
            conn.close()


# Student Logout
@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


@app.route("/quiz/<int:quiz_id>", methods=["GET", "POST"])
@login_required
def start_quiz(quiz_id):
    student_id = session["student_id"]
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch Quiz Metadata
        cursor.execute(
            """
            SELECT q.quiz_title, s.subject_name, t.topic_name, q.difficulty
            FROM quizzes q
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            WHERE q.quiz_id = %s
            """,
            (quiz_id,)
        )
        quiz_meta = cursor.fetchone()
        if not quiz_meta:
            flash("The requested quiz does not exist.", "danger")
            return redirect(url_for("available_quizzes"))

        quiz_title, subject_name, topic_name, difficulty = quiz_meta

        # GET: Start or resume an active quiz attempt
        if request.method == "GET":

            active_attempt_id = session.get("active_quiz_attempt_id")
            active_quiz_id = session.get("active_quiz_id")

            existing_attempt = None
            # Only resume if student is refreshing their active session for this exact quiz
            if active_attempt_id and active_quiz_id == quiz_id:
                cursor.execute(
                    """
                    SELECT attempt_id, started_at
                    FROM quiz_attempts
                    WHERE attempt_id = %s AND student_id = %s AND quiz_id = %s AND submitted_at IS NULL
                    """,
                    (active_attempt_id, student_id, quiz_id)
                )
                existing_attempt = cursor.fetchone()
                # Stale check: do not resume if older than 2 hours
                if existing_attempt:
                    diff_sec = int((datetime.now() - existing_attempt[1]).total_seconds())
                    if diff_sec > 7200:
                        existing_attempt = None

            if existing_attempt:
                attempt_id = existing_attempt[0]
                started_at = existing_attempt[1]
                elapsed_seconds = max(0, int((datetime.now() - started_at).total_seconds()))
            else:
                # Brand new quiz attempt: always starts fresh at 00:00
                cursor.execute(
                    """
                    INSERT INTO quiz_attempts (student_id, quiz_id, started_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    RETURNING attempt_id, started_at
                    """,
                    (student_id, quiz_id)
                )
                new_att = cursor.fetchone()
                attempt_id = new_att[0]
                started_at = new_att[1]
                elapsed_seconds = 0
                conn.commit()
                session["active_quiz_attempt_id"] = attempt_id
                session["active_quiz_id"] = quiz_id

            # Load questions for the student (do NOT select correct_option here)
            cursor.execute(
                """
                SELECT
                    q.question_id,
                    q.question_text,
                    q.option_a,
                    q.option_b,
                    q.option_c,
                    q.option_d
                FROM quiz_questions qq
                JOIN questions q
                    ON qq.question_id = q.question_id
                WHERE qq.quiz_id = %s
                ORDER BY q.question_id
                """,
                (quiz_id,)
            )
            questions = cursor.fetchall()

            if not questions:
                flash("No questions found for this quiz.", "warning")
                return redirect(url_for("available_quizzes"))

            cursor.close()

            return render_template(
                "quiz.html",
                questions=questions,
                quiz_id=quiz_id,
                attempt_id=attempt_id,
                quiz_title=quiz_title,
                subject_name=subject_name,
                topic_name=topic_name,
                difficulty=difficulty,
                elapsed_seconds=elapsed_seconds,
                started_at_iso=started_at.isoformat()
            )

        # POST: Submit the quiz answers
        else:
            attempt_id = request.form.get("attempt_id")

            if not attempt_id or not attempt_id.isdigit():
                flash("Invalid quiz attempt identification.", "danger")
                return redirect(url_for("available_quizzes"))

            attempt_id = int(attempt_id)

            cursor.execute(
                """
                SELECT started_at, submitted_at
                FROM quiz_attempts
                WHERE attempt_id = %s
                AND student_id = %s
                AND quiz_id = %s
                """,
                (attempt_id, student_id, quiz_id)
            )
            attempt = cursor.fetchone()

            if not attempt:
                flash("Quiz attempt could not be verified.", "danger")
                return redirect(url_for("available_quizzes"))

            # Duplicate submission prevention
            if attempt[1] is not None:
                flash("This quiz attempt was already submitted.", "info")
                return redirect(url_for("view_quiz_result", attempt_id=attempt_id))

            started_at = attempt[0]

            cursor.execute(
                """
                SELECT q.question_id, q.correct_option
                FROM quiz_questions qq
                JOIN questions q
                    ON qq.question_id = q.question_id
                WHERE qq.quiz_id = %s
                ORDER BY q.question_id
                """,
                (quiz_id,)
            )
            questions = cursor.fetchall()

            total_questions = len(questions)
            correct_answers = 0

            # Delete any partial previous answers for this attempt before re-recording
            cursor.execute("DELETE FROM student_answers WHERE attempt_id = %s", (attempt_id,))

            for question in questions:
                question_id = question[0]
                correct_option = question[1]

                selected_option = request.form.get(f"question_{question_id}")

                if selected_option not in ["A", "B", "C", "D"]:
                    flash("Please select an answer for every question.", "danger")
                    return redirect(url_for("start_quiz", quiz_id=quiz_id))

                is_correct = (selected_option == correct_option)
                if is_correct:
                    correct_answers += 1

                cursor.execute(
                    """
                    INSERT INTO student_answers
                    (attempt_id, question_id, selected_option, is_correct)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (attempt_id, question_id, selected_option, is_correct)
                )

            # Mathematical score and accuracy calculations
            score = round((correct_answers / total_questions) * 100, 2) if total_questions else 0.0
            accuracy = score
            time_taken = max(0, int((datetime.now() - started_at).total_seconds()))

            # Update the attempt record
            cursor.execute(
                """
                UPDATE quiz_attempts
                SET submitted_at = CURRENT_TIMESTAMP,
                    total_questions = %s,
                    correct_answers = %s,
                    score = %s,
                    accuracy = %s,
                    time_taken_seconds = %s
                WHERE attempt_id = %s
                """,
                (
                    total_questions,
                    correct_answers,
                    score,
                    accuracy,
                    time_taken,
                    attempt_id
                )
            )

            # If this attempt was taken as a retention follow-up, mark schedule as Completed
            retention_schedule_id = session.pop("active_retention_schedule_id", None)
            if retention_schedule_id:
                cursor.execute(
                    """
                    UPDATE retention_schedules
                    SET followup_attempt_id = %s, status = 'Completed'
                    WHERE schedule_id = %s AND student_id = %s
                    """,
                    (attempt_id, retention_schedule_id, student_id)
                )
            else:
                cursor.execute(
                    """
                    UPDATE retention_schedules
                    SET followup_attempt_id = %s, status = 'Completed'
                    WHERE schedule_id = (
                        SELECT schedule_id FROM retention_schedules
                        WHERE student_id = %s AND quiz_id = %s AND status = 'Pending' AND initial_attempt_id != %s
                        ORDER BY scheduled_for ASC
                        LIMIT 1
                    )
                    """,
                    (attempt_id, student_id, quiz_id, attempt_id)
                )

            # Automatically schedule 7-day knowledge retention follow-up for new quiz attempts
            cursor.execute(
                """
                INSERT INTO retention_schedules (student_id, initial_attempt_id, quiz_id, scheduled_for, status)
                SELECT %s, %s, %s, CURRENT_TIMESTAMP + INTERVAL '7 days', 'Pending'
                WHERE NOT EXISTS (
                    SELECT 1 FROM retention_schedules WHERE initial_attempt_id = %s
                )
                """,
                (student_id, attempt_id, quiz_id, attempt_id)
            )

            # Commit the full transaction safely
            conn.commit()

            # Clear active quiz session tracking upon submission
            session.pop("active_quiz_attempt_id", None)
            session.pop("active_quiz_id", None)

            flash(f"Quiz submitted successfully! You scored {correct_answers}/{total_questions} ({score}%).", "success")
            return redirect(url_for("view_quiz_result", attempt_id=attempt_id))

    except Exception as e:
        if conn:
            conn.rollback()
        print("Quiz error:", e)
        flash("An error occurred during quiz execution.", "danger")
        return redirect(url_for("available_quizzes"))
    finally:
        if conn:
            conn.close()


# Detailed Quiz Result Route
@app.route("/result/<int:attempt_id>")
@login_required
def view_quiz_result(attempt_id):
    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch attempt and quiz details (enforcing authorization)
        cursor.execute(
            """
            SELECT 
                qa.attempt_id,
                q.quiz_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                q.difficulty,
                qa.total_questions,
                qa.correct_answers,
                qa.score,
                qa.accuracy,
                qa.time_taken_seconds,
                qa.started_at,
                qa.submitted_at
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.quiz_id
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            WHERE qa.attempt_id = %s AND qa.student_id = %s AND qa.submitted_at IS NOT NULL
            """,
            (attempt_id, student_id)
        )
        attempt_data = cursor.fetchone()

        if not attempt_data:
            flash("Quiz result not found or access unauthorized.", "danger")
            return redirect(url_for("dashboard"))

        # 2. Fetch question-level review with student answers and explanations
        cursor.execute(
            """
            SELECT 
                q.question_id,
                q.question_text,
                q.option_a,
                q.option_b,
                q.option_c,
                q.option_d,
                q.correct_option,
                sa.selected_option,
                sa.is_correct,
                q.explanation
            FROM student_answers sa
            JOIN questions q ON sa.question_id = q.question_id
            WHERE sa.attempt_id = %s
            ORDER BY q.question_id
            """,
            (attempt_id,)
        )
        questions_review = cursor.fetchall()
        cursor.close()

        total_q = attempt_data[6] or 0
        correct_a = attempt_data[7] or 0
        incorrect_a = max(0, total_q - correct_a)

        return render_template(
            "result.html",
            attempt=attempt_data,
            total_questions=total_q,
            correct_answers=correct_a,
            incorrect_answers=incorrect_a,
            score=attempt_data[8],
            accuracy=attempt_data[9],
            time_taken_seconds=attempt_data[10],
            submitted_at=attempt_data[12],
            questions_review=questions_review,
            student_name=session.get("student_name", "Student")
        )
    except Exception as e:
        print("Error loading quiz result:", e)
        flash("Unable to load result details.", "danger")
        return redirect(url_for("dashboard"))
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    app.run(debug=True)
