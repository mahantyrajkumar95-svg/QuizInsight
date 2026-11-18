
import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Load .env from the project root
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "quizinsight"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "prefer")
    )
