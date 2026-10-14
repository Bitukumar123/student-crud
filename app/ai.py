"""OPTIONAL BONUS: ask natural-language questions about the data using a local Ollama model.

Safety design:
  * The model NEVER writes or runs SQL.
  * Our own code decides which records are relevant (simple, fixed rules),
    fetches them with the same parameterised queries the API uses,
    and hands them to the model as read-only context.
  * Contact details (email/phone) are only included if the question asks for them.
"""
import os
import re
import sqlite3
from datetime import date
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import crud
from .database import get_db

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
MAX_CONTEXT_RECORDS = 50

router = APIRouter(prefix="/ai", tags=["ai (optional)"])


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500, examples=["How many students are there?"])


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    filters_applied: list[str]
    records_used: list[dict]


def retrieve_context(db: sqlite3.Connection, question: str) -> dict:
    """Pick relevant records using fixed rules (no model involved)."""
    q = question.lower()
    filters: list[str] = []
    born_after: Optional[date] = None
    born_before: Optional[date] = None

    m = re.search(r"born\s+(after|before|in)\s+(\d{4})", q)
    if m:
        kind, year = m.group(1), int(m.group(2))
        if kind == "after":
            born_after = date(year, 12, 31)
            filters.append(f"born after year {year} (i.e. {year + 1} onwards)")
        elif kind == "before":
            born_before = date(year, 1, 1)
            filters.append(f"born before year {year}")
        else:
            born_after, born_before = date(year - 1, 12, 31), date(year + 1, 1, 1)
            filters.append(f"born in {year}")

    students = crud.list_students(
        db, born_after=born_after, born_before=born_before, limit=MAX_CONTEXT_RECORDS
    )
    everyone = crud.list_students(db, limit=500)

    # Course mentioned in the question?
    courses = {s["course"] for s in everyone if s["course"]}
    for course in courses:
        if course.lower() in q:
            students = [s for s in students if s["course"] == course]
            filters.append(f"course = {course}")

    # Student first/full name mentioned in the question?
    named = [
        s for s in everyone
        if s["name"].lower() in q
        or any(len(p) > 2 and re.search(rf"\b{re.escape(p)}\b", q) for p in s["name"].lower().split()[:1])
    ]
    if named:
        students = named[:MAX_CONTEXT_RECORDS]
        filters.append("name mentioned in question")

    wants_contact = any(w in q for w in ("email", "phone", "contact", "mobile", "number"))
    keep = ["id", "name", "date_of_birth", "course", "enrollment_date"]
    if wants_contact:
        keep += ["email", "phone"]

    return {
        "total_students": crud.count_students(db),
        "matched_count": len(students),
        "filters": filters,
        "students": [{k: s.get(k) for k in keep} for s in students],
    }


def build_prompt(question: str, context: dict) -> list[dict]:
    lines = [
        f"Total students in database: {context['total_students']}",
        f"Students matching the question's filters: {context['matched_count']}",
        f"Filters applied: {', '.join(context['filters']) or 'none'}",
        "Matching records:",
    ]
    lines += [str(s) for s in context["students"]] or ["(none)"]
    system = (
        "You answer questions about a student database. Use ONLY the data provided. "
        "Copy numbers and names exactly as given. If the data does not contain the answer, "
        "say you don't know. Keep the answer short and clear."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "DATA:\n" + "\n".join(lines) + f"\n\nQUESTION: {question}"},
    ]


def ask_ollama(messages: list[dict]) -> str:
    """Call the local Ollama server. Kept separate so tests can replace it."""
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": messages, "stream": False,
                  "options": {"temperature": 0}},
            timeout=120,
        )
        resp.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(503, f"Cannot reach Ollama at {OLLAMA_URL}. Start it with `ollama serve`.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            502, f"Ollama returned {exc.response.status_code}. Did you run `ollama pull {OLLAMA_MODEL}`?"
        )
    except httpx.TimeoutException:
        raise HTTPException(504, "Ollama took too long to respond.")
    return resp.json()["message"]["content"].strip()


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, db: sqlite3.Connection = Depends(get_db)):
    context = retrieve_context(db, body.question)
    answer = ask_ollama(build_prompt(body.question, context))
    return AskResponse(
        question=body.question,
        answer=answer,
        model=OLLAMA_MODEL,
        filters_applied=context["filters"],
        records_used=context["students"],
    )
