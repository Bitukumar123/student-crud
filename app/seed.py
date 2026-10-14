"""Load DUMMY sample data (all fictional). Run:  python -m app.seed"""
import sqlite3

from . import crud
from .database import connect, init_db

SAMPLE = [
    ("Aarav Sharma", "2004-05-17", "aarav.sharma@example.com", "+91 98765 43210", "Python Backend Development", "Mumbai", "2025-01-10"),
    ("Diya Patel", "2005-11-02", "diya.patel@example.com", "+91 91234 56780", "Data Science", "Pune", "2025-01-10"),
    ("Rohan Mehta", "2003-02-28", "rohan.mehta@example.com", None, "Python Backend Development", "Thane", "2024-07-15"),
    ("Isha Nair", "2006-08-09", "isha.nair@example.com", "+91 99887 76655", "Web Development", "Navi Mumbai", "2025-06-01"),
    ("Kabir Singh", "2002-12-21", None, "+91 90000 11122", "Data Science", "Delhi", "2024-07-15"),
    ("Meera Iyer", "2005-03-30", "meera.iyer@example.com", None, "Web Development", "Chennai", "2025-06-01"),
    ("Vikram Rao", "2007-01-14", "vikram.rao@example.com", "+91 98111 22233", "Python Backend Development", "Bengaluru", "2025-09-01"),
    ("Sara Khan", "2004-09-05", "sara.khan@example.com", "+91 97000 33344", "Data Science", "Hyderabad", "2025-01-10"),
]
KEYS = ["name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date"]


def main() -> None:
    init_db()
    db = connect()
    added = 0
    for row in SAMPLE:
        try:
            crud.create_student(db, dict(zip(KEYS, row)))
            added += 1
        except sqlite3.IntegrityError:
            pass  # already seeded
    db.close()
    print(f"Seeded {added} dummy students ({len(SAMPLE) - added} already present).")


if __name__ == "__main__":
    main()
