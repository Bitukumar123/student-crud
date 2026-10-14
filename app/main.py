"""FastAPI application: Students Database CRUD."""
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import ValidationError

from . import crud
from .ai import router as ai_router
from .database import get_db, init_db
from .schemas import StudentCreate, StudentOut, StudentUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create the table on startup if it does not exist yet
    yield


app = FastAPI(
    title="Students Database API",
    description="CRUD API for student records (FastAPI + SQLite), with an optional local-AI endpoint.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(ai_router)


def _not_found(student_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Student with id {student_id} not found")


def _duplicate_email() -> HTTPException:
    return HTTPException(status_code=409, detail="A student with this email already exists")


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "docs": "/docs"}


# ---------- Create ----------
@app.post("/students", response_model=StudentOut, status_code=201, tags=["students"])
def create_student(student: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        return crud.create_student(db, student.model_dump(mode="json"))
    except sqlite3.IntegrityError:
        raise _duplicate_email()


# ---------- Read ----------
@app.get("/students", response_model=list[StudentOut], tags=["students"])
def list_students(
    name: Optional[str] = Query(None, description="Partial, case-insensitive name match"),
    course: Optional[str] = Query(None, description="Partial, case-insensitive course match"),
    email: Optional[str] = Query(None, description="Exact email match"),
    born_after: Optional[date] = Query(None, description="Date of birth strictly after this date"),
    born_before: Optional[date] = Query(None, description="Date of birth strictly before this date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    return crud.list_students(db, name, course, email, born_after, born_before, limit, offset)


@app.get("/students/{student_id}", response_model=StudentOut, tags=["students"])
def get_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    student = crud.get_student(db, student_id)
    if student is None:
        raise _not_found(student_id)
    return student


# ---------- Update ----------
@app.put("/students/{student_id}", response_model=StudentOut, tags=["students"])
def replace_student(student_id: int, student: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    """Full update: the body must contain the complete record."""
    try:
        updated = crud.update_student(db, student_id, student.model_dump(mode="json"))
    except sqlite3.IntegrityError:
        raise _duplicate_email()
    if updated is None:
        raise _not_found(student_id)
    return updated


@app.patch("/students/{student_id}", response_model=StudentOut, tags=["students"])
def patch_student(student_id: int, changes: StudentUpdate, db: sqlite3.Connection = Depends(get_db)):
    """Partial update: send only the fields to change."""
    existing = crud.get_student(db, student_id)
    if existing is None:
        raise _not_found(student_id)

    merged = {c: existing.get(c) for c in crud.COLUMNS}
    merged.update(changes.model_dump(mode="json", exclude_unset=True))
    try:  # re-run every validation rule on the merged record
        validated = StudentCreate(**merged)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json()))

    try:
        return crud.update_student(db, student_id, validated.model_dump(mode="json"))
    except sqlite3.IntegrityError:
        raise _duplicate_email()


# ---------- Delete ----------
@app.delete("/students/{student_id}", status_code=204, tags=["students"])
def delete_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    if not crud.delete_student(db, student_id):
        raise _not_found(student_id)
    return Response(status_code=204)
