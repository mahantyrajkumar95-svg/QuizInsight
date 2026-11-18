"""
Migration Script: Add selected_question_ids JSONB column to quiz_attempts table in PostgreSQL.
Enables dynamic 10-question random sampling per quiz attempt while maintaining consistency across page refreshes.
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
        ALTER TABLE quiz_attempts 
        ADD COLUMN IF NOT EXISTS selected_question_ids JSONB;
        """)
        conn.commit()
        print("Migration successful: selected_question_ids column added to quiz_attempts.")
    except Exception as e:
        conn.rollback()
        print(f"Migration error: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    apply_migration()
