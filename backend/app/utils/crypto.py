import os
import hmac
import hashlib
import base64

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")

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
