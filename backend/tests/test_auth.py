"""
Phase 11 auth: register-or-login, passphrase protection, token verification,
and that a token actually scopes the watchlist to its owner.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.services import auth


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_token_roundtrip_and_tamper_detection():
    token = auth.create_token(42, "alice")
    payload = auth.verify_token(token)
    assert payload["uid"] == 42 and payload["un"] == "alice"
    # Flip a character in the body -> signature no longer matches -> None.
    body, sig = token.split(".")
    assert auth.verify_token(f"{body}x.{sig}") is None
    assert auth.verify_token("garbage") is None


def test_passphrase_hash_is_not_plaintext_and_verifies():
    stored = auth.hash_passphrase("hunter2")
    assert "hunter2" not in stored
    assert auth.verify_passphrase("hunter2", stored) is True
    assert auth.verify_passphrase("wrong", stored) is False


def test_new_username_registers_and_returns_token(client):
    resp = client.post("/api/auth/login", json={"username": "alice"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "alice"
    assert body["is_new"] is True
    assert body["has_passphrase"] is False
    assert auth.verify_token(body["token"])["un"] == "alice"


def test_existing_open_username_logs_in(client):
    client.post("/api/auth/login", json={"username": "bob"})
    resp = client.post("/api/auth/login", json={"username": "bob"})
    assert resp.status_code == 200
    assert resp.json()["is_new"] is False


def test_passphrase_protected_account_requires_correct_passphrase(client):
    client.post("/api/auth/login", json={"username": "carol", "passphrase": "s3cret"})

    # Wrong / missing passphrase -> 401.
    assert client.post("/api/auth/login", json={"username": "carol", "passphrase": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "carol"}).status_code == 401
    # Correct passphrase -> ok.
    assert client.post("/api/auth/login", json={"username": "carol", "passphrase": "s3cret"}).status_code == 200


def test_me_requires_auth_and_returns_username(client):
    assert client.get("/api/auth/me").status_code == 401

    token = client.post("/api/auth/login", json={"username": "dave"}).json()["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "dave"


def test_watchlist_requires_auth(client):
    assert client.get("/api/watchlist").status_code == 401
    assert client.post("/api/watchlist", json={"symbol": "AAPL"}).status_code == 401


def test_watchlist_is_scoped_to_the_token_owner(client):
    alice = client.post("/api/auth/login", json={"username": "alice2"}).json()["token"]
    bob = client.post("/api/auth/login", json={"username": "bob2"}).json()["token"]

    client.post("/api/watchlist", json={"symbol": "AAPL"}, headers={"Authorization": f"Bearer {alice}"})
    client.post("/api/watchlist", json={"symbol": "TSLA"}, headers={"Authorization": f"Bearer {bob}"})

    alice_list = client.get("/api/watchlist", headers={"Authorization": f"Bearer {alice}"}).json()
    bob_list = client.get("/api/watchlist", headers={"Authorization": f"Bearer {bob}"}).json()
    assert [i["symbol"] for i in alice_list] == ["AAPL"]
    assert [i["symbol"] for i in bob_list] == ["TSLA"]


def test_preferences_persist_per_user(client):
    token = client.post("/api/auth/login", json={"username": "erin"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.put("/api/auth/preferences", json={"preferences": {"social": "reddit"}}, headers=headers)
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["preferences"] == {"social": "reddit"}
