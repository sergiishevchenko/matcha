from app import db
from app.models import User, Like, ProfileView


def calculate_fame_rating(user_id):
    likes_count = Like.query.filter_by(liked_id=user_id).count()
    views_count = ProfileView.query.filter_by(viewed_id=user_id).count()
    connections = db.session.query(Like).filter(
        Like.liker_id == user_id,
        Like.liked_id.in_(
            db.session.query(Like.liker_id).filter(Like.liked_id == user_id)
        )
    ).count()
    rating = (likes_count * 10) + (views_count * 1) + (connections * 20)
    return rating


def update_user_fame(user_id):
    user = User.query.get(user_id)
    if user:
        user.fame_rating = calculate_fame_rating(user_id)
        db.session.commit()
    return user.fame_rating if user else 0
