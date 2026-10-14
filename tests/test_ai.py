"""Tests for the optional AI extension. Ollama itself is replaced by a stub."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDENTS_DB", str(tmp_path / "ai.db"))
    from app.main import app

    with TestClient(app) as c:
        for name, dob, course in [
            ("Aarav Sharma", "2004-05-17", "Python"),
            ("Diya Patel", "2005-11-02", "Data Science"),
            ("Isha Nair", "2006-08-09", "Python"),
        ]:
            c.post("/students", json={"name": name, "date_of_birth": dob,
                                      "email": f"{name.split()[0].lower()}@example.com", "course": course})
        yield c


def test_context_born_after_year(client, monkeypatch):
    seen = {}

    def fake_ollama(messages):
        seen["prompt"] = messages[-1]["content"]
        return "stub answer"

    monkeypatch.setattr("app.ai.ask_ollama", fake_ollama)
    r = client.post("/ai/ask", json={"question": "List students born after 2005"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "stub answer"
    assert [s["name"] for s in body["records_used"]] == ["Isha Nair"]  # only 2006+
    assert "Aarav" not in seen["prompt"]  # irrelevant records are not sent to the model


def test_context_count_question_includes_total(client, monkeypatch):
    monkeypatch.setattr("app.ai.ask_ollama", lambda m: m[-1]["content"])
    r = client.post("/ai/ask", json={"question": "How many students are there?"})
    assert "Total students in database: 3" in r.json()["answer"]


def test_email_hidden_unless_asked(client, monkeypatch):
    monkeypatch.setattr("app.ai.ask_ollama", lambda m: "ok")
    plain = client.post("/ai/ask", json={"question": "Tell me about Diya"}).json()
    assert "email" not in plain["records_used"][0]
    asked = client.post("/ai/ask", json={"question": "What is Diya's email?"}).json()
    assert asked["records_used"][0]["email"] == "diya@example.com"


def test_ollama_down_returns_503(client):
    import app.ai as ai
    ai.OLLAMA_URL = "http://127.0.0.1:1"  # nothing listens here
    assert client.post("/ai/ask", json={"question": "How many students?"}).status_code == 503
