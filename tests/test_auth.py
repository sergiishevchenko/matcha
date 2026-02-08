import pytest
from app import db
from app.models import User


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
            user = User.query.filter_by(username="newuser").first()
            assert user is not None
            assert user.email == "newuser@example.com"

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


class TestLogout:
    def test_logout(self, logged_in_client):
        response = logged_in_client.get("/auth/logout", follow_redirects=True)
        assert response.status_code == 200
        assert b"logged out" in response.data
