"""All SQL lives here. Every query is parameterised (no string-built values)."""
import sqlite3
from datetime import date
from typing import Optional

COLUMNS = ["name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date"]


def create_student(db: sqlite3.Connection, data: dict) -> dict:
    placeholders = ", ".join("?" for _ in COLUMNS)
    cur = db.execute(
        f"INSERT INTO students ({', '.join(COLUMNS)}) VALUES ({placeholders})",
        [data.get(c) for c in COLUMNS],
    )
    db.commit()
    return get_student(db, cur.lastrowid)


def get_student(db: sqlite3.Connection, student_id: int) -> Optional[dict]:
    row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return dict(row) if row else None


def list_students(
    db: sqlite3.Connection,
    name: Optional[str] = None,
    course: Optional[str] = None,
    email: Optional[str] = None,
    born_after: Optional[date] = None,
    born_before: Optional[date] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    where, params = [], []
    if name:
        where.append("name LIKE ?")
        params.append(f"%{name}%")
    if course:
        where.append("course LIKE ?")
        params.append(f"%{course}%")
    if email:
        where.append("email = ?")
        params.append(email.lower())
    if born_after:  # strictly after
        where.append("date_of_birth > ?")
        params.append(born_after.isoformat())
    if born_before:  # strictly before
        where.append("date_of_birth < ?")
        params.append(born_before.isoformat())

    sql = "SELECT * FROM students"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id LIMIT ? OFFSET ?"
    params += [limit, offset]
    return [dict(r) for r in db.execute(sql, params).fetchall()]


def count_students(db: sqlite3.Connection) -> int:
    return db.execute("SELECT COUNT(*) FROM students").fetchone()[0]


def update_student(db: sqlite3.Connection, student_id: int, data: dict) -> Optional[dict]:
    """Overwrite every editable column with `data` (caller supplies the full record)."""
    assignments = ", ".join(f"{c} = ?" for c in COLUMNS)
    cur = db.execute(
        f"UPDATE students SET {assignments} WHERE id = ?",
        [data.get(c) for c in COLUMNS] + [student_id],
    )
    db.commit()
    if cur.rowcount == 0:
        return None
    return get_student(db, student_id)


def delete_student(db: sqlite3.Connection, student_id: int) -> bool:
    cur = db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    return cur.rowcount > 0
