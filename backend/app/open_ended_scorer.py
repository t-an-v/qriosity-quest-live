"""
Scores open-ended (subjective) answers using Gemini with structured JSON prompting.
Same pattern as the privacy policy grader: strict JSON output, one call per answer,
no free-form text response that we'd have to parse loosely.

Uses the new `google.genai` SDK (the old `google.generativeai` package is
deprecated as of 2026 and no longer receives updates/fixes).

Two distinct paths, per the Master Rubric:
  - score_open_ended_answer: for trait questions (2,3,5,6,8,9,10,14,15,16).
    Scored 1-4 on the SAME universal scale for every question (rubric.json's
    "open_ended_scale"), not per-question criteria.
  - extract_reflection_answer: for the Q17/Q18 AI-and-the-future questions.
    NOT trait-scored at all - just pulls a quote to give the report voice.
"""

import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()  # reads GEMINI_API_KEY from a local .env file - never commit that file

RUBRIC_PATH = Path(__file__).parent.parent / "data" / "rubric.json"

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3.5-flash-lite"  # free-tier friendly: higher RPM than standard Flash, good for iterative testing
# Alternative if you want slightly stronger reasoning and can live with lower RPM: "gemini-3.6-flash"


def load_rubric() -> dict:
    with open(RUBRIC_PATH, "r") as f:
        return json.load(f)


def build_scoring_prompt(question_prompt: str, trait: str, trait_description: str, scale: dict, student_answer: str) -> str:
    """
    Builds a structured prompt that forces Gemini to return ONLY JSON.
    Uses the SAME universal 1-4 scale for every question (per Master Rubric
    Section 4) rather than bespoke per-question criteria.
    """
    scale_text = "\n".join(f"{level}: {desc}" for level, desc in scale.items())

    return f"""You are scoring a student's answer to a curiosity assessment question.
This question is designed to draw out the trait "{trait}": {trait_description}

Score strictly against the criteria below - do not be lenient, do not invent
strengths the answer doesn't show.

QUESTION: {question_prompt}

SCORING CRITERIA (1-4 scale, same scale used for every question):
{scale_text}

STUDENT'S ANSWER:
\"\"\"{student_answer}\"\"\"

Respond with ONLY valid JSON, no markdown formatting, no preamble, in this exact shape:
{{
  "score": <integer 1-4>,
  "quoted_evidence": "<a short exact phrase copied directly from the student's answer that justifies the score - must be verbatim from their answer, not paraphrased>",
  "feedback": "<one or two sentences. FIRST name something the student did well, specifically - never generic praise. THEN offer one small, concrete next step to deepen the trait further. Never frame a low score as a failure - it's a direction to grow in, not a shortcoming.>"
}}"""


def build_reflection_prompt(question_prompt: str, student_answer: str) -> str:
    """
    Q17/Q18 only. Per Master Rubric Section 3, these are NOT scored against
    any trait - purely reflective content used to add voice/personality to
    the report. No score field at all.
    """
    return f"""A student answered a reflective, open-ended question about AI and the future
of learning. This is NOT being graded against any trait or rubric - you're
just pulling out a short, genuine quote that captures their voice for their
personal report.

QUESTION: {question_prompt}

STUDENT'S ANSWER:
\"\"\"{student_answer}\"\"\"

Respond with ONLY valid JSON, no markdown formatting, no preamble, in this exact shape:
{{
  "quoted_evidence": "<a short exact phrase copied directly from the student's answer - must be verbatim, not paraphrased - that best captures their voice or perspective>",
  "summary": "<one warm sentence, written for a parent/teacher audience, describing what the student's answer reveals about how they think - no scoring language>"
}}"""


def call_with_retry(prompt: str, max_retries: int = 3):
    """
    Handles the free tier's rate limit (429 errors) gracefully instead of
    crashing the whole batch. Waits longer each retry (backoff), since
    hammering the API immediately after a 429 just makes it worse.
    """
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = (attempt + 1) * 15  # 15s, 30s, 45s
                print(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
            else:
                raise
    raise RuntimeError("Gemini API rate limit exceeded after retries - try again in a minute, or check your daily quota hasn't been hit.")


def score_open_ended_answer(question_id: str, student_answer: str, rubric: dict) -> dict:
    question = rubric["questions"].get(str(question_id))
    if question is None:
        raise ValueError(f"Unknown question id: {question_id}")
    if question["type"] != "open":
        raise ValueError(f"Question {question_id} is not a scored open-ended question - use extract_reflection_answer for reflection questions")

    trait = question["trait"]
    trait_description = rubric["traits"][trait]
    scale = rubric["open_ended_scale"]
    # open_ended_scale has a "_note" key mixed in with the 1-4 levels - keep it out of the prompt
    scale = {k: v for k, v in scale.items() if k != "_note"}

    prompt = build_scoring_prompt(question["prompt"], trait, trait_description, scale, student_answer)
    response = call_with_retry(prompt)

    try:
        parsed = json.loads(response.text.strip())
    except json.JSONDecodeError:
        # TODO: add retry-with-stricter-prompt logic here before this goes live
        raise ValueError(f"Gemini did not return valid JSON for question {question_id}: {response.text}")

    return {
        "question_id": question_id,
        "trait": trait,
        "score": parsed["score"],
        "quoted_evidence": parsed["quoted_evidence"],
        "feedback": parsed["feedback"],
        "raw_student_answer": student_answer,  # kept for the validation layer
    }


def extract_reflection_answer(question_id: str, student_answer: str, rubric: dict) -> dict:
    """
    Q17/Q18 only. No score, no trait - see build_reflection_prompt.
    """
    question = rubric["questions"].get(str(question_id))
    if question is None:
        raise ValueError(f"Unknown question id: {question_id}")
    if question["type"] != "reflection":
        raise ValueError(f"Question {question_id} is not a reflection question - use score_open_ended_answer for trait questions")

    prompt = build_reflection_prompt(question["prompt"], student_answer)
    response = call_with_retry(prompt)

    try:
        parsed = json.loads(response.text.strip())
    except json.JSONDecodeError:
        raise ValueError(f"Gemini did not return valid JSON for question {question_id}: {response.text}")

    return {
        "question_id": question_id,
        "trait": None,
        "score": None,
        "quoted_evidence": parsed["quoted_evidence"],
        "summary": parsed["summary"],
        "raw_student_answer": student_answer,
    }


def score_all_open_ended(open_answers: dict, rubric: dict) -> list[dict]:
    """
    open_answers: {"2": "I would ask the plant if...", "3": "...", ...}
    Only pass trait questions (type "open") here - route 17/18 through
    score_all_reflections instead.
    """
    return [
        score_open_ended_answer(qid, answer, rubric)
        for qid, answer in open_answers.items()
    ]


def score_all_reflections(reflection_answers: dict, rubric: dict) -> list[dict]:
    """
    reflection_answers: {"17": "...", "18": "..."}
    """
    return [
        extract_reflection_answer(qid, answer, rubric)
        for qid, answer in reflection_answers.items()
    ]