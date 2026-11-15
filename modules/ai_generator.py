"""
AI Quiz Generation Module
Generates multiple-choice quiz questions using external LLM APIs (Gemini, OpenAI, or Groq)
with strict JSON validation, schema verification, and informative diagnostic errors.

Important Architectural Rule:
AI-generated quizzes are NOT inserted into the existing quiz-bank tables (quizzes, questions, quiz_questions).
Storage is handled exclusively in the separate ai_quiz_attempts table.
"""

import json
import os
import re
import requests
import time

from pathlib import Path
from dotenv import load_dotenv

# Load .env from the main project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=True)
print("AI MODULE LOADED")
print("ENV FILE EXISTS:", ENV_FILE.exists())
print("GEMINI KEY DETECTED:", bool(os.getenv("GEMINI_API_KEY")))


class AIGenerationError(Exception):
    """Custom exception raised when AI question generation fails."""
    pass


def validate_questions(questions_data, difficulty="Easy"):
    """
    Validates that the AI-generated questions conform strictly to the required schema:
    - question_text: non-empty string
    - option_a, option_b, option_c, option_d: non-empty strings
    - correct_option: exactly 'A', 'B', 'C', or 'D'
    - explanation: helpful non-empty rationale
    """
    if not isinstance(questions_data, list) or len(questions_data) == 0:
        return []

    validated = []
    for idx, item in enumerate(questions_data, start=1):
        if not isinstance(item, dict):
            continue

        q_text = str(item.get("question_text", "")).strip()
        opt_a = str(item.get("option_a", "")).strip()
        opt_b = str(item.get("option_b", "")).strip()
        opt_c = str(item.get("option_c", "")).strip()
        opt_d = str(item.get("option_d", "")).strip()
        correct = str(item.get("correct_option", "")).strip().upper()
        explanation = str(item.get("explanation", "")).strip()

        # Check required fields and valid answer key
        if not q_text or not opt_a or not opt_b or not opt_c or not opt_d:
            continue
        if correct not in ["A", "B", "C", "D"]:
            continue
        if not explanation:
            explanation = f"Option {correct} is the verified correct answer for this question."

        validated.append({
            "question_id": idx,
            "question_text": q_text,
            "option_a": opt_a,
            "option_b": opt_b,
            "option_c": opt_c,
            "option_d": opt_d,
            "correct_option": correct,
            "explanation": explanation,
            "difficulty": difficulty
        })

    return validated


def _call_gemini_api(api_key, topic, difficulty, num_questions):
    """Call Google Gemini Generative Language API."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
    prompt = f"""You are an expert academic examiner. Generate exactly {num_questions} multiple-choice questions on the topic: "{topic}".
Difficulty Level: {difficulty}

Requirements:
- Each question must be technically accurate, educational, and relevant to "{topic}".
- 4 distinct options: option_a, option_b, option_c, option_d.
- Exactly one correct answer: correct_option (A, B, C, or D).
- Provide a clear diagnostic explanation explaining why that option is correct.
- Return ONLY a valid JSON array of objects with no markdown code fencing or introductory text.

