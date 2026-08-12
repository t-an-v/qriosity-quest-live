"""
Quick manual test script - run this directly instead of pasting code into
the interactive Python shell (avoids indentation/paste issues entirely).

Usage: py test_scoring.py
"""

from open_ended_scorer import score_open_ended_answer
from mcq_scorer import load_rubric, score_mcq_answer
from validator import validate_scored_answer

rubric = load_rubric()

# Test 0: MCQ safety net - option 'a' for Q1 has no confirmed score yet
mcq_result = score_mcq_answer("1", "a", rubric)
print("--- Q1 option 'a' (should be unconfirmed) ---")
print(mcq_result)
print()

# Test 1: Joyful Discovery trait (Q2)
result = score_open_ended_answer(
    "2",
    "I would ask the plant why it feels sad sometimes and if it likes rain.",
    rubric,
)
validated = validate_scored_answer(result)
print("--- Q2 (Joyful Discovery) ---")
print(validated)
print()

# Test 2: Insight Seeker trait (Q6)
result2 = score_open_ended_answer(
    "6",
    "Maybe the water came from the air because it was cold outside and the leaf was cooler than the air around it.",
    rubric,
)
validated2 = validate_scored_answer(result2)
print("--- Q6 (Insight Seeker) ---")
print(validated2)
print()

# Test 3: Bold Engager trait (Q8)
result3 = score_open_ended_answer(
    "8",
    "I would tell Sara we should look it up together right now on my mom's phone.",
    rubric,
)
validated3 = validate_scored_answer(result3)
print("--- Q8 (Bold Engager) ---")
print(validated3)
print()

# Test 4: Open Ended trait (Q17)
result4 = score_open_ended_answer(
    "17",
    "I wonder if AI can ever really understand feelings or if it just pretends to.",
    rubric,
)
validated4 = validate_scored_answer(result4)
print("--- Q17 (Open Ended) ---")
print(validated4)