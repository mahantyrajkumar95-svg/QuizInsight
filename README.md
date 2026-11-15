# QuizInsight – AI-Powered Online Quiz & Student Performance Analytics System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analytics-150458.svg?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3.svg?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**QuizInsight** is a production-grade, full-stack educational web application designed to move beyond traditional quiz scores (such as simply showing "7/10") by providing students with **deep, actionable academic diagnostics**. 

Powered by **Flask**, **PostgreSQL 18**, **Pandas**, **NumPy**, **Matplotlib**, and external **AI Large Language Models (LLMs)**, QuizInsight automatically evaluates learning trends, tracks pacing, pinpoints conceptual weak spots, generates personalized practice recommendations, and schedules 7-day spaced repetition retests to combat the forgetting curve.

---

## Table of Contents

1. [Key Features & Capabilities](#key-features--capabilities)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Database Schema & Architecture](#database-schema--architecture)
5. [Prerequisites & System Requirements](#prerequisites--system-requirements)
6. [Step-by-Step Installation & Setup Guide](#step-by-step-installation--setup-guide)
7. [Environment Configuration (`.env`)](#environment-configuration-env)
8. [Database Initialization & Seeding](#database-initialization--seeding)
9. [Running the Application](#running-the-application)
10. [Automated Testing Suite](#automated-testing-suite)
11. [Project Directory Structure](#project-directory-structure)
12. [Security & Data Protection](#security--data-protection)

---

## Key Features & Capabilities

### 1. Modern Landing Page & Authentication
- **Engaging Landing Interface**: Highlights system capabilities, core analytics features, and 6-step study workflow.
- **Secure Authentication**: Student registration and login protected with Werkzeug cryptographic hashing (`scrypt` / `pbkdf2`), duplicate checks, and secure session management.

### 2. Dynamic Student Dashboard
- **Live Statistical KPIs**: Displays Total Completed Attempts, Overall Average Score, Latest Score, Accuracy Rate, and Performance Trend indicator.
- **Quick-Start Quiz Browser**: Instant access to popular curriculum quizzes with difficulty badges.
- **Recent Attempt Feed & Retention Radar**: Real-time snapshot of recent test results and upcoming retention schedules.

### 3. Curriculum Browsing & Multi-Parameter Filtering
- **Subject & Topic Explorer**: Dynamic topic loading via asynchronous JSON APIs (`/api/topics/<id>`).
- **Granular Filter Controls**: Multi-parameter filtering by Subject, Topic, and Difficulty (Easy, Medium, Hard).

### 4. AI-Powered Quiz Generation
- **Dynamic Question Synthesis**: Generates unique multiple-choice quizzes on-demand using external LLMs (Google Gemini, OpenAI, Groq).
- **Curriculum Fallback Engine**: Guarantees uninterrupted operation even if external AI services are offline or unconfigured.
- **Strict Format & Schema Validation**: Ensures every question contains exactly 4 distinct options, an unambiguous correct answer key, and an educational explanation.

### 5. Visible Elapsed-Time Stopwatch (Live Timer)
- **True Elapsed-Time Stopwatch**: Formatted as `00:00 → 00:01 → 00:02...` measuring exact attempt duration.
- **Database Synchronization**: Synchronized with PostgreSQL `started_at` timestamps—**never resets on browser refresh**.
- **Interactive Question Progress**: Live counter tracking answered questions in real-time.

### 6. Automated Scoring & Diagnostic Explanations
- **Instant Result Evaluation**: Computes percentage scores, accuracy metrics, and elapsed time upon submission.
- **Detailed Question Review**: Highlights selected answers, correct keys, and in-depth rationales for every question.
- **Navigation Shortcuts**: One-click actions to retake quizzes, review history, view analytics, or return to the dashboard.

### 7. Performance Trend Analysis (Data Science Engine)
- **Pandas & NumPy Analytics**: Computes score progression trajectories using linear regression (`np.polyfit`).
- **Trajectory Classification**: Categorizes student performance as **Improving**, **Declining**, or **Stable**.
- **Dynamic Matplotlib Visualizations**: High-resolution charts dynamically generated in memory and embedded as base64 images without cluttering the disk.

### 8. Time-Based Pacing & Question Speed Breakdown
- **Efficiency Metrics**: Measures Total Time Taken, Average Completion Time, Fastest Attempt, and Slowest Attempt.
- **Pacing Correlation**: Subplot scatter plot mapping Time Taken vs. Score Achieved with regression trendlines.

### 9. Weak Topic Detection & Academic Diagnostics
- **Topic Accuracy Formula**:
  $$\text{Topic Accuracy} = \left(\frac{\text{Correct Answers in Topic}}{\text{Total Questions Answered in Topic}}\right) \times 100$$
- **Standardized Mastery Tiers**:
  - **Strong Mastery**: $\ge 80\%$ (Emerald Green)
  - **Good Understanding**: $60\% - 79\%$ (Primary Blue)
  - **Needs Practice**: $40\% - 59\%$ (Amber Orange)
  - **Weak Topic**: $< 40\%$ (Coral Red)
- **Color-Coded Horizontal Bar Chart**: Visualizes topic strengths and conceptual gaps sorted from weakest to strongest.

### 10. Personalized Practice Recommendations
- **Targeted Study Plan**: Automatically recommends high-priority quizzes for topics performing below the 60% proficiency threshold.
- **Diagnostic Insights**: Explains *why* each topic was recommended with exact accuracy statistics.
- **Dual Practice Options**: Directly launch an existing curriculum quiz or generate a targeted AI quiz with pre-selected topic parameters.
- **Database Persistence**: Synchronizes recommendations with the PostgreSQL `practice_recommendations` table.

### 11. Knowledge Retention & Spaced Repetition System
- **Combat the Forgetting Curve**: Automatically schedules a follow-up retest 7 days after completing a quiz.
- **Retention Delta Formula**:
  $$\text{Retention Delta } (\Delta) = \text{Follow-up Score} - \text{Initial Score}$$
- **Memory Classification**:
  - **Knowledge Improved**: $\Delta > 0\%$
  - **Knowledge Retained**: $\Delta = 0\%$
  - **Slight Decay**: $-10\% \le \Delta < 0\%$
  - **Significant Decay**: $\Delta < -10\%$
- **Performance Comparison Table**: Side-by-side comparison of Initial vs. Follow-up scores, elapsed days, and retention badges.

---

## System Architecture

```
                      +---------------------------------------+
                      |       Student Web Browser (UI)        |
                      | Bootstrap 5, Jinja2, Responsive Views |
                      +-------------------+-------------------+
                                          |
                                HTTP Requests / JSON
                                          v
                      +---------------------------------------+
                      |         Flask Web Application         |
                      |   Routes, Sessions, Auth & Controls   |
                      +---------+-------------------+---------+
                                |                   |
        +-----------------------+                   +-----------------------+
        |                                                                   |
        v                                                                   v
+-------------------------------+                               +-------------------------------+
|     Analytics & ML Engine     |                               |      AI Quiz Generator        |
|  - Pandas: Dataframes & Trends|                               |  - Google Gemini / OpenAI     |
|  - NumPy: Polyfit Regression  |                               |  - Curriculum Fallback Engine |
|  - Matplotlib: Base64 Visuals |                               |  - Strict JSON Validation     |
+---------------+---------------+                               +---------------+---------------+
                |                                                               |
                +-----------------------+---------------------------------------+
                                        |
                                        v
                      +---------------------------------------+
                      |         PostgreSQL 18 Database        |
                      |  10 Relational Tables, 11 Fast Indexes|
                      +---------------------------------------+
```

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons, Jinja2 |
| **Backend** | Python 3.10+, Flask 3.x, Werkzeug (Security), python-dotenv |
| **Database** | PostgreSQL 18, `psycopg2-binary` (Connection Pooling) |
| **Data Analytics** | Pandas, NumPy, Matplotlib (`Agg` Headless Renderer) |
| **AI Integration** | REST APIs (`requests`) for Google Gemini, OpenAI, or Groq |
| **Testing** | Standard Python `unittest` / `test_client`, custom E2E automation |

---

## Database Schema & Architecture

The database schema is fully normalized and enforced with Foreign Keys, Cascading Deletions, and 11 Performance Indexes.

```
  students
    ├── quiz_attempts
    │     ├── student_answers ────> questions ────> topics ────> subjects
    │     │                                          ▲              ▲
    │     └── retention_schedules (followup)         │              │
    │                                                │              │
    ├── practice_recommendations ────────────────────┴──────────────┘
    └── retention_schedules (initial) ───────> quizzes 
```

### Table Summary (10 Tables)

1. `students`: Stores student account credentials with cryptographic password hashes.
2. `subjects`: High-level academic disciplines (e.g. *Python*, *Mathematics*).
3. `topics`: Granular curriculum units within subjects (e.g. *Loops*, *Variables*, *Algebra*).
4. `quizzes`: Quiz metadata, difficulty ratings, and quiz type (`Existing` or `AI-Generated`).
5. `questions`: Multiple-choice questions, options A–D, correct answer key, and explanations.
6. `quiz_questions`: M:N junction table mapping questions to specific quizzes.
7. `quiz_attempts`: Attempt records with start/submission timestamps, score, accuracy, and elapsed stopwatch seconds.
8. `student_answers`: Question-by-question choices and correctness flags for diagnostic analysis.
9. `practice_recommendations`: Personalized recommendations categorized by priority (`High`, `Medium`, `Low`).
10. `retention_schedules`: 7-day spaced repetition schedules tracking initial vs. follow-up retests.

---

## Prerequisites & System Requirements

Ensure the following software is installed on your computer:

- **Python**: Version `3.10` or higher ([Download Python](https://www.python.org/downloads/))
- **PostgreSQL**: Version `18` (or `14+`) running locally ([Download PostgreSQL](https://www.postgresql.org/download/))
- **Git**: (Optional, for version control)

---

## Step-by-Step Installation & Setup Guide

### 1. Open the Project Folder
Open your terminal (PowerShell on Windows, or Bash on macOS/Linux) and navigate to the project root:

```bash
cd "C:\Users\rajku\OneDrive\Desktop\coding\QuizInsight"
```

### 2. Set Up Python Virtual Environment

```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment:
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
.\venv\Scripts\activate.bat

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Required Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Environment Configuration (`.env`)

Create a `.env` file in the root project folder (or update the existing one) with your database credentials:

```env
# Flask Application Secret Key
SECRET_KEY=your_secure_random_flask_secret_key_here

# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=quizinsight
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here

# Optional: External AI Service Credentials (for AI Quiz Generation)
# The application automatically uses verified curriculum fallback if left blank
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

> **Security Note**: Never commit your `.env` file to public repositories.

---

## Database Initialization & Seeding

### 1. Create the Database
In PostgreSQL, create the `quizinsight` database:

```sql
CREATE DATABASE quizinsight;
```

### 2. Apply Schema & Performance Indexes
Execute [`database/schema.sql`](database/schema.sql) using `psql` or pgAdmin:

```bash
psql -U postgres -d quizinsight -f database/schema.sql
```

### 3. Seed Curriculum Topics & Questions
Execute [`database/seed_topics_data.sql`](database/seed_topics_data.sql) to populate subjects (*Python*, *Mathematics*), topics, questions, and baseline quizzes:

```bash
psql -U postgres -d quizinsight -f database/seed_topics_data.sql
```

---

## Running the Application

Ensure your virtual environment is active, then launch the Flask server:

```bash
python app.py
```

Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## Automated Testing Suite

QuizInsight includes a comprehensive verification suite with unit, integration, and master end-to-end (E2E) tests.

### 1. Run the Master End-to-End Workflow Test
Simulates the entire student lifecycle (Registration $\to$ Login $\to$ AI Quiz $\to$ Stopwatch Attempt $\to$ Result $\to$ Analytics $\to$ Recommendations $\to$ Retention Retest $\to$ Logout $\to$ Cleanup):

```bash
python tests/test_e2e_workflow.py
```

### 2. Run the Full Regression Suite Across All Phases
Executes all phase-by-phase test suites (Phases 2 through 19):

```bash
python scratch/run_all_tests.py
```

All tests execute non-destructively against the database and clean up temporary test records upon completion.

---

## Project Directory Structure

```text
QuizInsight/
│
├── analytics/                      # Data Analytics & Machine Learning Modules
│   ├── performance.py              # Performance Trend & Time-Based Analysis (Pandas, Matplotlib)
│   ├── recommendations.py          # Personalized Practice Recommendation Engine
│   └── retention.py                # Spaced Repetition & Retention Delta Tracking
│
├── database/                       # Database DDL & Seeds
│   ├── schema.sql                  # Complete PostgreSQL 18 Schema & 11 Performance Indexes
│   └── seed_topics_data.sql        # Starter Curriculum Data (Python, Mathematics, Questions)
│
├── frontend/                       # Frontend Presentation Layer
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css           # Global Theme, Components & Custom Styling
│   │   └── js/
│   │       └── stopwatch.js        # Elapsed-Time Stopwatch (Resilient to Refresh)
│   └── templates/                  # Jinja2 HTML5 Templates
│       ├── ai_quiz.html            # AI Quiz Generation Interface
│       ├── analytics.html          # Performance, Pacing & Weak Topic Analytics Dashboard
│       ├── dashboard.html          # Dynamic Student Dashboard Hub
│       ├── history.html            # Quiz History & Aggregate Records
│       ├── index.html              # Landing / Home Page
│       ├── login.html              # Authentication: Student Login
│       ├── quiz.html               # Live Quiz Runner with Sticky Stopwatch
│       ├── quiz_selection.html     # Subject & Topic Filter Browser
│       ├── recommendations.html    # Personalized Practice Recommendations View
│       ├── register.html           # Authentication: Student Registration
│       ├── result.html             # Detailed Quiz Result Review & Explanations
│       └── retention.html          # Knowledge Retention & Spaced Repetition Retesting
│
├── modules/                        # External AI & Core Service Integrations
│   └── ai_generator.py             # LLM API Client (Gemini, OpenAI, Groq) with Fallback
│
├── tests/                          # Automated Integration Test Suite
│   └── test_e2e_workflow.py        # Master End-to-End System Test (16 Stages)
│
├── app.py                          # Flask Application Entry Point & Route Controllers
├── config.py                       # PostgreSQL Database Connection Handler
├── requirements.txt                # Python Dependencies
├── .env                            # Environment Configuration (Credentials)
└── README.md                       # Comprehensive System Documentation
```

---

## Security & Data Protection

- **Password Encryption**: Implemented using Werkzeug's adaptive cryptographic key-derivation algorithms (`scrypt` / `pbkdf2`).
- **SQL Injection Prevention**: 100% of database queries utilize parameterized queries (`%s`). Zero raw string interpolation.
- **Route Authorization**: All authenticated endpoints are protected with custom `@login_required` decorators.
- **IDOR / Privilege Escalation Defense**: Strict checks ensure students can only view and modify their own test attempts, recommendations, and schedules.
- **Cross-Site Scripting (XSS) Protection**: Jinja2 contextual autoescaping active on all user-supplied data.

---

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
