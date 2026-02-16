from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models import User, Like, Block

videochat_bp = Blueprint("videochat", __name__)

active_calls = {}


def are_matched(user1_id, user2_id):
    like1 = Like.query.filter_by(liker_id=user1_id, liked_id=user2_id).first()
    like2 = Like.query.filter_by(liker_id=user2_id, liked_id=user1_id).first()
    return like1 is not None and like2 is not None


def is_blocked(user1_id, user2_id):
    return Block.query.filter(
        ((Block.blocker_id == user1_id) & (Block.blocked_id == user2_id)) |
        ((Block.blocker_id == user2_id) & (Block.blocked_id == user1_id))
    ).first() is not None


@videochat_bp.route("/call/<int:user_id>")
@login_required
def call(user_id):
    if user_id == current_user.id:
        flash("You cannot call yourself.", "error")
        return redirect(url_for("chat.index"))
    user = db.get_or_404(User, user_id)
    if is_blocked(current_user.id, user_id):
        flash("Cannot call this user.", "error")
        return redirect(url_for("chat.index"))
    if not are_matched(current_user.id, user_id):
        flash("You can only call matched users.", "error")
        return redirect(url_for("chat.index"))
    room_id = f"call_{min(current_user.id, user_id)}_{max(current_user.id, user_id)}"
    return render_template("videochat/call.html", other_user=user, room_id=room_id)


@socketio.on("join_call")
def handle_join_call(data):
    room = data.get("room")
    user_id = data.get("user_id")
    if room and user_id:
        join_room(room)
        active_calls[user_id] = room
        emit("user_joined", {"user_id": user_id}, room=room, include_self=False)


@socketio.on("leave_call")
def handle_leave_call(data):
    room = data.get("room")
    user_id = data.get("user_id")
    if room:
        leave_room(room)
        if user_id in active_calls:
            del active_calls[user_id]
        emit("user_left", {"user_id": user_id}, room=room, include_self=False)


@socketio.on("offer")
def handle_offer(data):
    room = data.get("room")
    emit("offer", data, room=room, include_self=False)


@socketio.on("answer")
def handle_answer(data):
    room = data.get("room")
    emit("answer", data, room=room, include_self=False)


@socketio.on("ice_candidate")
def handle_ice_candidate(data):
    room = data.get("room")
    emit("ice_candidate", data, room=room, include_self=False)


@socketio.on("call_request")
def handle_call_request(data):
    target_user_id = data.get("target_user_id")
    caller_id = data.get("caller_id")
    caller_name = data.get("caller_name")
    room = data.get("room")
    emit("incoming_call", {
        "caller_id": caller_id,
        "caller_name": caller_name,
        "room": room
    }, room=f"user_{target_user_id}")


@socketio.on("call_declined")
def handle_call_declined(data):
    room = data.get("room")
    emit("call_declined", {}, room=room, include_self=False)


@socketio.on("call_ended")
def handle_call_ended(data):
    room = data.get("room")
    emit("call_ended", {}, room=room, include_self=False)
