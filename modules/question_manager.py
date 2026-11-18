"""
Question Manager Module for QuizInsight.
Handles duplicate detection, text normalization, question validation,
and seamless question addition to the question bank without storage limits.
"""

import re
from typing import Optional, Dict, Any, List
from config import get_db_connection


def normalize_question_text(text: str) -> str:
    """
    Normalizes question text for robust duplicate comparison.
    Converts to lowercase, normalizes curly/straight quotes, removes punctuation,
    and collapses all whitespace to single spaces.
    """
    if not text:
        return ""
    text = text.lower()
    text = text.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
    text = re.sub(r'[\s\W_]+', ' ', text).strip()
    return text


def find_duplicate_question(question_text: str, exclude_question_id: Optional[int] = None, conn=None) -> Optional[Dict[str, Any]]:
    """
    Checks whether a duplicate or equivalent question already exists in the question bank.
    Compares normalized text against all stored questions.
    Returns the existing question details if a duplicate is found, else None.
    """
    normalized_input = normalize_question_text(question_text)
    if not normalized_input:
        return None

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cur = conn.cursor()
        query = """
            SELECT q.question_id, q.topic_id, t.topic_name, s.subject_name, q.question_text, q.difficulty
            FROM questions q
            JOIN topics t ON q.topic_id = t.topic_id
            JOIN subjects s ON t.subject_id = s.subject_id
        """
        params = []
        if exclude_question_id:
            query += " WHERE q.question_id != %s"
            params.append(exclude_question_id)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        for r in rows:
            stored_norm = normalize_question_text(r[4])
            if stored_norm == normalized_input:
                return {
                    "question_id": r[0],
                    "topic_id": r[1],
                    "topic_name": r[2],
                    "subject_name": r[3],
                    "question_text": r[4],
                    "difficulty": r[5]
                }
        return None
    finally:
        if close_conn:
            conn.close()


def validate_new_question(
    topic_id: int,
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct_option: str,
    explanation: str = "",
    difficulty: str = "Easy",
    exclude_question_id: Optional[int] = None,
    conn=None
) -> None:
    """
    Validates question inputs and verifies uniqueness against the existing question bank.
    Raises ValueError with descriptive reason if invalid or duplicate.
    """
    if not question_text or not question_text.strip():
        raise ValueError("Question text cannot be empty.")

    if not all([option_a, option_b, option_c, option_d]):
        raise ValueError("All four options (A, B, C, D) must be provided.")

    clean_correct = correct_option.strip().upper() if correct_option else ""
    if clean_correct not in ["A", "B", "C", "D"]:
        raise ValueError(f"Correct option must be one of A, B, C, or D (got: '{correct_option}').")

    if difficulty not in ["Easy", "Medium", "Hard"]:
        raise ValueError(f"Difficulty must be Easy, Medium, or Hard (got: '{difficulty}').")

    # Check for duplicate question in question bank
    existing_dup = find_duplicate_question(question_text, exclude_question_id=exclude_question_id, conn=conn)
    if existing_dup:
        raise ValueError(
            f"Duplicate question detected: An equivalent question already exists in the question bank "
            f"(Question ID: {existing_dup['question_id']} under Topic: '{existing_dup['topic_name']}'). "
            f"Stored Text: '{existing_dup['question_text']}'"
        )


def add_question(
    topic_id: int,
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct_option: str,
    explanation: str = "",
    difficulty: str = "Easy",
    quiz_id: Optional[int] = None,
    conn=None
) -> int:
    """
    Validates and inserts a new unique question into the question bank.
    Optionally links it to a quiz in quiz_questions.
    Returns the newly created question_id.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        # Validate uniqueness and formatting
        validate_new_question(
            topic_id=topic_id,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option,
            explanation=explanation,
            difficulty=difficulty,
            conn=conn
        )

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING question_id
            """,
            (
                topic_id,
                question_text.strip(),
                option_a.strip(),
                option_b.strip(),
                option_c.strip(),
                option_d.strip(),
                correct_option.strip().upper(),
                explanation.strip() if explanation else "",
                difficulty
            )
        )
        new_question_id = cur.fetchone()[0]

        # Link to quiz if quiz_id is provided
        if quiz_id:
            cur.execute(
                """
                INSERT INTO quiz_questions (quiz_id, question_id)
                VALUES (%s, %s)
                ON CONFLICT (quiz_id, question_id) DO NOTHING
                """,
                (quiz_id, new_question_id)
            )

        conn.commit()
        return new_question_id
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()


def get_quiz_question_counts(conn=None) -> List[Dict[str, Any]]:
    """
    Inspects all quizzes in the Existing Quiz section and returns their unique question counts.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                q.quiz_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                q.difficulty,
                COUNT(DISTINCT qq.question_id) AS unique_questions
            FROM quizzes q
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            LEFT JOIN quiz_questions qq ON q.quiz_id = qq.quiz_id
            WHERE q.quiz_type = 'Existing'
            GROUP BY q.quiz_id, q.quiz_title, s.subject_name, t.topic_name, q.difficulty
            ORDER BY q.quiz_id
            """
        )
        rows = cur.fetchall()
        return [
            {
                "quiz_id": r[0],
                "quiz_title": r[1],
                "subject_name": r[2],
                "topic_name": r[3],
                "difficulty": r[4],
                "unique_questions": r[5]
            }
            for r in rows
        ]
    finally:
        if close_conn:
            conn.close()
