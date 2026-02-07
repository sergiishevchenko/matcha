from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models import User, Block, UserImage

map_bp = Blueprint("map", __name__)


@map_bp.route("/")
@login_required
def index():
    return render_template("map/index.html")


@map_bp.route("/users")
@login_required
def users_json():
    blocked_ids = [b.blocked_id for b in Block.query.filter_by(blocker_id=current_user.id).all()]
    blocked_by_ids = [b.blocker_id for b in Block.query.filter_by(blocked_id=current_user.id).all()]
    exclude_ids = set(blocked_ids + blocked_by_ids + [current_user.id])
    users = User.query.filter(
        User.email_verified == True,
        User.latitude.isnot(None),
        User.longitude.isnot(None),
        ~User.id.in_(exclude_ids)
    ).limit(200).all()
    result = []
    for u in users:
        img = UserImage.query.filter_by(user_id=u.id, is_profile_picture=True).first()
        result.append({
            "id": u.id,
            "username": u.username,
            "first_name": u.first_name,
            "age": None,
            "lat": u.latitude,
            "lng": u.longitude,
            "is_online": u.is_online,
            "photo": img.filename if img else None,
        })
    return jsonify(result)
