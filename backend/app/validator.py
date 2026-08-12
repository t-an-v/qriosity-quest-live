"""
Hallucination guard, adapted from the privacy policy grader pattern.

Every quote Gemini claims came from the student's answer gets checked
against what the student ACTUALLY wrote, using fuzzy matching so close
paraphrases still pass, but invented content gets flagged.
"""

from difflib import SequenceMatcher

MATCH_THRESHOLD = 0.7  # tune this once we have more real answers to test against


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_best_match(quote: str, source_text: str, window_ratio: float = 1.3) -> float:
    """
    Slides the quote length across the source text to find the best-matching
    substring, rather than comparing the quote against the whole answer at once
    (which would unfairly punish short quotes from long answers).
    """
    quote_len = len(quote)
    window_len = int(quote_len * window_ratio)
    best_score = 0.0

    if len(source_text) <= window_len:
        return similarity(quote, source_text)

    for start in range(0, len(source_text) - window_len + 1, max(1, window_len // 4)):
        chunk = source_text[start:start + window_len]
        score = similarity(quote, chunk)
        best_score = max(best_score, score)

    return best_score


def validate_scored_answer(scored_result: dict) -> dict:
    """
    Takes one scored open-ended answer (from open_ended_scorer) and checks
    whether the quoted_evidence actually appears in the student's raw answer.

    Adds a 'validated' flag and a 'match_score' so we can decide whether
    this result is safe to include in a report, or needs a human look.
    """
    quote = scored_result.get("quoted_evidence", "")
    source = scored_result.get("raw_student_answer", "")

    match_score = find_best_match(quote, source) if quote and source else 0.0

    return {
        **scored_result,
        "match_score": round(match_score, 3),
        "validated": match_score >= MATCH_THRESHOLD,
    }


def validate_all(scored_results: list[dict]) -> list[dict]:
    validated = [validate_scored_answer(r) for r in scored_results]

    flagged = [r for r in validated if not r["validated"]]
    if flagged:
        # TODO: decide what happens to flagged results - re-run with stricter
        # prompt? drop the quote and keep the score? route to manual review?
        # Not deciding this in code until we've discussed it.
        pass

    return validated
