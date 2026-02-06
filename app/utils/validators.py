import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


def is_valid_email(email):
    if not email or len(email) > 120:
        return False
    return bool(EMAIL_REGEX.match(email))


def is_valid_username(username):
    if not username or len(username) > 80:
        return False
    return bool(USERNAME_REGEX.match(username))


def is_valid_name(name):
    if not name or len(name) > 80 or len(name) < 1:
        return False
    return bool(re.match(r"^[\w\s'-]+$", name, re.UNICODE))
