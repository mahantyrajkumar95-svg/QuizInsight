"""
Migration Script: Deduplicate Question Bank & Seed Minimum 10 Unique Questions Per Quiz
QuizInsight Question Bank Overhaul
"""

import sys
import os
import re
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import get_db_connection
from modules.question_manager import normalize_question_text, add_question, find_duplicate_question

# ==============================================================================
# NEW HIGH-QUALITY UNIQUE QUESTIONS (10 PER QUIZ, 70 TOTAL)
# ==============================================================================

NEW_QUESTIONS_DATA = {
    # --------------------------------------------------------------------------
    # QUIZ 1: Python Basics - Easy Quiz (Subject: Python, Topic 1: Variables)
    # --------------------------------------------------------------------------
    1: [
        {
            "topic_id": 1,
            "question_text": "What function in Python returns the memory address of an object assigned to a variable?",
            "option_a": "address()",
            "option_b": "id()",
            "option_c": "memory()",
            "option_d": "loc()",
            "correct_option": "B",
            "explanation": "The id() function returns the unique identity (memory address in CPython) of the object bound to a variable.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "According to PEP 8 style guide, how should constant variables be named in Python?",
            "option_a": "camelCase",
            "option_b": "lowercase_with_underscores",
            "option_c": "ALL_CAPITAL_LETTERS",
            "option_d": "kebab-case",
            "correct_option": "C",
            "explanation": "PEP 8 specifies that constants should be written in all capital letters with underscores separating words (e.g., MAX_CONNECTIONS).",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "What will be the values of a and b after executing `a, b = 10, 20` followed by `a, b = b, a`?",
            "option_a": "a = 10, b = 20",
            "option_b": "a = 20, b = 10",
            "option_c": "a = 20, b = 20",
            "option_d": "a = 10, b = 10",
            "correct_option": "B",
            "explanation": "Python tuple packing and unpacking swaps variable values simultaneously without requiring an explicit temporary variable.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "What happens when you assign an integer to variable x and then assign a string to the same variable x?",
            "option_a": "A TypeError is raised immediately",
            "option_b": "Python automatically updates x to reference the new string object",
            "option_c": "The variable x is deleted",
            "option_d": "Python casts the string to an integer automatically",
            "correct_option": "B",
            "explanation": "Python is dynamically typed; variables are merely names bound to objects. Reassigning changes the reference to the new object.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "What exception is raised if you try to print a variable before it has been defined or assigned?",
            "option_a": "ValueError",
            "option_b": "TypeError",
            "option_c": "NameError",
            "option_d": "AttributeError",
            "correct_option": "C",
            "explanation": "Accessing an unbound identifier in the local or global namespace raises a NameError.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "Which built-in function is used to determine the data type of an object assigned to a variable?",
            "option_a": "typeof()",
            "option_b": "type()",
            "option_c": "datatype()",
            "option_d": "checktype()",
            "correct_option": "B",
            "explanation": "type(variable) returns the class type of the object stored in the variable.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "Which keyword is used inside a function to modify a variable defined at the module-level scope?",
            "option_a": "outer",
            "option_b": "nonlocal",
            "option_c": "global",
            "option_d": "static",
            "correct_option": "C",
            "explanation": "The 'global' keyword informs Python that the specified identifier belongs to the global (module) namespace.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "What is the output of the expression `x = '10' + '20'` followed by `print(x)`?",
            "option_a": "30",
            "option_b": "1020",
            "option_c": "Error",
            "option_d": "None",
            "correct_option": "B",
            "explanation": "When operands are strings, the + operator concatenates them, producing '1020' rather than numerical addition.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "Which of the following is an invalid variable name in Python because it is a reserved language keyword?",
            "option_a": "pass_value",
            "option_b": "pass",
            "option_c": "_pass",
            "option_d": "Pass",
            "correct_option": "B",
            "explanation": "'pass' is a reserved keyword in Python and cannot be used as an identifier name.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 1,
            "question_text": "Consider `a = [1, 2, 3]` and `b = a`. If we append 4 to b (`b.append(4)`), what is the value of a?",
            "option_a": "[1, 2, 3]",
            "option_b": "[1, 2, 3, 4]",
            "option_c": "[4, 1, 2, 3]",
            "option_d": "None",
            "correct_option": "B",
            "explanation": "Variables a and b reference the exact same mutable list object in memory, so changes through b are reflected in a.",
            "difficulty": "Easy"
        }
    ],

    # --------------------------------------------------------------------------
    # QUIZ 8: Python Conditional Statements - Practice Quiz (Topic 3)
    # --------------------------------------------------------------------------
    8: [
        {
            "topic_id": 3,
            "question_text": "Which of the following values evaluates to False when tested in a Python boolean conditional context?",
            "option_a": "[0]",
            "option_b": "'False'",
            "option_c": "[]",
            "option_d": "(-1)",
            "correct_option": "C",
            "explanation": "An empty sequence such as an empty list [] is inherently falsy in Python boolean evaluations.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "What is the correct syntax for a one-line ternary conditional expression in Python?",
            "option_a": "condition ? val_true : val_false",
            "option_b": "val_true if condition else val_false",
            "option_c": "if condition then val_true else val_false",
            "option_d": "val_true unless condition val_false",
            "correct_option": "B",
            "explanation": "Python uses the syntax `X if C else Y` for conditional ternary expressions.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "In the expression `A and B`, when does Python avoid evaluating B due to short-circuit logic?",
            "option_a": "When A evaluates to True",
            "option_b": "When A evaluates to False",
            "option_c": "When B evaluates to True",
            "option_d": "When both A and B are integers",
            "correct_option": "B",
            "explanation": "The 'and' operator short-circuits: if the first operand is falsy, the result is already determined to be falsy and B is not evaluated.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "What will be the output of `if 5 > 3 > 1: print('Chain') else: print('No')`?",
            "option_a": "Chain",
            "option_b": "No",
            "option_c": "SyntaxError",
            "option_d": "TypeError",
            "correct_option": "A",
            "explanation": "Python supports chained comparisons: `5 > 3 > 1` is evaluated as `(5 > 3) and (3 > 1)`, which is True.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "Which operator is used to verify whether a specific element exists within a collection inside an if statement?",
            "option_a": "contains",
            "option_b": "has",
            "option_c": "in",
            "option_d": "exists",
            "correct_option": "C",
            "explanation": "The 'in' operator checks for membership of an element within an iterable sequence or collection.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "What statement can be placed in an if block to make it syntactically valid when no action is needed yet?",
            "option_a": "continue",
            "option_b": "pass",
            "option_c": "break",
            "option_d": "return",
            "correct_option": "B",
            "explanation": "The 'pass' statement is a null operation in Python used as a placeholder in empty code blocks.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "What is the difference between `x == y` and `x is y` in a Python conditional check?",
            "option_a": "`==` checks memory identity; `is` checks value equality",
            "option_b": "`==` checks value equality; `is` checks memory object identity",
            "option_c": "Both operators perform the identical check",
            "option_d": "`is` can only be used with numbers",
            "correct_option": "B",
            "explanation": "`==` evaluates if the values of the operands are equal, while `is` evaluates if both refer to the exact same object in memory.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "What will be printed by `if not (10 < 5): print('Verified') else: print('Denied')`?",
            "option_a": "Verified",
            "option_b": "Denied",
            "option_c": "Error",
            "option_d": "None",
            "correct_option": "A",
            "explanation": "10 < 5 is False. The 'not' operator inverts False to True, so the if block executes 'Verified'.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "What is the output of `x = 10; print('High' if x > 15 else 'Medium' if x > 5 else 'Low')`?",
            "option_a": "High",
            "option_b": "Medium",
            "option_c": "Low",
            "option_d": "SyntaxError",
            "correct_option": "B",
            "explanation": "Since x = 10 is not > 15, the first else branch triggers, and since 10 > 5 is True, 'Medium' is returned.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 3,
            "question_text": "In Python, which character is required at the end of every `if`, `elif`, and `else` header line?",
            "option_a": "; (semicolon)",
            "option_b": ": (colon)",
            "option_c": "{ (left brace)",
            "option_d": "-> (arrow)",
            "correct_option": "B",
            "explanation": "Compound statements in Python such as if/elif/else must end with a colon (:) preceding the indented suite.",
            "difficulty": "Easy"
        }
    ],

    # --------------------------------------------------------------------------
    # QUIZ 9: Python Loops - Practice Quiz (Topic 4)
    # --------------------------------------------------------------------------
    9: [
        {
            "topic_id": 4,
            "question_text": "When does the `else` block attached to a Python `for` or `while` loop execute?",
            "option_a": "Only when the loop encounters a break statement",
            "option_b": "When the loop completes all iterations normally without hitting a break",
            "option_c": "After every single loop iteration",
            "option_d": "Only when an exception occurs inside the loop",
            "correct_option": "B",
            "explanation": "A loop's else block executes only if the loop finishes iterating naturally without being terminated by a break statement.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "What is the result of `list(range(2, 10, 2))`?",
            "option_a": "[2, 4, 6, 8, 10]",
            "option_b": "[2, 4, 6, 8]",
            "option_c": "[4, 6, 8, 10]",
            "option_d": "[2, 3, 4, 5, 6, 7, 8, 9]",
            "correct_option": "B",
            "explanation": "range(start, stop, step) starts at 2, increments by 2, and stops strictly before 10, yielding [2, 4, 6, 8].",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "Which built-in function provides both the index and value when iterating over a sequence in a for loop?",
            "option_a": "index()",
            "option_b": "enumerate()",
            "option_c": "zip()",
            "option_d": "count()",
            "correct_option": "B",
            "explanation": "enumerate(iterable) yields pairs of (index, item) during loop iteration.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "What is the output of `list(range(5, 0, -1))`?",
            "option_a": "[5, 4, 3, 2, 1, 0]",
            "option_b": "[5, 4, 3, 2, 1]",
            "option_c": "[4, 3, 2, 1, 0]",
            "option_d": "[]",
            "correct_option": "B",
            "explanation": "With a negative step of -1, range starts at 5 and counts down to 1 (stopping before 0).",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "Which function allows iterating simultaneously over two or more lists of equal length in parallel?",
            "option_a": "combine()",
            "option_b": "pair()",
            "option_c": "zip()",
            "option_d": "merge()",
            "correct_option": "C",
            "explanation": "zip(*iterables) aggregates elements from each of the iterables into tuples for parallel iteration.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "What happens if a while loop's condition never evaluates to False and no break is executed?",
            "option_a": "Python terminates the script after 1000 iterations",
            "option_b": "The loop runs infinitely until interrupted or memory is exhausted",
            "option_c": "The loop automatically converts to a for loop",
            "option_d": "A LoopWarning is emitted",
            "correct_option": "B",
            "explanation": "If a while loop condition remains permanently true, an infinite loop occurs until manually halted or killed.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "How many times will `for x in range(3):` iterate if the loop body contains `break` unconditionally?",
            "option_a": "0 times",
            "option_b": "1 time",
            "option_c": "3 times",
            "option_d": "Infinite times",
            "correct_option": "B",
            "explanation": "The loop begins the first iteration (x = 0), hits the break statement immediately, and exits, completing exactly 1 iteration.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "What method is used to loop over both keys and values of a Python dictionary simultaneously?",
            "option_a": "dict.keys()",
            "option_b": "dict.values()",
            "option_c": "dict.items()",
            "option_d": "dict.pairs()",
            "correct_option": "C",
            "explanation": "dict.items() returns a view object displaying a list of a given dictionary's (key, value) tuple pairs.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "What is the evaluated output of the list comprehension `[n ** 2 for n in range(4)]`?",
            "option_a": "[1, 4, 9, 16]",
            "option_b": "[0, 1, 4, 9]",
            "option_c": "[0, 2, 4, 6]",
            "option_d": "[0, 1, 8, 27]",
            "correct_option": "B",
            "explanation": "range(4) produces 0, 1, 2, 3. Squaring each yields 0, 1, 4, 9.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 4,
            "question_text": "If a `break` statement executes inside an inner nested loop, which loop does it terminate?",
            "option_a": "Only the innermost loop enclosing the break",
            "option_b": "All enclosing outer loops",
            "option_c": "The outermost loop only",
            "option_d": "The entire Python script",
            "correct_option": "A",
            "explanation": "In Python, break terminates solely the innermost enclosing loop.",
            "difficulty": "Easy"
        }
    ],

    # --------------------------------------------------------------------------
    # QUIZ 10: Number System - Fundamentals Quiz (Topic 7)
    # --------------------------------------------------------------------------
    10: [
        {
            "topic_id": 7,
            "question_text": "What is the Greatest Common Divisor (GCD) of 24 and 36?",
            "option_a": "6",
            "option_b": "8",
            "option_c": "12",
            "option_d": "18",
            "correct_option": "C",
            "explanation": "Factors of 24: 1, 2, 3, 4, 6, 8, 12, 24. Factors of 36: 1, 2, 3, 4, 6, 9, 12, 18, 36. The greatest common factor is 12.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "What is the Least Common Multiple (LCM) of 4 and 6?",
            "option_a": "12",
            "option_b": "24",
            "option_c": "18",
            "option_d": "8",
            "correct_option": "A",
            "explanation": "Multiples of 4: 4, 8, 12, 16... Multiples of 6: 6, 12, 18... The smallest shared positive multiple is 12.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "A number is divisible by 3 if and only if which condition is met?",
            "option_a": "Its last digit is 3",
            "option_b": "The sum of its digits is divisible by 3",
            "option_c": "Its last two digits are divisible by 3",
            "option_d": "It is an odd number",
            "correct_option": "B",
            "explanation": "According to the divisibility rule of 3, an integer is divisible by 3 if the sum of all its digits is divisible by 3.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "What are two positive integers called if their Greatest Common Divisor is equal to 1?",
            "option_a": "Twin primes",
            "option_b": "Coprime (or relatively prime)",
            "option_c": "Composite numbers",
            "option_d": "Irrational numbers",
            "correct_option": "B",
            "explanation": "Two numbers are coprime (or relatively prime) if they share no common positive factor other than 1.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "What is the decimal (base 10) value of the binary number (1011)_2?",
            "option_a": "9",
            "option_b": "10",
            "option_c": "11",
            "option_d": "13",
            "correct_option": "C",
            "explanation": "(1 * 2^3) + (0 * 2^2) + (1 * 2^1) + (1 * 2^0) = 8 + 0 + 2 + 1 = 11.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "Which of the following numbers is neither prime nor composite?",
            "option_a": "0",
            "option_b": "1",
            "option_c": "2",
            "option_d": "3",
            "correct_option": "B",
            "explanation": "By mathematical definition, 1 has only one positive divisor (itself), so it is neither prime nor composite.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "In the number 4,875, what is the place value of the digit 8?",
            "option_a": "8",
            "option_b": "80",
            "option_c": "800",
            "option_d": "8000",
            "correct_option": "C",
            "explanation": "The digit 8 occupies the hundreds position, so its place value is 8 * 100 = 800.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "Which set of numbers contains all natural numbers and the number zero?",
            "option_a": "Negative integers",
            "option_b": "Whole numbers",
            "option_c": "Irrational numbers",
            "option_d": "Prime numbers",
            "correct_option": "B",
            "explanation": "The whole numbers set is defined as {0, 1, 2, 3, ...}, which includes zero and all positive natural numbers.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "What is the result of dividing any non-zero number by zero in standard arithmetic?",
            "option_a": "Zero",
            "option_b": "One",
            "option_c": "Undefined",
            "option_d": "Infinity",
            "correct_option": "C",
            "explanation": "Division by zero is undefined in standard real arithmetic.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 7,
            "question_text": "How many prime numbers exist between 1 and 10 inclusive?",
            "option_a": "3",
            "option_b": "4",
            "option_c": "5",
            "option_d": "6",
            "correct_option": "B",
            "explanation": "The prime numbers between 1 and 10 are 2, 3, 5, and 7, which gives a total of 4 primes.",
            "difficulty": "Easy"
        }
    ],

    # --------------------------------------------------------------------------
    # QUIZ 11: Percentage - Practical Math Quiz (Topic 8)
    # --------------------------------------------------------------------------
    11: [
        {
            "topic_id": 8,
            "question_text": "What is 15% of 300?",
            "option_a": "30",
            "option_b": "45",
            "option_c": "50",
            "option_d": "60",
            "correct_option": "B",
            "explanation": "15% of 300 = (15 / 100) * 300 = 15 * 3 = 45.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "If a value decreases from 120 to 90, what is the percentage decrease?",
            "option_a": "20%",
            "option_b": "25%",
            "option_c": "30%",
            "option_d": "33.3%",
            "correct_option": "B",
            "explanation": "Decrease = 120 - 90 = 30. Percentage decrease = (30 / 120) * 100 = 25%.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "A student scored 45 marks out of 60 on an exam. What is their score percentage?",
            "option_a": "70%",
            "option_b": "75%",
            "option_c": "80%",
            "option_d": "85%",
            "correct_option": "B",
            "explanation": "Percentage = (45 / 60) * 100 = 0.75 * 100 = 75%.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "If 40% of a number is equal to 80, what is the value of the number?",
            "option_a": "160",
            "option_b": "200",
            "option_c": "240",
            "option_d": "320",
            "correct_option": "B",
            "explanation": "0.40 * X = 80 => X = 80 / 0.40 = 200.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "An item costs $80. If an 8% sales tax is added, what is the total price?",
            "option_a": "$84.80",
            "option_b": "$86.40",
            "option_c": "$88.00",
            "option_d": "$85.20",
            "correct_option": "B",
            "explanation": "Tax = 80 * 0.08 = $6.40. Total price = 80 + 6.40 = $86.40.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "What is the fraction 3/5 expressed as a percentage?",
            "option_a": "35%",
            "option_b": "50%",
            "option_c": "60%",
            "option_d": "65%",
            "correct_option": "C",
            "explanation": "(3 / 5) * 100 = 0.6 * 100 = 60%.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "A shirt originally priced at $50 is on sale with a 20% discount. What is the sale price?",
            "option_a": "$30",
            "option_b": "$35",
            "option_c": "$40",
            "option_d": "$45",
            "correct_option": "C",
            "explanation": "Discount = 20% of 50 = $10. Sale price = 50 - 10 = $40.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "What is 50% of 20% of 1,000?",
            "option_a": "50",
            "option_b": "100",
            "option_c": "150",
            "option_d": "200",
            "correct_option": "B",
            "explanation": "20% of 1000 = 200. 50% of 200 = 100.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "If a town population increases from 20,000 to 22,000, what is the growth rate percentage?",
            "option_a": "5%",
            "option_b": "10%",
            "option_c": "12%",
            "option_d": "15%",
            "correct_option": "B",
            "explanation": "Increase = 2,000. Percentage growth = (2,000 / 20,000) * 100 = 10%.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 8,
            "question_text": "A price of $100 increases by 10% and then the new price decreases by 10%. What is the final price?",
            "option_a": "$100",
            "option_b": "$99",
            "option_c": "$98",
            "option_d": "$101",
            "correct_option": "B",
            "explanation": "$100 + 10% = $110. $110 - 10% ($11) = $99.",
            "difficulty": "Easy"
        }
    ],

    # --------------------------------------------------------------------------
    # QUIZ 12: Profit and Loss - Foundations Quiz (Topic 9)
    # --------------------------------------------------------------------------
    12: [
        {
            "topic_id": 9,
            "question_text": "If an item with a Cost Price of $400 is sold for $320, what is the loss amount?",
            "option_a": "$60",
            "option_b": "$70",
            "option_c": "$80",
            "option_d": "$100",
            "correct_option": "C",
            "explanation": "Loss = Cost Price - Selling Price = 400 - 320 = $80.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "If Cost Price is $400 and Selling Price is $320, what is the loss percentage?",
            "option_a": "15%",
            "option_b": "20%",
            "option_c": "25%",
            "option_d": "30%",
            "correct_option": "B",
            "explanation": "Loss % = (Loss / Cost Price) * 100 = (80 / 400) * 100 = 20%.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "What term describes the condition when Selling Price equals Cost Price (neither profit nor loss)?",
            "option_a": "Discount margin",
            "option_b": "Break-even point",
            "option_c": "Gross yield",
            "option_d": "Marked parity",
            "correct_option": "B",
            "explanation": "The break-even point is reached when total revenue equals total cost, yielding zero profit and zero loss.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "A trader buys a bicycle for $200 and wants to make a 25% profit. What should be the Selling Price?",
            "option_a": "$225",
            "option_b": "$240",
            "option_c": "$250",
            "option_d": "$260",
            "correct_option": "C",
            "explanation": "Profit = 25% of 200 = $50. Selling Price = 200 + 50 = $250.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "If an item is sold for $330 at a 10% profit, what was its original Cost Price?",
            "option_a": "$290",
            "option_b": "$300",
            "option_c": "$310",
            "option_d": "$315",
            "correct_option": "B",
            "explanation": "Selling Price = CP * 1.10 => 330 = CP * 1.10 => CP = 330 / 1.10 = $300.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "What is the formula to calculate Discount?",
            "option_a": "Selling Price - Cost Price",
            "option_b": "Marked Price - Selling Price",
            "option_c": "Cost Price - Marked Price",
            "option_d": "Selling Price - Marked Price",
            "correct_option": "B",
            "explanation": "Discount is the concession allowed on the Marked Price: Discount = Marked Price - Selling Price.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "An article with a Marked Price of $500 is sold for $450. What is the discount percentage?",
            "option_a": "8%",
            "option_b": "10%",
            "option_c": "12%",
            "option_d": "15%",
            "correct_option": "B",
            "explanation": "Discount = 500 - 450 = 50. Discount % = (50 / 500) * 100 = 10%.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "A merchant buys goods for $1,000 and spends $200 on transportation. What is the actual total Cost Price?",
            "option_a": "$1,000",
            "option_b": "$1,100",
            "option_c": "$1,200",
            "option_d": "$800",
            "correct_option": "C",
            "explanation": "Overhead expenses like transportation and repair are added to the purchase price to calculate the true Cost Price: 1000 + 200 = $1,200.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "If a watch is sold at a loss of 15% on a Cost Price of $80, what is the Selling Price?",
            "option_a": "$65",
            "option_b": "$68",
            "option_c": "$70",
            "option_d": "$72",
            "correct_option": "B",
            "explanation": "Loss = 15% of 80 = $12. Selling Price = 80 - 12 = $68.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 9,
            "question_text": "What is the effective single discount equivalent to two successive discounts of 10% and 10%?",
            "option_a": "20%",
            "option_b": "19%",
            "option_c": "18%",
            "option_d": "21%",
            "correct_option": "B",
            "explanation": "Starting with $100: after 1st discount = $90; after 2nd discount of 10% on $90 ($9) = $81. Total discount = 100 - 81 = 19%.",
            "difficulty": "Easy"
        }
    ],

    # --------------------------------------------------------------------------
    # QUIZ 13: Algebra - Equations & Expansions Quiz (Topic 10)
    # --------------------------------------------------------------------------
    13: [
        {
            "topic_id": 10,
            "question_text": "What is the algebraic expansion of `(a - b)^2`?",
            "option_a": "a^2 - b^2",
            "option_b": "a^2 - 2ab + b^2",
            "option_c": "a^2 + 2ab - b^2",
            "option_d": "a^2 - 2ab - b^2",
            "correct_option": "B",
            "explanation": "(a - b)^2 = (a - b)(a - b) = a^2 - 2ab + b^2.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "What is the expansion of `(a - b)(a + b)`?",
            "option_a": "a^2 + b^2",
            "option_b": "a^2 - b^2",
            "option_c": "(a - b)^2",
            "option_d": "2a - 2b",
            "correct_option": "B",
            "explanation": "The product of the sum and difference of two terms is the difference of their squares: a^2 - b^2.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "Solve the linear equation for x: `5x - 3 = 2x + 9`.",
            "option_a": "x = 2",
            "option_b": "x = 3",
            "option_c": "x = 4",
            "option_d": "x = 5",
            "correct_option": "C",
            "explanation": "5x - 2x = 9 + 3 => 3x = 12 => x = 4.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "What is the degree of the polynomial `4x^3 + 7x^2 - 2x + 5`?",
            "option_a": "1",
            "option_b": "2",
            "option_c": "3",
            "option_d": "4",
            "correct_option": "C",
            "explanation": "The degree of a polynomial is the highest power of the variable present in it, which is 3.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "What are the factored components of the quadratic expression `x^2 + 5x + 6`?",
            "option_a": "(x + 1)(x + 6)",
            "option_b": "(x + 2)(x + 3)",
            "option_c": "(x - 2)(x - 3)",
            "option_d": "(x + 5)(x + 1)",
            "correct_option": "B",
            "explanation": "We find two numbers whose sum is 5 and product is 6: 2 and 3. Thus, (x + 2)(x + 3).",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "If x = 3 and y = -2, what is the value of the expression `2x^2 - 3y`?",
            "option_a": "12",
            "option_b": "18",
            "option_c": "24",
            "option_d": "30",
            "correct_option": "C",
            "explanation": "2(3^2) - 3(-2) = 2(9) - (-6) = 18 + 6 = 24.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "What is the coefficient of x in the expression `8x^2 - 5x + 11`?",
            "option_a": "8",
            "option_b": "5",
            "option_c": "-5",
            "option_d": "11",
            "correct_option": "C",
            "explanation": "The numerical multiplier preceding x is -5.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "Translate to an algebraic equation: 'Three times a number n increased by 7 is equal to 28.'",
            "option_a": "3(n + 7) = 28",
            "option_b": "3n + 7 = 28",
            "option_c": "7n + 3 = 28",
            "option_d": "3n - 7 = 28",
            "correct_option": "B",
            "explanation": "Three times n is 3n, increased by 7 gives 3n + 7, which equals 28.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "What is the solution for x in the equation `x / 4 + 3 = 7`?",
            "option_a": "x = 12",
            "option_b": "x = 16",
            "option_c": "x = 20",
            "option_d": "x = 28",
            "correct_option": "B",
            "explanation": "x / 4 = 7 - 3 = 4 => x = 4 * 4 = 16.",
            "difficulty": "Easy"
        },
        {
            "topic_id": 10,
            "question_text": "What distinguishes an algebraic equation from an algebraic expression?",
            "option_a": "An equation contains an equality symbol (=); an expression does not",
            "option_b": "An expression always contains variables; an equation does not",
            "option_c": "An equation cannot have negative numbers",
            "option_d": "There is no difference between them",
            "correct_option": "A",
            "explanation": "An algebraic equation equates two expressions using an equal sign (=), whereas an expression has no equality relation.",
            "difficulty": "Easy"
        }
    ]
}