JSON Schema:
[
  {{
    "question_text": "Question statement here?",
    "option_a": "First option",
    "option_b": "Second option",
    "option_c": "Third option",
    "option_d": "Fourth option",
    "correct_option": "A",
    "explanation": "Clear explanation why option A is correct."
  }}
]"""

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "responseMimeType": "application/json"
        }
    }

# Retry Gemini requests when the server is temporarily unavailable
    max_retries = 3

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key
                },
                json=payload,
                timeout=25
            )

            if resp.status_code in [503, 502, 504] and attempt < max_retries:
                wait_time = 2 ** (attempt + 1)
                print(f"Gemini server busy. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            resp.raise_for_status()
            break

        except requests.exceptions.RequestException:
            if attempt == max_retries:
                raise

            wait_time = 2 ** (attempt + 1)
            print(f"Gemini request failed. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    data = resp.json()
    candidates = data.get("candidates", [])

    if not candidates:
        raise AIGenerationError("Gemini API returned an empty candidate list.")

    text = candidates[0]["content"]["parts"][0]["text"].strip()
    return json.loads(text)


def _call_openai_or_groq_api(api_key, base_url, model, topic, difficulty, num_questions):
    """Call OpenAI or Groq compatible Chat Completion API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "You are an expert educator. Generate academic multiple-choice questions strictly formatted as a raw JSON array. "
        "Each object must have 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option' (A, B, C, or D), and 'explanation'."
    )
    user_prompt = (
        f"Generate exactly {num_questions} {difficulty}-difficulty multiple-choice questions on the educational topic: '{topic}'."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3
    }

    resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=25)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise AIGenerationError("API returned no response choices.")
    content = choices[0]["message"]["content"].strip()

    if content.startswith("```"):
        content = re.sub(r"^```[a-zA-Z]*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    return json.loads(content)


def _generate_mock_questions(topic, difficulty, num_questions):
    """
    Topic-aware generator for automated testing or offline mock testing mode.
    Used when MOCK_AI=True or during testing to avoid external network dependency.
    """
    questions = []
    for i in range(1, num_questions + 1):
        questions.append({
            "question_text": f"In {topic}, which of the following is a key fundamental principle for {difficulty.lower()} applications (Item {i})?",
            "option_a": f"Ensuring proper architecture, semantic consistency, and correctness for {topic}",
            "option_b": f"Ignoring standard error handling and edge cases",
            "option_c": f"Using deprecated global mutable state without thread safety",
            "option_d": f"Bypassing all input verification and security protocols",
            "correct_option": "A",
            "explanation": f"In {topic}, sound architectural consistency and validation are essential to reliable execution."
        })
    return validate_questions(questions, difficulty=difficulty)


def generate_ai_questions(topic, difficulty="Medium", num_questions=5, allow_mock_fallback=False):
    print("DEBUG: generate_ai_questions() FUNCTION CALLED")
    """
    Attempts to generate questions for any student-entered educational topic.
    Validates the generated questions.
    If generation fails or no API key is configured, raises AIGenerationError with a helpful message.
    """
    topic = str(topic).strip()
    if not topic:
        raise AIGenerationError("Topic cannot be empty. Please enter an educational topic.")

    difficulty = difficulty.strip().capitalize()
    if difficulty not in ["Easy", "Medium", "Hard"]:
        difficulty = "Medium"

    try:
        num_questions = int(num_questions)
        num_questions = max(1, min(20, num_questions))
    except (ValueError, TypeError):
        num_questions = 5

    # Check for test/mock mode
    if os.getenv("MOCK_AI", "").lower() in ["1", "true", "yes"] or allow_mock_fallback:
        mock_qs = _generate_mock_questions(topic, difficulty, num_questions)
        return mock_qs, "Simulated AI (Test Mode)"


    load_dotenv(dotenv_path=ENV_FILE, override=True)

    print("DEBUG ENV PATH:", ENV_FILE)
    print("DEBUG GEMINI KEY FOUND:", bool(os.getenv("GEMINI_API_KEY")))

    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    print("DEBUG - Gemini key loaded:", bool(gemini_key))
    print("DEBUG - OpenAI key loaded:", bool(openai_key))
    print("DEBUG - Groq key loaded:", bool(groq_key)) 

    if not gemini_key and not openai_key and not groq_key:
        raise AIGenerationError(
            "No AI API key found. Please configure GEMINI_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY "
            "in your .env file to enable live AI quiz generation."
        )

    last_error = None

    # 1. Try Gemini
    if gemini_key:
        try:
            raw = _call_gemini_api(gemini_key, topic, difficulty, num_questions)
            validated = validate_questions(raw, difficulty=difficulty)
            if validated:
                return validated[:num_questions], "Google Gemini (gemini-3.5-flash-lite)"
            else:
                last_error = "Gemini API returned questions that did not match the required schema."
        except Exception as e:
            last_error = f"Gemini API error: {str(e)}"

    # 2. Try OpenAI
    if openai_key:
        try:
            raw = _call_openai_or_groq_api(openai_key, "https://api.openai.com/v1", "gpt-4o-mini", topic, difficulty, num_questions)
            validated = validate_questions(raw, difficulty=difficulty)
            if validated:
                return validated[:num_questions], "OpenAI (gpt-4o-mini)"
            else:
                last_error = "OpenAI API returned questions that did not match the required schema."
        except Exception as e:
            last_error = f"OpenAI API error: {str(e)}"

    # 3. Try Groq
    if groq_key:
        try:
            raw = _call_openai_or_groq_api(groq_key, "https://api.groq.com/openai/v1", "llama-3.1-8b-instant", topic, difficulty, num_questions)
            validated = validate_questions(raw, difficulty=difficulty)
            if validated:
                return validated[:num_questions], "Groq (Llama 3.1)"
            else:
                last_error = "Groq API returned questions that did not match the required schema."
        except Exception as e:
            last_error = f"Groq API error: {str(e)}"

    raise AIGenerationError(
        f"AI Quiz Generation failed: {last_error or 'Unable to generate questions from configured AI provider.'}"
    )
