import pytest
from app import create_app, db, bcrypt
from app.models import User, Tag, UserTag, Like, Block, Message, Notification


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = "/tmp/test_uploads"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024


@pytest.fixture
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def user(app):
    with app.app_context():
        password_hash = bcrypt.generate_password_hash("Test1234!").decode("utf-8")
        u = User(
            username="testuser",
            email="test@example.com",
            password_hash=password_hash,
            first_name="Test",
            last_name="User",
            email_verified=True,
        )
        db.session.add(u)
        db.session.commit()
        return u.id


@pytest.fixture
def user2(app):
    with app.app_context():
        password_hash = bcrypt.generate_password_hash("Test1234!").decode("utf-8")
        u = User(
            username="testuser2",
            email="test2@example.com",
            password_hash=password_hash,
            first_name="Test2",
            last_name="User2",
            email_verified=True,
        )
        db.session.add(u)
        db.session.commit()
        return u.id


@pytest.fixture
def logged_in_client(client, user, app):
    with app.app_context():
        client.post("/auth/login", data={
            "username": "testuser",
            "password": "Test1234!"
        })
    return client
