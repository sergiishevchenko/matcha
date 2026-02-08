import pytest
from app.utils.security import is_password_strong, sanitize_string
from app.utils.validators import is_valid_email, is_valid_username, is_valid_name
from app.utils.matching import calculate_age, haversine_distance
from datetime import date


class TestPasswordStrength:
    def test_strong_password(self):
        ok, err = is_password_strong("Test1234!")
        assert ok is True
        assert err is None

    def test_short_password(self):
        ok, err = is_password_strong("Test1!")
        assert ok is False
        assert "8 characters" in err

    def test_no_uppercase(self):
        ok, err = is_password_strong("test1234!")
        assert ok is False
        assert "uppercase" in err

    def test_no_lowercase(self):
        ok, err = is_password_strong("TEST1234!")
        assert ok is False
        assert "lowercase" in err

    def test_no_digit(self):
        ok, err = is_password_strong("TestTest!")
        assert ok is False
        assert "digit" in err


class TestSanitizeString:
    def test_strips_whitespace(self):
        assert sanitize_string("  hello  ", 100) == "hello"

    def test_removes_html(self):
        result = sanitize_string("<script>alert('xss')</script>hello", 100)
        assert "<script>" not in result

    def test_truncates_length(self):
        result = sanitize_string("a" * 200, 50)
        assert len(result) <= 50

    def test_none_input(self):
        assert sanitize_string(None, 100) == ""


class TestValidators:
    def test_valid_email(self):
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("user.name+tag@domain.co.uk") is True

    def test_invalid_email(self):
        assert is_valid_email("notanemail") is False
        assert is_valid_email("@example.com") is False
        assert is_valid_email("test@") is False
        assert is_valid_email("") is False

    def test_valid_username(self):
        assert is_valid_username("john_doe123") is True
        assert is_valid_username("abc") is True

    def test_invalid_username(self):
        assert is_valid_username("ab") is False
        assert is_valid_username("a" * 31) is False
        assert is_valid_username("user@name") is False
        assert is_valid_username("user name") is False

    def test_valid_name(self):
        assert is_valid_name("John") is True
        assert is_valid_name("Mary-Jane") is True
        assert is_valid_name("O'Connor") is True

    def test_invalid_name(self):
        assert is_valid_name("") is False
        assert is_valid_name("a" * 81) is False


class TestMatching:
    def test_calculate_age(self):
        today = date.today()
        birth = date(today.year - 25, today.month, today.day)
        assert calculate_age(birth) == 25

    def test_calculate_age_none(self):
        assert calculate_age(None) is None

    def test_haversine_distance(self):
        zurich = (47.3769, 8.5417)
        geneva = (46.2044, 6.1432)
        distance = haversine_distance(zurich[0], zurich[1], geneva[0], geneva[1])
        assert 220 < distance < 230

    def test_haversine_same_point(self):
        distance = haversine_distance(47.0, 8.0, 47.0, 8.0)
        assert distance == 0
