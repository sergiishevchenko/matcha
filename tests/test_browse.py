import pytest
from app import db
from app.models import User, Like, Block


class TestSuggestions:
    def test_suggestions_requires_login(self, client):
        response = client.get("/browse/suggestions")
        assert response.status_code == 302

    def test_suggestions_page_loads(self, logged_in_client):
        response = logged_in_client.get("/browse/suggestions")
        assert response.status_code == 200


class TestSearch:
    def test_search_requires_login(self, client):
        response = client.get("/browse/search")
        assert response.status_code == 302

    def test_search_page_loads(self, logged_in_client):
        response = logged_in_client.get("/browse/search")
        assert response.status_code == 200


class TestLike:
    def test_like_user(self, logged_in_client, user2, app):
        response = logged_in_client.post(
            f"/browse/like/{user2}",
            follow_redirects=True
        )
        assert response.status_code == 200
        with app.app_context():
            like = Like.query.filter_by(liked_id=user2).first()
            assert like is not None

    def test_cannot_like_self(self, logged_in_client, user, app):
        response = logged_in_client.post(
            f"/browse/like/{user}",
            follow_redirects=True
        )
        with app.app_context():
            like = Like.query.filter_by(liker_id=user, liked_id=user).first()
            assert like is None


class TestUnlike:
    def test_unlike_user(self, logged_in_client, user, user2, app):
        with app.app_context():
            like = Like(liker_id=user, liked_id=user2)
            db.session.add(like)
            db.session.commit()
        response = logged_in_client.post(
            f"/browse/unlike/{user2}",
            follow_redirects=True
        )
        assert response.status_code == 200
        with app.app_context():
            like = Like.query.filter_by(liker_id=user, liked_id=user2).first()
            assert like is None


class TestBlock:
    def test_block_user(self, logged_in_client, user2, app):
        response = logged_in_client.post(
            f"/browse/block/{user2}",
            follow_redirects=True
        )
        assert response.status_code == 200
        with app.app_context():
            block = Block.query.filter_by(blocked_id=user2).first()
            assert block is not None

    def test_cannot_like_blocked_user(self, logged_in_client, user, user2, app):
        with app.app_context():
            block = Block(blocker_id=user, blocked_id=user2)
            db.session.add(block)
            db.session.commit()
        response = logged_in_client.post(
            f"/browse/like/{user2}",
            follow_redirects=True
        )
        assert b"cannot like" in response.data
