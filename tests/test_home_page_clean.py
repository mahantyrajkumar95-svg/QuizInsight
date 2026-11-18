"""
Test Home Page hero section layout and verify Deep Performance Insights card is removed.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

def test_home_page_rendering():
    client = app.test_client()
    
    # Test logged out view
    response_anon = client.get('/')
    assert response_anon.status_code == 200, f"Expected 200, got {response_anon.status_code}"
    html_anon = response_anon.get_data(as_text=True)
    
    # Verify card is removed
    assert "Deep Performance Insights" not in html_anon, "Found 'Deep Performance Insights' in HTML!"
    assert "Beyond simple scores" not in html_anon, "Found 'Beyond simple scores' in HTML!"
    assert "Elapsed-Time Stopwatch" not in html_anon, "Found 'Elapsed-Time Stopwatch' in HTML!"
    assert "Weak Topic Detection identifies specific areas" not in html_anon, "Found weak topic detection card bullet in HTML!"
    assert "AI-Generated Quizzes create targeted practice" not in html_anon, "Found AI-Generated Quizzes card bullet in HTML!"
    assert "Knowledge Retention tracks long-term mastery" not in html_anon, "Found knowledge retention card bullet in HTML!"
    assert "Real-Time" not in html_anon, "Found 'Real-Time' badge in HTML!"
    
    # Verify retained hero elements
    assert "Learn Smarter with QuizInsight" in html_anon
    assert "An AI-Powered Online Quiz and Student Performance Analytics Platform." in html_anon
    assert "Practice quizzes, understand your performance, identify weak topics, and improve your knowledge through personalized recommendations." in html_anon
    assert "Get Started" in html_anon
    assert "Login" in html_anon
    assert 'col-lg-10 col-xl-9' in html_anon
    
    # Test logged in view
    with client.session_transaction() as sess:
        sess['student_id'] = 1
        sess['student_name'] = 'Alice'
        sess['student_email'] = 'alice@example.com'
    
    response_auth = client.get('/')
    assert response_auth.status_code == 200
    html_auth = response_auth.get_data(as_text=True)
    
    assert "Welcome back, <strong>Alice</strong>!" in html_auth
    assert "Go to Dashboard" in html_auth
    assert "Deep Performance Insights" not in html_auth

    print("ALL HOME PAGE TESTS PASSED!")

if __name__ == '__main__':
    test_home_page_rendering()
