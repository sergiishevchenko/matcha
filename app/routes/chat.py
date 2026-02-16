from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from app import db, socketio
from app.models import User, Message, Like, Block, Notification

chat_bp = Blueprint("chat", __name__)


def get_matches(user_id):
    my_likes = db.session.query(Like.liked_id).filter(Like.liker_id == user_id)
    liked_me = db.session.query(Like.liker_id).filter(Like.liked_id == user_id)
    match_ids = my_likes.intersect(liked_me).all()
    match_ids = [m[0] for m in match_ids]
    blocked_by_me = db.session.query(Block.blocked_id).filter(Block.blocker_id == user_id)
    blocked_me = db.session.query(Block.blocker_id).filter(Block.blocked_id == user_id)
    matches = User.query.filter(
        User.id.in_(match_ids),
        User.id.notin_(blocked_by_me),
        User.id.notin_(blocked_me),
    ).all()
    return matches


def is_match(user1_id, user2_id):
    like1 = Like.query.filter_by(liker_id=user1_id, liked_id=user2_id).first()
    like2 = Like.query.filter_by(liker_id=user2_id, liked_id=user1_id).first()
    return like1 is not None and like2 is not None


def is_blocked(user1_id, user2_id):
    b1 = Block.query.filter_by(blocker_id=user1_id, blocked_id=user2_id).first()
    b2 = Block.query.filter_by(blocker_id=user2_id, blocked_id=user1_id).first()
    return b1 is not None or b2 is not None


def get_conversation(user1_id, user2_id, limit=100):
    messages = Message.query.filter(
        ((Message.sender_id == user1_id) & (Message.receiver_id == user2_id)) |
        ((Message.sender_id == user2_id) & (Message.receiver_id == user1_id))
    ).order_by(Message.created_at.desc()).limit(limit).all()
    return list(reversed(messages))


def get_unread_count(user_id, from_user_id):
    return Message.query.filter_by(
        sender_id=from_user_id,
        receiver_id=user_id,
        is_read=False
    ).count()


@chat_bp.route("/")
@login_required
def index():
    matches = get_matches(current_user.id)
    matches_data = []
    for m in matches:
        unread = get_unread_count(current_user.id, m.id)
        last_msg = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == m.id)) |
            ((Message.sender_id == m.id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.created_at.desc()).first()
        matches_data.append({
            "user": m,
            "unread": unread,
            "last_message": last_msg,
        })
    matches_data.sort(key=lambda x: x["last_message"].created_at if x["last_message"] else datetime.min, reverse=True)
    return render_template("chat/index.html", matches=matches_data)


@chat_bp.route("/<int:user_id>")
@login_required
def conversation(user_id):
    if user_id == current_user.id:
        return redirect(url_for("chat.index"))
    other = db.get_or_404(User, user_id)
    if not is_match(current_user.id, user_id):
        flash("You can only chat with your matches.", "error")
        return redirect(url_for("chat.index"))
    if is_blocked(current_user.id, user_id):
        flash("Cannot chat with this user.", "error")
        return redirect(url_for("chat.index"))
    Message.query.filter_by(sender_id=user_id, receiver_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
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
    msg = Message(sender_id=current_user.id, receiver_id=receiver_id, content=content)
    db.session.add(msg)
    notif = Notification(user_id=receiver_id, type="message", related_user_id=current_user.id, message_id=msg.id)
    db.session.add(notif)
    db.session.commit()
    room = f"user_{receiver_id}"
    socketio.emit("new_message", {
        "id": msg.id,
        "sender_id": current_user.id,
        "sender_name": current_user.first_name,
        "content": msg.content,
        "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M"),
    }, room=room)
    socketio.emit("notification", {
        "type": "message",
        "from_user_id": current_user.id,
        "from_user_name": current_user.first_name,
    }, room=room)
    return jsonify({
        "success": True,
        "message": {
            "id": msg.id,
            "content": msg.content,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M"),
        }
    })


@chat_bp.route("/unread-count")
@login_required
def unread_count():
    count = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False
    ).count()
    return jsonify({"count": count})


@socketio.on("connect")
def handle_connect():
    from flask_login import current_user
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")
        current_user.is_online = True
        current_user.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()


@socketio.on("disconnect")
def handle_disconnect():
    from flask_login import current_user
    if current_user.is_authenticated:
        leave_room(f"user_{current_user.id}")
        current_user.is_online = False
        current_user.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()


@socketio.on("mark_read")
def handle_mark_read(data):
    from flask_login import current_user
    if not current_user.is_authenticated:
        return
    sender_id = data.get("sender_id")
    if sender_id:
        Message.query.filter_by(
            sender_id=int(sender_id),
            receiver_id=current_user.id,
            is_read=False
        ).update({"is_read": True})
        db.session.commit()
