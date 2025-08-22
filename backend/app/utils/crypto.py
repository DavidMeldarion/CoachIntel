import os
import hmac
import hashlib
import base64
from functools import lru_cache
from typing import Union, Optional

from cryptography.fernet import Fernet, InvalidToken

try:
    import phonenumbers  # type: ignore
except ImportError:  # lightweight fallback if phonenumbers not installed
    phonenumbers = None  # pragma: no cover

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")
FERNET_KEY = os.getenv("FERNET_KEY")  # must be a 32-byte urlsafe base64 key

_DEF_PAD = {0: '', 2: '==', 3: '='}

def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip('=')

def _b64url_decode(s: str) -> bytes:
    pad = _DEF_PAD[len(s) % 4]
    return base64.urlsafe_b64decode(s + pad)

def sign_hmac_token(text: str) -> str:
    mac = hmac.new(SECRET_KEY.encode('utf-8'), text.encode('utf-8'), hashlib.sha256).digest()
    return _b64url_encode(mac)

def verify_hmac_token(text: str, token: str) -> bool:
    try:
        expected = sign_hmac_token(text)
        return hmac.compare_digest(expected, token)
    except Exception:
        return False


# ---------------------------
# Fernet helpers
# ---------------------------
@lru_cache(maxsize=1)
def fernet() -> Fernet:
    if not FERNET_KEY:
        raise RuntimeError("FERNET_KEY environment variable is required for encryption")
    # Validate length (should decode to 32 bytes)
    try:
        key_bytes = base64.urlsafe_b64decode(FERNET_KEY)
        if len(key_bytes) != 32:
            raise ValueError
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("FERNET_KEY must be a urlsafe base64-encoded 32 byte key") from e
    return Fernet(FERNET_KEY)

def encrypt(data: Union[str, bytes]) -> bytes:
    """Encrypt a string or bytes, returning ciphertext bytes."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return fernet().encrypt(data)

def decrypt(token: bytes) -> str:
    """Decrypt ciphertext bytes returning UTF-8 string. Raises on invalid token."""
    try:
        return fernet().decrypt(token).decode('utf-8')
    except InvalidToken as e:
        raise ValueError("Invalid encryption token") from e


# ---------------------------
# Email hashing (PII lookup) – deterministic lowercase/trim SHA-256 hex
# ---------------------------
def hash_email(email: str) -> str:
    normalized = (email or '').strip().lower()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


# ---------------------------
# Phone hashing (after E.164 normalization)
# ---------------------------
def hash_phone(phone: str) -> Optional[str]:
    normalized = e164(phone)
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


# ---------------------------
# Phone normalization to E.164
# ---------------------------
def e164(phone: str, default_region: str = 'US') -> Optional[str]:
    if not phone:
        return None
    if not phonenumbers:  # fallback naive normalization
        digits = ''.join(ch for ch in phone if ch.isdigit() or ch == '+')
        if digits.startswith('+') and 8 <= len(digits) <= 16:
            return digits
        return None
    try:
        parsed = phonenumbers.parse(phone, None if phone.startswith('+') else default_region)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:  # pragma: no cover
        return None

__all__ = [
    'sign_hmac_token', 'verify_hmac_token', 'fernet', 'encrypt', 'decrypt', 'hash_email', 'hash_phone', 'e164'
]
