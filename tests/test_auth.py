import pytest
from app.database import query_one, execute, execute_returning, commit


class TestRegister:
    def test_register_page_loads(self, client):
        response = client.get("/auth/register")
        assert response.status_code == 200
        assert b"Register" in response.data

    def test_register_success(self, client, app):
        response = client.post("/auth/register", data={
            "email": "newuser@example.com",
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "password": "Test1234!",
            "password_confirm": "Test1234!",
        }, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            row = query_one("SELECT email FROM users WHERE username = %s", ("newuser",))
            assert row is not None
            assert row["email"] == "newuser@example.com"

    def test_register_password_mismatch(self, client):
        response = client.post("/auth/register", data={
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "Test1234!",
            "password_confirm": "Different1!",
        }, follow_redirects=True)
        assert b"Passwords do not match" in response.data

    def test_register_weak_password(self, client):
        response = client.post("/auth/register", data={
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "weak",
            "password_confirm": "weak",
        }, follow_redirects=True)
        assert b"at least 8 characters" in response.data

    def test_register_invalid_email(self, client):
        response = client.post("/auth/register", data={
            "email": "notanemail",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "Test1234!",
            "password_confirm": "Test1234!",
        }, follow_redirects=True)
        assert b"Invalid email" in response.data

    def test_register_invalid_username(self, client):
        response = client.post("/auth/register", data={
            "email": "test@example.com",
            "username": "ab",
            "first_name": "Test",
            "last_name": "User",
            "password": "Test1234!",
            "password_confirm": "Test1234!",
        }, follow_redirects=True)
        assert b"3-30 characters" in response.data

    def test_register_duplicate_email(self, client, user, app):
        with app.app_context():
            response = client.post("/auth/register", data={
                "email": "test@example.com",
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "password": "Test1234!",
                "password_confirm": "Test1234!",
            }, follow_redirects=True)
            assert b"Email already registered" in response.data


class TestLogin:
    def test_login_page_loads(self, client):
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"Login" in response.data

    def test_login_success(self, client, user, app):
        response = client.post("/auth/login", data={
            "username": "testuser",
            "password": "Test1234!",
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_login_wrong_password(self, client, user):
        response = client.post("/auth/login", data={
            "username": "testuser",
            "password": "WrongPassword1!",
        }, follow_redirects=True)
        assert b"Invalid username or password" in response.data

    def test_login_nonexistent_user(self, client):
        response = client.post("/auth/login", data={
            "username": "nonexistent",
            "password": "Test1234!",
        }, follow_redirects=True)
        assert b"Invalid username or password" in response.data


class TestResendVerification:
    def test_resend_verification_page_loads(self, client):
        response = client.get("/auth/resend-verification")
        assert response.status_code == 200
        assert b"Resend verification" in response.data

    def test_resend_verification_generates_token(self, client, app):
        with app.app_context():
            row = execute_returning(
                "INSERT INTO users (username, email, password_hash, first_name, last_name, "
                "email_verified, gender, biography) "
                "VALUES (%s, %s, %s, %s, %s, false, 'male', 'Test biography') RETURNING id",
                ("unverifieduser", "unverified@example.com", "dummy-hash", "Unverified", "User"),
            )
            commit()
            user_id = row["id"]

        response = client.post("/auth/resend-verification", data={
            "email": "unverified@example.com",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"If an unverified account exists with that email" in response.data

        with app.app_context():
            updated = query_one(
                "SELECT verification_token FROM users WHERE id = %s", (user_id,)
            )
            assert updated["verification_token"] is not None


class TestLogout:
    def test_logout(self, logged_in_client):
        response = logged_in_client.get("/auth/logout", follow_redirects=True)
        assert response.status_code == 200
        assert b"logged out" in response.data
