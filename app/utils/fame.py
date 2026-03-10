from app.database import query_one, execute, commit


def calculate_fame_rating(user_id):
    likes = query_one("SELECT COUNT(*) AS cnt FROM likes WHERE liked_id = %s", (user_id,))
    views = query_one("SELECT COUNT(*) AS cnt FROM profile_views WHERE viewed_id = %s", (user_id,))
    connections = query_one(
        "SELECT COUNT(*) AS cnt FROM likes l1 "
        "JOIN likes l2 ON l1.liked_id = l2.liker_id AND l1.liker_id = l2.liked_id "
        "WHERE l1.liker_id = %s",
        (user_id,),
    )
    rating = (likes["cnt"] * 10) + (views["cnt"] * 1) + (connections["cnt"] * 20)
    return rating


def update_user_fame(user_id):
    rating = calculate_fame_rating(user_id)
    execute("UPDATE users SET fame_rating = %s WHERE id = %s", (rating, user_id))
    commit()
    return rating
