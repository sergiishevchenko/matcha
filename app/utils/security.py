import re
import os

COMMON_WORDS_PATH = os.path.join(os.path.dirname(__file__), "common_words.txt")

_common_words = None


def _load_common_words():
    global _common_words
    if _common_words is not None:
        return _common_words
    try:
        with open(COMMON_WORDS_PATH, "r") as f:
            _common_words = set(line.strip().lower() for line in f if line.strip())
    except IOError:
        _common_words = set()
    return _common_words


def is_password_strong(password):
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    words = _load_common_words()
    lower = password.lower()
    for word in words:
        if len(word) >= 4 and word in lower:
            return False, "Password must not contain common English words."
    return True, None


def sanitize_string(value, max_length=255):
    if value is None:
        return None
    s = str(value).strip()
    if len(s) > max_length:
        s = s[:max_length]
    return s if s else None
