from types import SimpleNamespace
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from app import socketio
from app.database import query_one

videochat_bp = Blueprint("videochat", __name__)

active_calls = {}


def are_matched(user1_id, user2_id):
    r = query_one(
        "SELECT 1 FROM likes l1 JOIN likes l2 "
        "ON l1.liker_id = l2.liked_id AND l1.liked_id = l2.liker_id "
        "WHERE l1.liker_id = %s AND l1.liked_id = %s",
        (user1_id, user2_id),
    )
    return r is not None


def _is_blocked(user1_id, user2_id):
    r = query_one(
        "SELECT id FROM blocks WHERE "
        "(blocker_id=%s AND blocked_id=%s) OR (blocker_id=%s AND blocked_id=%s)",
        (user1_id, user2_id, user2_id, user1_id),
    )
    return r is not None


@videochat_bp.route("/call/<int:user_id>")
@login_required
def call(user_id):
    if user_id == current_user.id:
        flash("You cannot call yourself.", "error")
        return redirect(url_for("chat.index"))
    user_row = query_one(
        "SELECT u.id, u.username, u.first_name, u.last_name, u.is_online, "
        "ui.filename AS pp_filename "
        "FROM users u LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.id = %s",
        (user_id,),
    )
    if not user_row:
        flash("User not found.", "error")
        return redirect(url_for("chat.index"))
    if _is_blocked(current_user.id, user_id):
        flash("Cannot call this user.", "error")
        return redirect(url_for("chat.index"))
    if not are_matched(current_user.id, user_id):
        flash("You can only call matched users.", "error")
        return redirect(url_for("chat.index"))
    pp = SimpleNamespace(filename=user_row["pp_filename"]) if user_row.get("pp_filename") else None
    other_user = SimpleNamespace(
        id=user_row["id"], username=user_row["username"],
        first_name=user_row["first_name"], last_name=user_row["last_name"],
        is_online=user_row["is_online"], profile_picture=pp,
    )
    room_id = f"call_{min(current_user.id, user_id)}_{max(current_user.id, user_id)}"
    return render_template("videochat/call.html", other_user=other_user, room_id=room_id)


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
        "room": room,
    }, room=f"user_{target_user_id}")


@socketio.on("call_declined")
def handle_call_declined(data):
    room = data.get("room")
    emit("call_declined", {}, room=room, include_self=False)


@socketio.on("call_ended")
def handle_call_ended(data):
    room = data.get("room")
    emit("call_ended", {}, room=room, include_self=False)
