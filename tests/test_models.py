import pytest
from app.database import query_one, execute, execute_returning, commit


class TestUserModel:
    def test_create_user(self, app):
        with app.app_context():
            row = execute_returning(
                "INSERT INTO users (username, email, password_hash, first_name, last_name) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id, fame_rating, email_verified",
                ("modeltest", "model@test.com", "hash", "Model", "Test"),
            )
            commit()
            assert row["id"] is not None
            assert row["fame_rating"] == 0
            assert row["email_verified"] is False

    def test_user_unique_username(self, app, user):
        with app.app_context():
            with pytest.raises(Exception):
                execute(
                    "INSERT INTO users (username, email, password_hash, first_name, last_name) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    ("testuser", "different@test.com", "hash", "Test", "User"),
                )
                commit()

    def test_user_unique_email(self, app, user):
        with app.app_context():
            with pytest.raises(Exception):
                execute(
                    "INSERT INTO users (username, email, password_hash, first_name, last_name) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    ("different", "test@example.com", "hash", "Test", "User"),
                )
                commit()


class TestTagModel:
    def test_create_tag(self, app):
        with app.app_context():
            row = execute_returning(
                "INSERT INTO tags (name) VALUES (%s) RETURNING id, name", ("hiking",)
            )
            commit()
            assert row["id"] is not None
            assert row["name"] == "hiking"


class TestLikeModel:
    def test_create_like(self, app, user, user2):
        with app.app_context():
            row = execute_returning(
                "INSERT INTO likes (liker_id, liked_id) VALUES (%s, %s) RETURNING id",
                (user, user2),
            )
            commit()
            assert row["id"] is not None

    def test_like_unique_constraint(self, app, user, user2):
        with app.app_context():
            execute("INSERT INTO likes (liker_id, liked_id) VALUES (%s, %s)", (user, user2))
            commit()
            with pytest.raises(Exception):
                execute("INSERT INTO likes (liker_id, liked_id) VALUES (%s, %s)", (user, user2))
                commit()


class TestBlockModel:
    def test_create_block(self, app, user, user2):
        with app.app_context():
            row = execute_returning(
                "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s, %s) RETURNING id",
                (user, user2),
            )
            commit()
            assert row["id"] is not None


class TestMessageModel:
    def test_create_message(self, app, user, user2):
        with app.app_context():
            row = execute_returning(
                "INSERT INTO messages (sender_id, receiver_id, content) "
                "VALUES (%s, %s, %s) RETURNING id, is_read",
                (user, user2, "Hello!"),
            )
            commit()
            assert row["id"] is not None
            assert row["is_read"] is False


class TestNotificationModel:
    def test_create_notification(self, app, user, user2):
        with app.app_context():
            row = execute_returning(
                "INSERT INTO notifications (user_id, type, related_user_id) "
                "VALUES (%s, %s, %s) RETURNING id, is_read",
                (user, "like", user2),
            )
            commit()
            assert row["id"] is not None
            assert row["is_read"] is False
