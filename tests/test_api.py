import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDENTS_DB", str(tmp_path / "test.db"))
    from app.main import app

    with TestClient(app) as c:  # entering the context runs startup (creates the table)
        yield c


def student(**overrides):
    data = {
        "name": "Aarav Sharma",
        "date_of_birth": "2004-05-17",
        "email": "aarav@example.com",
        "phone": "+91 98765 43210",
        "course": "Python",
    }
    data.update(overrides)
    return data


# ---------- Create ----------
def test_create_student(client):
    r = client.post("/students", json=student())
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1 and body["name"] == "Aarav Sharma"


def test_create_requires_email_or_phone(client):
    r = client.post("/students", json=student(email=None, phone=None))
    assert r.status_code == 422


def test_create_with_only_phone_is_ok(client):
    assert client.post("/students", json=student(email=None)).status_code == 201


@pytest.mark.parametrize(
    "bad",
    [
        {"name": ""},
        {"email": "not-an-email"},
        {"phone": "abc"},
        {"date_of_birth": "2999-01-01"},
        {"date_of_birth": "17-05-2004"},
    ],
)
def test_create_validation_errors(client, bad):
    assert client.post("/students", json=student(**bad)).status_code == 422


def test_duplicate_email_returns_409(client):
    client.post("/students", json=student())
    r = client.post("/students", json=student(name="Someone Else", email="AARAV@example.com"))
    assert r.status_code == 409


# ---------- Read ----------
def test_list_and_filter(client):
    client.post("/students", json=student())
    client.post("/students", json=student(name="Diya Patel", email="diya@example.com",
                                          date_of_birth="2006-01-01", course="Data Science"))
    assert len(client.get("/students").json()) == 2
    assert [s["name"] for s in client.get("/students", params={"name": "diya"}).json()] == ["Diya Patel"]
    assert len(client.get("/students", params={"course": "data"}).json()) == 1
    assert len(client.get("/students", params={"born_after": "2005-01-01"}).json()) == 1


def test_get_student_and_404(client):
    sid = client.post("/students", json=student()).json()["id"]
    assert client.get(f"/students/{sid}").json()["email"] == "aarav@example.com"
    assert client.get("/students/999").status_code == 404


# ---------- Update ----------
def test_put_replaces_record(client):
    sid = client.post("/students", json=student()).json()["id"]
    r = client.put(f"/students/{sid}", json=student(name="Aarav S.", course="Data Science"))
    assert r.status_code == 200 and r.json()["name"] == "Aarav S."
    assert client.put("/students/999", json=student()).status_code == 404


def test_patch_changes_only_given_fields(client):
    sid = client.post("/students", json=student()).json()["id"]
    r = client.patch(f"/students/{sid}", json={"course": "Web Development"})
    assert r.status_code == 200
    assert r.json()["course"] == "Web Development"
    assert r.json()["name"] == "Aarav Sharma"  # untouched


def test_patch_cannot_remove_all_contact_info(client):
    sid = client.post("/students", json=student()).json()["id"]
    r = client.patch(f"/students/{sid}", json={"email": None, "phone": None})
    assert r.status_code == 422
    assert client.get(f"/students/{sid}").json()["email"] == "aarav@example.com"  # unchanged


def test_patch_404(client):
    assert client.patch("/students/999", json={"name": "X"}).status_code == 404


# ---------- Delete ----------
def test_delete(client):
    sid = client.post("/students", json=student()).json()["id"]
    assert client.delete(f"/students/{sid}").status_code == 204
    assert client.get(f"/students/{sid}").status_code == 404
    assert client.delete(f"/students/{sid}").status_code == 404


# ---------- Persistence ----------
def test_data_persists_across_app_restarts(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDENTS_DB", str(tmp_path / "persist.db"))
    from app.main import app

    with TestClient(app) as c:
        sid = c.post("/students", json=student()).json()["id"]
    with TestClient(app) as c2:  # "restart"
        assert c2.get(f"/students/{sid}").json()["name"] == "Aarav Sharma"
