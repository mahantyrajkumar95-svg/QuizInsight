/**
 * QuizInsight - Universal Elapsed-Time Stopwatch
 * Count-up format: 00:00 -> 00:01 -> 00:02 ...
 * Synchronizes with individual attempt lifecycle.
 * Resilient against page refreshes; prevents duplicate timer intervals.
 */

document.addEventListener('DOMContentLoaded', function () {
    const timerElement = document.getElementById('stopwatchDisplay');
    if (!timerElement) return;

    // Clear any previous interval to prevent duplicate or accelerated ticking
    if (window._quizInsightTimerInterval) {
        clearInterval(window._quizInsightTimerInterval);
        window._quizInsightTimerInterval = null;
    }

    // Attempt identifier (e.g. existing_12 or ai_5)
    const attemptId = timerElement.getAttribute('data-attempt-id') || 'default';
    const storageKey = 'quizinsight_timer_start_' + attemptId;

    // Initial server elapsed seconds (0 for fresh attempts)
    let initialElapsed = parseInt(timerElement.getAttribute('data-initial-elapsed') || '0', 10);
    if (isNaN(initialElapsed) || initialElapsed < 0) {
        initialElapsed = 0;
    }

    let startTimeMs = null;
    try {
        const savedStart = sessionStorage.getItem(storageKey);
        if (savedStart) {
            const parsed = parseInt(savedStart, 10);
            if (!isNaN(parsed) && parsed > 0 && parsed <= Date.now() && (Date.now() - parsed) < 86400000) {
                startTimeMs = parsed;
            }
        }
    } catch (e) {
        // Fallback if sessionStorage is disabled
    }

    // If no active session start time exists, initialize from server elapsed
    if (!startTimeMs) {
        startTimeMs = Date.now() - (initialElapsed * 1000);
        try {
            sessionStorage.setItem(storageKey, String(startTimeMs));
        } catch (e) {}
    }

    function formatTime(totalSeconds) {
        const s = Math.max(0, Math.floor(totalSeconds));
        const hours = Math.floor(s / 3600);
        const minutes = Math.floor((s % 3600) / 60);
        const seconds = s % 60;

        const mm = String(minutes).padStart(2, '0');
        const ss = String(seconds).padStart(2, '0');

        if (hours > 0) {
            const hh = String(hours).padStart(2, '0');
            return `${hh}:${mm}:${ss}`;
        }
        return `${mm}:${ss}`;
    }

    function updateStopwatch() {
        const elapsedNow = Math.max(0, Math.floor((Date.now() - startTimeMs) / 1000));
        timerElement.textContent = formatTime(elapsedNow);
    }

    // Initialize display immediately
    updateStopwatch();

    // Tick every 1 second
    window._quizInsightTimerInterval = setInterval(updateStopwatch, 1000);

    // Form submission confirmation, immediate timer stop & duplicate click prevention
    const quizForm = document.getElementById('quizForm');
    if (quizForm) {
        quizForm.addEventListener('submit', function (e) {
            if (window._quizInsightTimerInterval) {
                clearInterval(window._quizInsightTimerInterval);
                window._quizInsightTimerInterval = null;
            }
            try {
                sessionStorage.removeItem(storageKey);
            } catch (err) {}

            const submitBtn = document.getElementById('submitQuizBtn');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Submitting Answers...';
            }
        });
    }

    // Answer tracker: count answered questions and update visual progress
    const radios = document.querySelectorAll('input[type="radio"]');
    const answeredCountEl = document.getElementById('answeredCount');
    const totalQuestions = parseInt(document.getElementById('totalQuestionsCount')?.textContent || '0', 10);

    function updateAnsweredCount() {
        const checkedQuestions = new Set();
        radios.forEach(r => {
            if (r.checked) {
                checkedQuestions.add(r.name);
            }
        });
        if (answeredCountEl) {
            answeredCountEl.textContent = checkedQuestions.size;
        }
    }

    radios.forEach(r => {
        r.addEventListener('change', updateAnsweredCount);
    });
    updateAnsweredCount();
});
