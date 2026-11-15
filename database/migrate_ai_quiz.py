"""
Migration Script: Create ai_quiz_attempts table in PostgreSQL.
Separates AI-generated quizzes completely from the existing question bank (quizzes, questions, quiz_questions).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import get_db_connection

def apply_migration():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_quiz_attempts (
            ai_attempt_id SERIAL PRIMARY KEY,
            student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
            topic VARCHAR(200) NOT NULL,
            difficulty VARCHAR(20) NOT NULL,
            num_questions INT NOT NULL,
            questions_data JSONB NOT NULL,
            student_answers JSONB DEFAULT '{}'::jsonb,
            score NUMERIC(5,2) DEFAULT 0.00,
            accuracy NUMERIC(5,2) DEFAULT 0.00,
            correct_answers INT DEFAULT 0,
            total_questions INT NOT NULL,
            time_taken_seconds INT DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_ai_quiz_attempts_student ON ai_quiz_attempts(student_id);
        CREATE INDEX IF NOT EXISTS idx_ai_quiz_attempts_submitted ON ai_quiz_attempts(submitted_at);
        """)
        conn.commit()
        print("Migration successful: ai_quiz_attempts table created.")
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    apply_migration()
