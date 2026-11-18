-- ====================================================================
-- QuizInsight – AI-Powered Online Quiz & Student Performance Analytics
-- Database: PostgreSQL 18
-- Schema Definition & Performance Indexes
-- ====================================================================
--
-- RELATIONSHIP ARCHITECTURE:
-- 
--   students
--     ├── quiz_attempts
--     │     ├── student_answers ────> questions ────> topics ────> subjects
--     │     │                                          ▲              ▲
--     │     └── retention_schedules (followup)         │              │
--     │                                                │              │
--     ├── practice_recommendations ────────────────────┴──────────────┘
--     └── retention_schedules (initial) ───────> quizzes 
--
-- ====================================================================

-- 1. Students Table
-- Stores student profile and authentication credentials.
CREATE TABLE IF NOT EXISTS students (
    student_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Subjects Table
-- Academic domains (e.g. 'Python', 'Mathematics').
CREATE TABLE IF NOT EXISTS subjects (
    subject_id SERIAL PRIMARY KEY,
    subject_name VARCHAR(100) NOT NULL UNIQUE
);

-- 3. Topics Table
-- Granular academic curriculum topics within subjects.
CREATE TABLE IF NOT EXISTS topics (
    topic_id SERIAL PRIMARY KEY,
    subject_id INT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    topic_name VARCHAR(100) NOT NULL
);

-- 4. Quizzes Table
-- Test instances (both curriculum 'Existing' and dynamic 'AI-Generated').
CREATE TABLE IF NOT EXISTS quizzes (
    quiz_id SERIAL PRIMARY KEY,
    subject_id INT NOT NULL REFERENCES subjects(subject_id) ON DELETE CASCADE,
    topic_id INT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    quiz_title VARCHAR(150) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    quiz_type VARCHAR(20) NOT NULL DEFAULT 'Existing', -- 'Existing' or 'AI-Generated'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Questions Table
-- Multiple choice questions with 4 options and answer explanation.
CREATE TABLE IF NOT EXISTS questions (
    question_id SERIAL PRIMARY KEY,
    topic_id INT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option CHAR(1) NOT NULL,
    explanation TEXT,
    difficulty VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Quiz Questions Mapping Table
-- Many-to-many relationship mapping questions to specific quizzes.
CREATE TABLE IF NOT EXISTS quiz_questions (
    quiz_id INT NOT NULL REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    question_id INT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    PRIMARY KEY (quiz_id, question_id)
);

-- 7. Quiz Attempts Table
-- Student quiz test attempts with stopwatch elapsed duration and metrics.
CREATE TABLE IF NOT EXISTS quiz_attempts (
    attempt_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    quiz_id INT NOT NULL REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    total_questions INT DEFAULT 0,
    correct_answers INT DEFAULT 0,
    score NUMERIC(5,2) DEFAULT 0.00,
    accuracy NUMERIC(5,2) DEFAULT 0.00,
    time_taken_seconds INT DEFAULT 0,
    selected_question_ids JSONB
);

-- 8. Student Answers Table
-- Records every selected answer per question within an attempt for weak-topic diagnostics.
CREATE TABLE IF NOT EXISTS student_answers (
    answer_id SERIAL PRIMARY KEY,
    attempt_id INT NOT NULL REFERENCES quiz_attempts(attempt_id) ON DELETE CASCADE,
    question_id INT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
    selected_option CHAR(1) NOT NULL,
    is_correct BOOLEAN NOT NULL
);

-- 9. Practice Recommendations Table
-- Stores personalized AI-driven practice recommendations prioritized by mastery gaps.
CREATE TABLE IF NOT EXISTS practice_recommendations (
    recommendation_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    topic_id INT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    quiz_id INT REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'Medium', -- 'High', 'Medium', 'Low'
    status VARCHAR(20) DEFAULT 'Active',    -- 'Active', 'Completed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. Retention Schedules Table
-- Spaced repetition schedules (7-day intervals) measuring long-term memory retention.
CREATE TABLE IF NOT EXISTS retention_schedules (
    schedule_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    initial_attempt_id INT NOT NULL REFERENCES quiz_attempts(attempt_id) ON DELETE CASCADE,
    quiz_id INT NOT NULL REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    scheduled_for TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending',   -- 'Pending', 'Completed'
    followup_attempt_id INT REFERENCES quiz_attempts(attempt_id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. AI Quiz Attempts Table
-- Completely decoupled storage for dynamic AI quizzes on any student-entered topic.
-- Questions are stored as a JSON snapshot without contaminating curriculum question banks.
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

-- ====================================================================
-- PERFORMANCE INDEXES
-- Optimized for high-throughput queries across student dashboards,
-- performance trend analysis, weak topic detection, and retention schedules.
-- ====================================================================

CREATE INDEX IF NOT EXISTS idx_topics_subject ON topics(subject_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_subject ON quizzes(subject_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_topic ON quizzes(topic_id);
CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_student ON quiz_attempts(student_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS idx_student_answers_attempt ON student_answers(attempt_id);
CREATE INDEX IF NOT EXISTS idx_student_answers_question ON student_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_practice_recs_student ON practice_recommendations(student_id);
CREATE INDEX IF NOT EXISTS idx_retention_schedules_student ON retention_schedules(student_id);
CREATE INDEX IF NOT EXISTS idx_retention_schedules_quiz ON retention_schedules(quiz_id);
CREATE INDEX IF NOT EXISTS idx_ai_quiz_attempts_student ON ai_quiz_attempts(student_id);
CREATE INDEX IF NOT EXISTS idx_ai_quiz_attempts_submitted ON ai_quiz_attempts(submitted_at);

-- Question Bank Uniqueness (Enforces zero duplicates across all formatting/spacing/capitalization)
CREATE OR REPLACE FUNCTION normalize_question_text(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN lower(regexp_replace(regexp_replace(trim(input_text), '[^a-zA-Z0-9]+', ' ', 'g'), '\s+', ' ', 'g'));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_normalized_unique 
ON questions (normalize_question_text(question_text));
