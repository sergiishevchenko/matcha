from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Notification, User

notifications_bp = Blueprint("notifications", __name__)


def get_notification_text(notif):
    user = User.query.get(notif.related_user_id) if notif.related_user_id else None
    name = user.first_name if user else "Someone"
    if notif.type == "like":
        return f"{name} liked your profile"
    elif notif.type == "view":
        return f"{name} viewed your profile"
    elif notif.type == "message":
        return f"{name} sent you a message"
    elif notif.type == "match":
        return f"You and {name} are now connected!"
    elif notif.type == "unlike":
        return f"{name} unliked your profile"
    elif notif.type == "event":
        return f"{name} sent you an event invitation"
    return "New notification"


@notifications_bp.route("/")
@login_required
def index():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    notif_data = []
    for n in notifications:
        user = User.query.get(n.related_user_id) if n.related_user_id else None
        notif_data.append({
            "notification": n,
            "text": get_notification_text(n),
            "user": user,
        })
    return render_template("notifications/index.html", notifications=notif_data)


@notifications_bp.route("/count")
@login_required
def count():
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"count": unread})


@notifications_bp.route("/mark-read", methods=["POST"])
@login_required
def mark_read():
    data = request.get_json() or {}
    notif_id = data.get("notification_id")
    if notif_id:
        notif = Notification.query.filter_by(id=int(notif_id), user_id=current_user.id).first()
        if notif:
            notif.is_read = True
            db.session.commit()
    return jsonify({"success": True})


@notifications_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True})


@notifications_bp.route("/api")
@login_required
def api_list():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(20).all()
    result = []
    for n in notifications:
        result.append({
            "id": n.id,
            "type": n.type,
            "text": get_notification_text(n),
            "related_user_id": n.related_user_id,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return jsonify({"notifications": result})
