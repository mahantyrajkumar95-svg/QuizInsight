-- Seed script for additional topics: Conditional Statements, Loops, and Mathematics
-- Topics:
-- 3: Conditional Statements (Python)
-- 4: Loops (Python)
-- 7: Number System (Mathematics)
-- 8: Percentage (Mathematics)
-- 9: Profit and Loss (Mathematics)
-- 10: Algebra (Mathematics)

-- 1. Conditional Statements Questions (Python - Topic 3)
INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 3, 'Which keyword is used for conditional branching in Python?', 'if', 'switch', 'when', 'case', 'A', 'Python uses the "if" keyword for conditional branching.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'Which keyword is used for conditional branching in Python?');

INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 3, 'What is the correct syntax for an "else if" statement in Python?', 'else if', 'elseif', 'elif', 'elsif', 'C', '"elif" is the keyword used in Python for else if condition.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'What is the correct syntax for an "else if" statement in Python?');

INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 3, 'What will be the output of `if 0: print("Yes") else: print("No")`?', 'Yes', 'No', 'Error', 'None', 'B', 'In Python, 0 evaluates to falsy, so the else branch executes.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'What will be the output of `if 0: print("Yes") else: print("No")`?');

-- 2. Loops Questions (Python - Topic 4)
INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 4, 'Which statement terminates the loop entirely in Python?', 'continue', 'break', 'pass', 'stop', 'B', '"break" terminates the current loop immediately.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'Which statement terminates the loop entirely in Python?');

INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 4, 'What is the output of `range(1, 5)` when converted to a list?', '[1, 2, 3, 4, 5]', '[1, 2, 3, 4]', '[0, 1, 2, 3, 4]', '[2, 3, 4, 5]', 'B', 'range(start, stop) generates numbers up to stop - 1.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'What is the output of `range(1, 5)` when converted to a list?');

INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 4, 'Which keyword skips the rest of the current iteration and moves to the next?', 'break', 'skip', 'continue', 'pass', 'C', '"continue" skips the rest of the current iteration.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'Which keyword skips the rest of the current iteration and moves to the next?');

-- 3. Number System Questions (Mathematics - Topic 7)
INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 7, 'What is the smallest prime number?', '0', '1', '2', '3', 'C', '2 is the smallest and the only even prime number.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'What is the smallest prime number?');

INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 7, 'Which of the following is an irrational number?', '3.14', '22/7', '√2', '5', 'C', 'The square root of 2 cannot be written as a fraction of integers.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'Which of the following is an irrational number?');

-- 4. Percentage Questions (Mathematics - Topic 8)
INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 8, 'What is 25% of 200?', '25', '40', '50', '60', 'C', '25% of 200 = (25/100) * 200 = 50.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'What is 25% of 200?');

INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 8, 'If a price increases from $80 to $100, what is the percentage increase?', '20%', '25%', '30%', '15%', 'B', 'Increase = (20 / 80) * 100 = 25%.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'If a price increases from $80 to $100, what is the percentage increase?');

-- 5. Profit and Loss Questions (Mathematics - Topic 9)
INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 9, 'If Cost Price = $500 and Selling Price = $600, what is the profit?', '$50', '$100', '$150', '$200', 'B', 'Profit = Selling Price - Cost Price = 600 - 500 = $100.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'If Cost Price = $500 and Selling Price = $600, what is the profit?');

INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 9, 'Profit percentage is always calculated on which price?', 'Selling Price', 'Cost Price', 'Marked Price', 'Discounted Price', 'B', 'Profit percentage is calculated on Cost Price: (Profit / CP) * 100.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'Profit percentage is always calculated on which price?');

-- 6. Algebra Questions (Mathematics - Topic 10)
INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 10, 'What is the value of x if 2x + 6 = 14?', '2', '3', '4', '5', 'C', '2x = 14 - 6 = 8, so x = 4.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'What is the value of x if 2x + 6 = 14?');

INSERT INTO questions (topic_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, difficulty)
SELECT 10, 'What is the expansion of (a + b)^2?', 'a^2 + b^2', 'a^2 + 2ab + b^2', 'a^2 - 2ab + b^2', '2a + 2b', 'B', '(a + b)^2 = a^2 + 2ab + b^2.', 'Easy'
WHERE NOT EXISTS (SELECT 1 FROM questions WHERE question_text = 'What is the expansion of (a + b)^2?');
