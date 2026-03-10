import pytest
from app.database import query_one, execute, commit


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
    def test_like_user(self, logged_in_client, user, user2, app):
        response = logged_in_client.post(
            f"/browse/like/{user2}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        with app.app_context():
            like = query_one(
                "SELECT id FROM likes WHERE liked_id = %s", (user2,)
            )
            assert like is not None

    def test_cannot_like_self(self, logged_in_client, user, app):
        response = logged_in_client.post(
            f"/browse/like/{user}",
            follow_redirects=True,
        )
        with app.app_context():
            like = query_one(
                "SELECT id FROM likes WHERE liker_id = %s AND liked_id = %s",
                (user, user),
            )
            assert like is None


class TestUnlike:
    def test_unlike_user(self, logged_in_client, user, user2, app):
        with app.app_context():
            execute(
                "INSERT INTO likes (liker_id, liked_id) VALUES (%s, %s)", (user, user2)
            )
            commit()
        response = logged_in_client.post(
            f"/browse/unlike/{user2}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        with app.app_context():
            like = query_one(
                "SELECT id FROM likes WHERE liker_id = %s AND liked_id = %s",
                (user, user2),
            )
            assert like is None


class TestBlock:
    def test_block_user(self, logged_in_client, user2, app):
        response = logged_in_client.post(
            f"/browse/block/{user2}",
            follow_redirects=True,
        )
        assert response.status_code == 200
        with app.app_context():
            block = query_one(
                "SELECT id FROM blocks WHERE blocked_id = %s", (user2,)
            )
            assert block is not None

    def test_cannot_like_blocked_user(self, logged_in_client, user, user2, app):
        with app.app_context():
            execute(
                "INSERT INTO blocks (blocker_id, blocked_id) VALUES (%s, %s)",
                (user, user2),
            )
            commit()
        response = logged_in_client.post(
            f"/browse/like/{user2}",
            follow_redirects=True,
        )
        assert b"cannot like" in response.data
