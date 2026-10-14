"""Pydantic models: request validation and response shapes."""
import re
from datetime import date
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{6,18}[0-9]$")


class StudentCreate(BaseModel):
    """Full student record. Used for POST and PUT."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "name": "Aarav Sharma",
                "date_of_birth": "2004-05-17",
                "email": "aarav.sharma@example.com",
                "phone": "+91 98765 43210",
                "course": "Python Backend Development",
                "address": "Mumbai, Maharashtra",
                "enrollment_date": "2025-01-10",
            }
        },
    )

    name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    course: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=255)
    enrollment_date: Optional[date] = None

    # Treat "" the same as "not provided".
    @field_validator("email", "phone", "course", "address", "enrollment_date", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v):
        return v.lower() if v else v

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        if v is not None and not PHONE_RE.match(v):
            raise ValueError("phone must be 8-20 characters: digits, spaces, -, (), optional leading +")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, v):
        if v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        if v.year < 1900:
            raise ValueError("date_of_birth must be 1900 or later")
        return v

    @model_validator(mode="after")
    def check_contact_and_dates(self):
        if not self.email and not self.phone:
            raise ValueError("at least one of email or phone is required")
        if self.enrollment_date and self.enrollment_date < self.date_of_birth:
            raise ValueError("enrollment_date cannot be before date_of_birth")
        return self


class StudentUpdate(BaseModel):
    """Partial update for PATCH: send only the fields you want to change.

    The API merges these into the stored record and re-validates the result
    with StudentCreate, so every rule above still applies.
    """

    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None


class StudentOut(BaseModel):
    id: int
    name: str
    date_of_birth: date
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None
    created_at: Optional[str] = None
