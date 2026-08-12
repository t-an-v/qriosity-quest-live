# Qriosity Quest Scoring Pipeline

Early sketch of the scoring pipeline: rule-based MCQ scoring, Gemini-based
open-ended scoring, and a validation layer before anything reaches a report.

## Structure

- `data/rubric.json` — the trait rubric, one entry per question. Includes
  question text, scoring criteria (1-4), and trait mapping.
- `app/mcq_scorer.py` — deterministic scoring for MCQ answers. No LLM calls.
- `app/open_ended_scorer.py` — Gemini scoring for open-ended answers, using
  structured JSON prompting (same pattern as the privacy policy grader).
- `app/validator.py` — hallucination guard. Checks every quote Gemini claims
  came from the student's answer against what they actually wrote.
- `app/pipeline.py` — orchestrates all three above, returns one structured result.
- `app/main.py` — minimal FastAPI wrapper, one `/score` endpoint.

## Not built yet (intentionally)

- Login / auth / test-taking UI — building this last, once scoring is proven.
- Report generation (turning `trait_totals` into the actual Letter to
  Parents / Teacher's Lens / Leadership Compass formats).
- Duplicate-answer / anti-copying detection — deprioritized per founder.
- Retry logic if Gemini returns malformed JSON.

## Known open items (need founder confirmation before this is final)

1. `rubric.json` — most MCQ questions only have ONE option's score confirmed
   (marked `null` for the rest). These are placeholders, not guesses baked
   into the system — the pipeline will flag any submission that hits an
   unconfirmed option rather than silently scoring it wrong.
2. `level_bands` in rubric.json — the Dormant/Developing/Strong/Excelling
   percentage cutoffs are a working theory from pattern-matching one sample
   report, not confirmed.
3. Question 6's trait mapping (Insight Seeker) was inferred by position,
   not verified against real scored content — flagged in rubric.json.
4. Gemini model choice (`gemini-1.5-flash` in open_ended_scorer.py) is a
   placeholder — worth revisiting once we know actual volume/cost needs.

## Running locally

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
uvicorn app.main:app --reload
```

Then POST to `/score` with `mcq_answers` and `open_answers` dicts.
