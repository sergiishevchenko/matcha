import pytest
from app import db
from app.models import User, Tag, UserTag, Like, Block, Message, Notification


class TestUserModel:
    def test_create_user(self, app):
        with app.app_context():
            user = User(
                username="modeltest",
                email="model@test.com",
                password_hash="hash",
                first_name="Model",
                last_name="Test",
            )
            db.session.add(user)
            db.session.commit()
            assert user.id is not None
            assert user.fame_rating == 0
            assert user.email_verified is False

    def test_user_unique_username(self, app, user):
        with app.app_context():
            user2 = User(
                username="testuser",
                email="different@test.com",
                password_hash="hash",
                first_name="Test",
                last_name="User",
            )
            db.session.add(user2)
            with pytest.raises(Exception):
                db.session.commit()

    def test_user_unique_email(self, app, user):
        with app.app_context():
            user2 = User(
                username="different",
                email="test@example.com",
                password_hash="hash",
                first_name="Test",
                last_name="User",
            )
            db.session.add(user2)
            with pytest.raises(Exception):
                db.session.commit()


class TestTagModel:
    def test_create_tag(self, app):
        with app.app_context():
            tag = Tag(name="hiking")
            db.session.add(tag)
            db.session.commit()
            assert tag.id is not None
            assert tag.name == "hiking"

    def test_tag_lowercase(self, app):
        with app.app_context():
            tag = Tag(name="HIKING")
            db.session.add(tag)
            db.session.commit()
            assert tag.name == "hiking"


class TestLikeModel:
    def test_create_like(self, app, user, user2):
        with app.app_context():
            like = Like(liker_id=user, liked_id=user2)
            db.session.add(like)
            db.session.commit()
            assert like.id is not None

    def test_like_unique_constraint(self, app, user, user2):
        with app.app_context():
            like1 = Like(liker_id=user, liked_id=user2)
            db.session.add(like1)
            db.session.commit()
            like2 = Like(liker_id=user, liked_id=user2)
            db.session.add(like2)
            with pytest.raises(Exception):
                db.session.commit()


class TestBlockModel:
    def test_create_block(self, app, user, user2):
        with app.app_context():
            block = Block(blocker_id=user, blocked_id=user2)
            db.session.add(block)
            db.session.commit()
            assert block.id is not None


class TestMessageModel:
    def test_create_message(self, app, user, user2):
        with app.app_context():
            msg = Message(
                sender_id=user,
                receiver_id=user2,
                content="Hello!"
            )
            db.session.add(msg)
            db.session.commit()
            assert msg.id is not None
            assert msg.is_read is False


class TestNotificationModel:
    def test_create_notification(self, app, user, user2):
        with app.app_context():
            notif = Notification(
                user_id=user,
                type="like",
                related_user_id=user2
            )
            db.session.add(notif)
            db.session.commit()
            assert notif.id is not None
            assert notif.is_read is False
