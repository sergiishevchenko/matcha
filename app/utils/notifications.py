from app import socketio


def emit_notification(user_id, notif_type, from_user):
    socketio.emit("notification", {
        "type": notif_type,
        "from_user_id": from_user.id,
        "from_user_name": from_user.first_name,
    }, room=f"user_{user_id}")
