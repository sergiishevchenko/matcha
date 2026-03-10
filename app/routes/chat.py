from datetime import datetime, timezone
from types import SimpleNamespace
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from app import socketio
from app.database import query_one, query_all, execute, execute_returning, commit

chat_bp = Blueprint("chat", __name__)


def get_matches(user_id):
    rows = query_all(
        "SELECT u.id, u.username, u.first_name, u.last_name, u.is_online, u.last_seen, "
        "u.profile_picture_id, ui.filename AS pp_filename "
        "FROM users u "
        "LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.id IN ("
        "  SELECT l1.liked_id FROM likes l1 "
        "  JOIN likes l2 ON l1.liker_id = l2.liked_id AND l1.liked_id = l2.liker_id "
        "  WHERE l1.liker_id = %s"
        ") "
        "AND u.id NOT IN (SELECT blocked_id FROM blocks WHERE blocker_id = %s) "
        "AND u.id NOT IN (SELECT blocker_id FROM blocks WHERE blocked_id = %s)",
        (user_id, user_id, user_id),
    )
    result = []
    for r in rows:
        pp = SimpleNamespace(filename=r["pp_filename"]) if r.get("pp_filename") else None
        user = SimpleNamespace(
            id=r["id"], username=r["username"], first_name=r["first_name"],
            last_name=r["last_name"], is_online=r["is_online"], last_seen=r["last_seen"],
            profile_picture_id=r["profile_picture_id"], profile_picture=pp,
        )
        result.append(user)
    return result


def is_match(user1_id, user2_id):
    r = query_one(
        "SELECT 1 FROM likes l1 JOIN likes l2 "
        "ON l1.liker_id = l2.liked_id AND l1.liked_id = l2.liker_id "
        "WHERE l1.liker_id = %s AND l1.liked_id = %s",
        (user1_id, user2_id),
    )
    return r is not None


def is_blocked(user1_id, user2_id):
    r = query_one(
        "SELECT id FROM blocks WHERE "
        "(blocker_id=%s AND blocked_id=%s) OR (blocker_id=%s AND blocked_id=%s)",
        (user1_id, user2_id, user2_id, user1_id),
    )
    return r is not None


def get_conversation(user1_id, user2_id, limit=100):
    rows = query_all(
        "SELECT * FROM messages WHERE "
        "(sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s) "
        "ORDER BY created_at DESC LIMIT %s",
        (user1_id, user2_id, user2_id, user1_id, limit),
    )
    return [SimpleNamespace(**r) for r in reversed(rows)]


def get_unread_count(user_id, from_user_id):
    r = query_one(
        "SELECT COUNT(*) AS cnt FROM messages WHERE sender_id=%s AND receiver_id=%s AND is_read=false",
        (from_user_id, user_id),
    )
    return r["cnt"]


@chat_bp.route("/")
@login_required
def index():
    matches = get_matches(current_user.id)
    matches_data = []
    for m in matches:
        unread = get_unread_count(current_user.id, m.id)
        last_msg_row = query_one(
            "SELECT * FROM messages WHERE "
            "(sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s) "
            "ORDER BY created_at DESC LIMIT 1",
            (current_user.id, m.id, m.id, current_user.id),
        )
        last_msg = SimpleNamespace(**last_msg_row) if last_msg_row else None
        matches_data.append({"user": m, "unread": unread, "last_message": last_msg})
    matches_data.sort(
        key=lambda x: x["last_message"].created_at if x["last_message"] else datetime.min,
        reverse=True,
    )
    return render_template("chat/index.html", matches=matches_data)


