"""
Minimal FastAPI app exposing the scoring pipeline.
This is intentionally bare right now - no auth, no database, no login flow.
Those come later, once the scoring logic itself is proven and confirmed.
"""

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.pipeline import run_pipeline

app = FastAPI(title="Qriosity Quest Scoring Pipeline")

origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SubmissionRequest(BaseModel):
    mcq_answers: dict[str, str]   # {"1": "b", "4": "b", ...}
    open_answers: dict[str, str]  # {"2": "...", "3": "...", ...}


@app.post("/score")
def score_submission(submission: SubmissionRequest):
    return run_pipeline(submission.mcq_answers, submission.open_answers)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    headers = {
        "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=headers,
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}
