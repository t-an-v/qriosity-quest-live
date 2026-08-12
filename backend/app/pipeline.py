"""
Orchestrates the full scoring pipeline for one student's submission:

  1. Score MCQ answers with rules (fast, free, deterministic)
  2. Score open-ended TRAIT answers with Gemini (structured JSON prompting,
     universal 1-4 scale)
  3. Extract Q17/Q18 reflection answers with Gemini (no trait, no score -
     just a quote for the report's voice)
  4. Validate every Gemini quote against the raw answer (hallucination guard)
  5. Aggregate per-trait totals
  6. Return a single structured result ready for report generation

This is the file that ties mcq_scorer, open_ended_scorer, and validator
together - nothing else in the codebase should need to know about all
three at once.

main.py still sends ALL open-ended answers (trait questions 2,3,5,6,8,9,10,
14,15,16 AND reflection questions 17,18) in a single open_answers dict - the
split by question type happens in here, driven by rubric.json, so the API
contract doesn't need to change.
"""

from collections import defaultdict

from app.mcq_scorer import load_rubric, score_all_mcq
from app.open_ended_scorer import score_all_open_ended, score_all_reflections
from app.validator import validate_all


def run_pipeline(mcq_answers: dict, open_answers: dict) -> dict:
    """
    mcq_answers: {"1": "b", "4": "b", ...}
    open_answers: {"2": "student's written response", ..., "17": "...", "18": "..."}
    """
    rubric = load_rubric()

    trait_answers, reflection_answers = _split_open_answers(open_answers, rubric)

    mcq_results = score_all_mcq(mcq_answers, rubric)
    open_results_raw = score_all_open_ended(trait_answers, rubric)
    open_results = validate_all(open_results_raw)

    reflection_results_raw = score_all_reflections(reflection_answers, rubric)
    reflection_results = validate_all(reflection_results_raw)

    unresolved = [r for r in mcq_results if r["needs_confirmation"]]
    unvalidated = [r for r in open_results if not r["validated"]]
    unvalidated_reflections = [r for r in reflection_results if not r["validated"]]

    trait_totals = compute_trait_totals(mcq_results, open_results, rubric)

    return {
        "mcq_results": mcq_results,
        "open_ended_results": open_results,
        "reflection_results": reflection_results,  # Q17/Q18 - not trait-scored, for report voice only
        "trait_totals": trait_totals,
        "warnings": {
            "mcq_needs_confirmation": [r["question_id"] for r in unresolved],
            "open_ended_failed_validation": [r["question_id"] for r in unvalidated],
            "reflection_failed_validation": [r["question_id"] for r in unvalidated_reflections],
        },
    }


def _split_open_answers(open_answers: dict, rubric: dict) -> tuple[dict, dict]:
    """
    Routes each open_answers entry to the trait scorer or the reflection
    extractor based on rubric.json's question "type" - so callers (main.py)
    don't need to know which questions are reflective.
    """
    trait_answers = {}
    reflection_answers = {}

    for qid, answer in open_answers.items():
        question = rubric["questions"].get(str(qid))
        if question is None:
            raise ValueError(f"Unknown question id in open_answers: {qid}")

        if question["type"] == "open":
            trait_answers[qid] = answer
        elif question["type"] == "reflection":
            reflection_answers[qid] = answer
        else:
            raise ValueError(f"Question {qid} has type '{question['type']}' - not valid in open_answers (mcq questions go in mcq_answers)")

    return trait_answers, reflection_answers


def compute_trait_totals(mcq_results: list[dict], open_results: list[dict], rubric: dict) -> dict:
    """
    Sums scores per trait. Reflection results (Q17/Q18) are intentionally
    excluded entirely - they're never passed into this function at all,
    not just filtered out, since they carry no trait or score by design.
    """
    totals = defaultdict(int)
    max_possible = defaultdict(int)

    all_results = mcq_results + open_results

    for result in all_results:
        if result.get("score") is None:
            continue  # unresolved MCQ mapping - don't silently count as 0

        trait = result["trait"]
        totals[trait] += result["score"]
        max_possible[trait] += 4

    return {
        trait: {
            "score": totals[trait],
            "max_possible": max_possible[trait],
            "percentage": round(100 * totals[trait] / max_possible[trait], 1) if max_possible[trait] else None,
        }
        for trait in totals
    }