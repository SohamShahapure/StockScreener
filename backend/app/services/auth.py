"""
Phase 11 authentication primitives - deliberately dependency-free (stdlib
only): salted PBKDF2 passphrase hashing and HMAC-signed stateless tokens.

The token is a compact `body.signature` string (JWT-ish but without the
extra deps): the body is a base64url JSON payload, the signature is an
HMAC-SHA256 over that body keyed by SECRET_KEY. Because it's signed, a
client can't tamper with the user id inside it; because it's stateless, we
don't need a server-side session table. This is intentionally simple - it
matches the low-friction "unique identifier" login the project opted for,
not a bank.
"""
import base64
import hashlib
import hmac
import json
import time

from app.core.config import settings

_PBKDF2_ROUNDS = 100_000


# --- Passphrase hashing ---------------------------------------------------

def hash_passphrase(passphrase: str) -> str:
    salt = hashlib.sha256(str(time.time_ns()).encode() + passphrase.encode()).digest()[:16]
    dk = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${dk.hex()}"


def verify_passphrase(passphrase: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, AttributeError):
        return False


# --- Signed tokens --------------------------------------------------------

def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(body: str) -> str:
    return _b64e(hmac.new(settings.SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest())


def create_token(user_id: int, username: str) -> str:
    body = _b64e(json.dumps({"uid": user_id, "un": username, "iat": int(time.time())}, separators=(",", ":")).encode())
    return f"{body}.{_sign(body)}"


def verify_token(token: str) -> dict | None:
    """Returns the decoded payload if the signature checks out, else None."""
    try:
        body, sig = token.split(".", 1)
    except (ValueError, AttributeError):
        return None
    if not hmac.compare_digest(sig, _sign(body)):
        return None
    try:
        return json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError):
        return None