def run_migration():
    print("=" * 75)
    print("QUIZINSIGHT MIGRATION: DEDUPLICATE QUESTION BANK & SEED MINIMUM 10 QUESTIONS")
    print("=" * 75)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # ----------------------------------------------------------------------
        # STEP 1: Identify and Report All Duplicates
        # ----------------------------------------------------------------------
        print("\n[STEP 1] Scanning Question Bank for Duplicate Questions...")
        cur.execute("SELECT question_id, topic_id, question_text FROM questions ORDER BY question_id")
        all_questions = cur.fetchall()

        groups = {}
        for qid, tid, qtext in all_questions:
            norm = normalize_question_text(qtext)
            if norm not in groups:
                groups[norm] = []
            groups[norm].append((qid, tid, qtext))

        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
        print(f"Total question rows in DB: {len(all_questions)}")
        print(f"Total unique normalized question concepts: {len(groups)}")
        print(f"Duplicate groups detected: {len(duplicate_groups)}")

        total_merged = 0
        for norm_key, qlist in duplicate_groups.items():
            canonical = qlist[0]
            dups = qlist[1:]
            canonical_id = canonical[0]
            print(f"\n  Duplicate Group for Concept: '{canonical[2][:70]}...'")
            print(f"    --> Canonical Question ID: {canonical_id}")
            for d in dups:
                dup_id = d[0]
                print(f"    --> Merging Duplicate Question ID {dup_id} into Canonical ID {canonical_id}...")

                # 1. Migrate quiz_questions mappings
                cur.execute("SELECT quiz_id FROM quiz_questions WHERE question_id = %s", (dup_id,))
                quizzes_using_dup = [r[0] for r in cur.fetchall()]
                for qz_id in quizzes_using_dup:
                    cur.execute(
                        """
                        INSERT INTO quiz_questions (quiz_id, question_id)
                        VALUES (%s, %s)
                        ON CONFLICT (quiz_id, question_id) DO NOTHING
                        """,
                        (qz_id, canonical_id)
                    )
                cur.execute("DELETE FROM quiz_questions WHERE question_id = %s", (dup_id,))

                # 2. Migrate student_answers (delete if attempt already recorded canonical answer)
                cur.execute(
                    """
                    DELETE FROM student_answers 
                    WHERE question_id = %s 
                      AND attempt_id IN (SELECT attempt_id FROM student_answers WHERE question_id = %s)
                    """,
                    (dup_id, canonical_id)
                )
                cur.execute(
                    "UPDATE student_answers SET question_id = %s WHERE question_id = %s",
                    (canonical_id, dup_id)
                )

                # 3. Migrate quiz_attempts.selected_question_ids JSONB
                cur.execute(
                    "SELECT attempt_id, selected_question_ids FROM quiz_attempts WHERE selected_question_ids IS NOT NULL"
                )
                att_rows = cur.fetchall()
                for att_id, sel_ids in att_rows:
                    if sel_ids:
                        ids_list = sel_ids if isinstance(sel_ids, list) else json.loads(sel_ids)
                        if dup_id in ids_list:
                            new_ids = []
                            for x in ids_list:
                                rep = canonical_id if x == dup_id else x
                                if rep not in new_ids:
                                    new_ids.append(rep)
                            cur.execute(
                                "UPDATE quiz_attempts SET selected_question_ids = %s WHERE attempt_id = %s",
                                (json.dumps(new_ids), att_id)
                            )

                # 4. Safely delete the redundant duplicate question row
                cur.execute("DELETE FROM questions WHERE question_id = %s", (dup_id,))
                total_merged += 1

        print(f"\n  --> Successfully merged and deleted {total_merged} duplicate question rows.")

        # Clean up accidental empty duplicate quizzes 2-7
        cur.execute("DELETE FROM quizzes WHERE quiz_id IN (2, 3, 4, 5, 6, 7)")
        print("  --> Safely cleaned up empty phantom duplicate quizzes 2 through 7.")

        # ----------------------------------------------------------------------
        # STEP 2: Enforce Database Engine Unique Index on Normalized Question Text
        # ----------------------------------------------------------------------
        print("\n[STEP 2] Creating PostgreSQL Functional Unique Index for Question Uniqueness...")
        cur.execute("""
            CREATE OR REPLACE FUNCTION normalize_question_text(input_text TEXT)
            RETURNS TEXT AS $$
            BEGIN
                RETURN lower(regexp_replace(regexp_replace(trim(input_text), '[^a-zA-Z0-9]+', ' ', 'g'), '\\s+', ' ', 'g'));
            END;
            $$ LANGUAGE plpgsql IMMUTABLE;

            CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_normalized_unique 
            ON questions (normalize_question_text(question_text));
        """)
        print("  --> PostgreSQL functional unique index `idx_questions_normalized_unique` enforced successfully!")

        # ----------------------------------------------------------------------
        # STEP 3: Add New Unique Questions to Ensure Minimum 10 Per Quiz
        # ----------------------------------------------------------------------
        print("\n[STEP 3] Adding New Relevant Unique Questions to Incomplete Quizzes...")
        conn.commit()  # commit deduplication and index before inserting new questions

        questions_added_per_quiz = {}
        for quiz_id, questions_list in NEW_QUESTIONS_DATA.items():
            cur.execute("SELECT quiz_title, COUNT(qq.question_id) FROM quizzes q LEFT JOIN quiz_questions qq ON q.quiz_id = qq.quiz_id WHERE q.quiz_id = %s GROUP BY q.quiz_title", (quiz_id,))
            q_info = cur.fetchone()
            quiz_title = q_info[0] if q_info else f"Quiz {quiz_id}"
            initial_count = q_info[1] if q_info else 0

            added_count = 0
            for qdata in questions_list:
                # Check for duplicate before insert
                existing = find_duplicate_question(qdata["question_text"], conn=conn)
                if existing:
                    print(f"    [SKIP] Already exists: '{qdata['question_text'][:50]}...' (ID: {existing['question_id']})")
                    # Ensure linked to this quiz
                    cur.execute(
                        "INSERT INTO quiz_questions (quiz_id, question_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (quiz_id, existing["question_id"])
                    )
                else:
                    new_qid = add_question(
                        topic_id=qdata["topic_id"],
                        question_text=qdata["question_text"],
                        option_a=qdata["option_a"],
                        option_b=qdata["option_b"],
                        option_c=qdata["option_c"],
                        option_d=qdata["option_d"],
                        correct_option=qdata["correct_option"],
                        explanation=qdata["explanation"],
                        difficulty=qdata["difficulty"],
                        quiz_id=quiz_id,
                        conn=conn
                    )
                    added_count += 1

            questions_added_per_quiz[quiz_id] = {
                "title": quiz_title,
                "initial": initial_count,
                "added": added_count
            }

        # ----------------------------------------------------------------------
        # STEP 4: Verification Summary
        # ----------------------------------------------------------------------
        print("\n[STEP 4] Auditing Final Question Counts Per Quiz...")
        cur.execute("""
            SELECT 
                q.quiz_id,
                q.quiz_title,
                s.subject_name,
                t.topic_name,
                COUNT(DISTINCT qq.question_id) AS unique_questions
            FROM quizzes q
            JOIN subjects s ON q.subject_id = s.subject_id
            JOIN topics t ON q.topic_id = t.topic_id
            LEFT JOIN quiz_questions qq ON q.quiz_id = qq.quiz_id
            WHERE q.quiz_type = 'Existing'
            GROUP BY q.quiz_id, q.quiz_title, s.subject_name, t.topic_name
            ORDER BY q.quiz_id
        """)
        final_quizzes = cur.fetchall()

        print("\n" + "-" * 75)
        print(f"{'Quiz ID':<8} | {'Subject':<12} | {'Topic':<22} | {'Unique Questions':<16} | {'Status'}")
        print("-" * 75)
        for fq in final_quizzes:
            status = "PASSED (>= 10)" if fq[4] >= 10 else "FAILED (< 10)"
            print(f"{fq[0]:<8} | {fq[2]:<12} | {fq[3]:<22} | {fq[4]:<16} | {status}")
            assert fq[4] >= 10, f"Quiz {fq[0]} has fewer than 10 questions: {fq[4]}"

        # Verify zero duplicates across entire question bank
        cur.execute("SELECT question_id, question_text FROM questions")
        check_all = cur.fetchall()
        check_norm = {}
        for qid, qtext in check_all:
            n = normalize_question_text(qtext)
            assert n not in check_norm, f"Duplicate still exists: '{qtext}' vs '{check_norm[n]}'"
            check_norm[n] = qid

        print("-" * 75)
        print(f"Verified: Question Bank contains {len(check_all)} total questions, ALL 100% UNIQUE.")
        print("=" * 75)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 75)

    except Exception as e:
        conn.rollback()
        print(f"Migration failed with error: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
