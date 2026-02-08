# Testing Documentation

## Overview

The test suite uses pytest with pytest-flask for Flask integration testing. Tests run against an in-memory SQLite database, so PostgreSQL is not required for testing.

## Setup

Install test dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

Run all tests:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run specific test file:

```bash
pytest tests/test_auth.py
```

Run specific test class:

```bash
pytest tests/test_auth.py::TestRegister
```

Run specific test:

```bash
pytest tests/test_auth.py::TestRegister::test_register_success
```

Run with coverage report:

```bash
pip install pytest-cov
pytest --cov=app --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py        # Shared fixtures
├── test_auth.py       # Authentication tests
├── test_browse.py     # Browse, like, block tests
├── test_models.py     # Database model tests
└── test_utils.py      # Utility function tests
```

## Fixtures (conftest.py)

| Fixture | Description |
|---------|-------------|
| `app` | Flask application with test config (SQLite in-memory) |
| `client` | Flask test client |
| `runner` | CLI test runner |
| `user` | Creates a verified test user (username: `testuser`) |
| `user2` | Creates a second verified test user (username: `testuser2`) |
| `logged_in_client` | Test client with authenticated session |

## Test Files

### test_auth.py

Tests for user authentication flows.

| Test Class | Test | Description |
|------------|------|-------------|
| `TestRegister` | `test_register_page_loads` | Register page returns 200 |
| | `test_register_success` | Valid registration creates user |
| | `test_register_password_mismatch` | Mismatched passwords show error |
| | `test_register_weak_password` | Weak password rejected |
| | `test_register_invalid_email` | Invalid email format rejected |
| | `test_register_invalid_username` | Invalid username format rejected |
| | `test_register_duplicate_email` | Duplicate email rejected |
| `TestLogin` | `test_login_page_loads` | Login page returns 200 |
| | `test_login_success` | Valid credentials log in user |
| | `test_login_wrong_password` | Wrong password shows error |
| | `test_login_nonexistent_user` | Nonexistent user shows error |
| `TestLogout` | `test_logout` | Logout redirects and shows message |

### test_utils.py

Tests for utility functions.

| Test Class | Test | Description |
|------------|------|-------------|
| `TestPasswordStrength` | `test_strong_password` | Valid password passes |
| | `test_short_password` | < 8 chars rejected |
| | `test_no_uppercase` | Missing uppercase rejected |
| | `test_no_lowercase` | Missing lowercase rejected |
| | `test_no_digit` | Missing digit rejected |
| `TestSanitizeString` | `test_strips_whitespace` | Trims leading/trailing spaces |
| | `test_removes_html` | Strips HTML tags |
| | `test_truncates_length` | Respects max length |
| | `test_none_input` | Handles None gracefully |
| `TestValidators` | `test_valid_email` | Valid emails pass |
| | `test_invalid_email` | Invalid emails rejected |
| | `test_valid_username` | Valid usernames pass |
| | `test_invalid_username` | Invalid usernames rejected |
| | `test_valid_name` | Valid names pass |
| | `test_invalid_name` | Invalid names rejected |
| `TestMatching` | `test_calculate_age` | Age calculation correct |
| | `test_calculate_age_none` | None birth date returns None |
| | `test_haversine_distance` | Distance calculation correct |
| | `test_haversine_same_point` | Same point returns 0 |

### test_models.py

Tests for SQLAlchemy models.

| Test Class | Test | Description |
|------------|------|-------------|
| `TestUserModel` | `test_create_user` | User creation with defaults |
| | `test_user_unique_username` | Duplicate username raises error |
| | `test_user_unique_email` | Duplicate email raises error |
| `TestTagModel` | `test_create_tag` | Tag creation works |
| | `test_tag_lowercase` | Tags normalized to lowercase |
| `TestLikeModel` | `test_create_like` | Like creation works |
| | `test_like_unique_constraint` | Duplicate like raises error |
| `TestBlockModel` | `test_create_block` | Block creation works |
| `TestMessageModel` | `test_create_message` | Message creation with defaults |
| `TestNotificationModel` | `test_create_notification` | Notification creation with defaults |

### test_browse.py

Tests for browsing and user interactions.

| Test Class | Test | Description |
|------------|------|-------------|
| `TestSuggestions` | `test_suggestions_requires_login` | Unauthenticated redirected |
| | `test_suggestions_page_loads` | Authenticated user sees page |
| `TestSearch` | `test_search_requires_login` | Unauthenticated redirected |
| | `test_search_page_loads` | Authenticated user sees page |
| `TestLike` | `test_like_user` | Liking creates Like record |
| | `test_cannot_like_self` | Self-like prevented |
| `TestUnlike` | `test_unlike_user` | Unliking removes Like record |
| `TestBlock` | `test_block_user` | Blocking creates Block record |
| | `test_cannot_like_blocked_user` | Cannot like blocked user |

## Test Configuration

Tests use a separate configuration defined in `conftest.py`:

```python
class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    UPLOAD_FOLDER = "/tmp/test_uploads"
```

Key differences from production:
- SQLite in-memory database (no PostgreSQL needed)
- CSRF protection disabled for easier form testing
- Temporary upload folder