@chat_bp.route("/<int:user_id>")
@login_required
def conversation(user_id):
    if user_id == current_user.id:
        return redirect(url_for("chat.index"))
    other_row = query_one(
        "SELECT u.*, ui.filename AS pp_filename, ui.id AS pp_id "
        "FROM users u LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.id = %s",
        (user_id,),
    )
    if not other_row:
        flash("User not found.", "error")
        return redirect(url_for("chat.index"))
    from app.models import make_user
    other = make_user(other_row)
    if not is_match(current_user.id, user_id):
        flash("You can only chat with your matches.", "error")
        return redirect(url_for("chat.index"))
    if is_blocked(current_user.id, user_id):
        flash("Cannot chat with this user.", "error")
        return redirect(url_for("chat.index"))
    execute(
        "UPDATE messages SET is_read=true WHERE sender_id=%s AND receiver_id=%s AND is_read=false",
        (user_id, current_user.id),
    )
    commit()
    messages = get_conversation(current_user.id, user_id)
    matches = get_matches(current_user.id)
    matches_data = []
    for m in matches:
        unread = get_unread_count(current_user.id, m.id)
        matches_data.append({"user": m, "unread": unread})
    return render_template("chat/conversation.html", other=other, messages=messages, matches=matches_data)


@chat_bp.route("/send", methods=["POST"])
@login_required
def send_message():
    data = request.get_json() or {}
    receiver_id = data.get("receiver_id")
    content = data.get("content", "").strip()
    if not receiver_id or not content:
        return jsonify({"success": False, "error": "Invalid data"}), 400
    receiver_id = int(receiver_id)
    if receiver_id == current_user.id:
        return jsonify({"success": False, "error": "Invalid receiver"}), 400
    if not is_match(current_user.id, receiver_id):
        return jsonify({"success": False, "error": "Not a match"}), 403
    if is_blocked(current_user.id, receiver_id):
        return jsonify({"success": False, "error": "Blocked"}), 403
    if len(content) > 2000:
        content = content[:2000]
    msg = execute_returning(
        "INSERT INTO messages (sender_id, receiver_id, content) VALUES (%s, %s, %s) "
        "RETURNING id, created_at",
        (current_user.id, receiver_id, content),
    )
    execute(
        "INSERT INTO notifications (user_id, type, related_user_id, message_id) "
        "VALUES (%s, 'message', %s, %s)",
        (receiver_id, current_user.id, msg["id"]),
    )
    commit()
    room = f"user_{receiver_id}"
    socketio.emit("new_message", {
        "id": msg["id"],
        "sender_id": current_user.id,
        "sender_name": current_user.first_name,
        "content": content,
        "created_at": msg["created_at"].strftime("%Y-%m-%d %H:%M"),
    }, room=room)
    socketio.emit("notification", {
        "type": "message",
        "from_user_id": current_user.id,
        "from_user_name": current_user.first_name,
    }, room=room)
    return jsonify({
        "success": True,
        "message": {
            "id": msg["id"],
            "content": content,
            "created_at": msg["created_at"].strftime("%Y-%m-%d %H:%M"),
        }
    })


@chat_bp.route("/unread-count")
@login_required
def unread_count():
    r = query_one(
        "SELECT COUNT(*) AS cnt FROM messages WHERE receiver_id=%s AND is_read=false",
        (current_user.id,),
    )
    return jsonify({"count": r["cnt"]})


@socketio.on("connect")
def handle_connect():
    from flask_login import current_user as cu
    if cu.is_authenticated:
        join_room(f"user_{cu.id}")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        execute("UPDATE users SET is_online=true, last_seen=%s WHERE id=%s", (now, cu.id))
        commit()


@socketio.on("disconnect")
def handle_disconnect():
    from flask_login import current_user as cu
    if cu.is_authenticated:
        leave_room(f"user_{cu.id}")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        execute("UPDATE users SET is_online=false, last_seen=%s WHERE id=%s", (now, cu.id))
        commit()


@socketio.on("mark_read")
def handle_mark_read(data):
    from flask_login import current_user as cu
    if not cu.is_authenticated:
        return
    sender_id = data.get("sender_id")
    if sender_id:
        execute(
            "UPDATE messages SET is_read=true WHERE sender_id=%s AND receiver_id=%s AND is_read=false",
            (int(sender_id), cu.id),
        )
        commit()
