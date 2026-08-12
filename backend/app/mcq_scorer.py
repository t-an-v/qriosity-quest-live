"""
Deterministic scorer for MCQ questions.
No LLM calls here - pure lookup against the rubric's option_trait_map.
Fast, free, and fully predictable - this is our reliability baseline.

CORRECTED MODEL (per official Master Rubric): each MCQ question has 5 options,
each option written to represent a DIFFERENT one of the 5 traits. Picking an
option is a full, complete signal for that trait - there is no partial credit.
So scoring is always 4 when an option is selected; the only real "lookup" is
which trait that option maps to.
"""

import json
from pathlib import Path

RUBRIC_PATH = Path(__file__).parent.parent / "data" / "rubric.json"

FULL_MARK = 4  # every MCQ selection is a complete expression of its trait - no partial credit


def load_rubric() -> dict:
    with open(RUBRIC_PATH, "r") as f:
        return json.load(f)


def score_mcq_answer(question_id: str, selected_option: str, rubric: dict) -> dict:
    """
    Scores a single MCQ answer by looking up which trait the selected option maps to.

    Returns a dict with the trait, a fixed score of 4, and a flag if this
    particular option->trait mapping hasn't been independently confirmed
    against a real founder-provided example yet (see rubric.json "confirmed").
    """
    question = rubric["questions"].get(str(question_id))
    if question is None:
        raise ValueError(f"Unknown question id: {question_id}")

    if question["type"] != "mcq":
        raise ValueError(f"Question {question_id} is not an MCQ question")

    option = selected_option.lower()
    option_map = question.get("option_trait_map", {})
    trait = option_map.get(option)

    if trait is None:
        raise ValueError(
            f"No trait mapping found for question {question_id}, option '{option}'. "
            f"Valid options for this question: {list(option_map.keys())}"
        )

    confirmed_options = question.get("confirmed", [])

    return {
        "question_id": question_id,
        "trait": trait,
        "selected_option": option,
        "score": FULL_MARK,
        "needs_confirmation": option not in confirmed_options,
    }


def score_all_mcq(mcq_answers: dict, rubric: dict) -> list[dict]:
    """
    mcq_answers: {"1": "b", "4": "b", "7": "c", ...}
    Returns a list of per-question score results.
    """
    results = []
    for question_id, selected_option in mcq_answers.items():
        results.append(score_mcq_answer(question_id, selected_option, rubric))
    return results


if __name__ == "__main__":
    # Quick manual test
    rubric = load_rubric()
    sample_answers = {"1": "b", "4": "b", "11": "b"}
    for result in score_all_mcq(sample_answers, rubric):
        print(result)