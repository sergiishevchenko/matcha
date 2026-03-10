from types import SimpleNamespace
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.database import query_one, query_all, execute, commit

notifications_bp = Blueprint("notifications", __name__)


def get_notification_text(notif_type, name):
    if notif_type == "like":
        return f"{name} liked your profile"
    elif notif_type == "view":
        return f"{name} viewed your profile"
    elif notif_type == "message":
        return f"{name} sent you a message"
    elif notif_type == "match":
        return f"You and {name} are now connected!"
    elif notif_type == "unlike":
        return f"{name} unliked your profile"
    elif notif_type == "event":
        return f"{name} sent you an event invitation"
    return "New notification"


@notifications_bp.route("/")
@login_required
def index():
    rows = query_all(
        "SELECT n.id, n.type, n.related_user_id, n.is_read, n.created_at, "
        "u.id AS user_id, u.first_name, u.username, u.profile_picture_id, "
        "ui.filename AS pp_filename "
        "FROM notifications n "
        "LEFT JOIN users u ON n.related_user_id = u.id "
        "LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE n.user_id = %s "
        "ORDER BY n.created_at DESC LIMIT 50",
        (current_user.id,),
    )
    notif_data = []
    for r in rows:
        name = r["first_name"] if r["first_name"] else "Someone"
        pp = SimpleNamespace(filename=r["pp_filename"]) if r.get("pp_filename") else None
        notif = SimpleNamespace(
            id=r["id"], type=r["type"], related_user_id=r["related_user_id"],
            is_read=r["is_read"], created_at=r["created_at"],
        )
        user_obj = None
        if r["user_id"]:
            user_obj = SimpleNamespace(
                id=r["user_id"], first_name=r["first_name"],
                username=r["username"], profile_picture=pp,
            )
        notif_data.append({
            "notification": notif,
            "text": get_notification_text(r["type"], name),
            "user": user_obj,
        })
    return render_template("notifications/index.html", notifications=notif_data)


@notifications_bp.route("/count")
@login_required
def count():
    r = query_one(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=%s AND is_read=false",
        (current_user.id,),
    )
    return jsonify({"count": r["cnt"]})


@notifications_bp.route("/mark-read", methods=["POST"])
@login_required
def mark_read():
    data = request.get_json() or {}
    notif_id = data.get("notification_id")
    if notif_id:
        execute(
            "UPDATE notifications SET is_read=true WHERE id=%s AND user_id=%s",
            (int(notif_id), current_user.id),
        )
        commit()
    return jsonify({"success": True})


@notifications_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    execute(
        "UPDATE notifications SET is_read=true WHERE user_id=%s AND is_read=false",
        (current_user.id,),
    )
    commit()
    return jsonify({"success": True})


@notifications_bp.route("/api")
@login_required
def api_list():
    rows = query_all(
        "SELECT n.id, n.type, n.related_user_id, n.is_read, n.created_at, "
        "u.first_name "
        "FROM notifications n "
        "LEFT JOIN users u ON n.related_user_id = u.id "
        "WHERE n.user_id = %s "
        "ORDER BY n.created_at DESC LIMIT 20",
        (current_user.id,),
    )
    result = []
    for r in rows:
        name = r["first_name"] if r["first_name"] else "Someone"
        result.append({
            "id": r["id"],
            "type": r["type"],
            "text": get_notification_text(r["type"], name),
            "related_user_id": r["related_user_id"],
            "is_read": r["is_read"],
            "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M"),
        })
    return jsonify({"notifications": result})
