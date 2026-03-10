from datetime import datetime, timezone
from types import SimpleNamespace
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.database import query_one, query_all, execute, execute_returning, commit
from app.utils.security import sanitize_string
from app.utils.notifications import emit_notification

events_bp = Blueprint("events", __name__)


def are_matched(user1_id, user2_id):
    r = query_one(
        "SELECT 1 FROM likes l1 JOIN likes l2 "
        "ON l1.liker_id = l2.liked_id AND l1.liked_id = l2.liker_id "
        "WHERE l1.liker_id = %s AND l1.liked_id = %s",
        (user1_id, user2_id),
    )
    return r is not None


def _load_events(sql, params):
    rows = query_all(sql, params)
    events = []
    for r in rows:
        creator = query_one("SELECT id, first_name, username FROM users WHERE id = %s", (r["creator_id"],))
        invitee = query_one("SELECT id, first_name, username FROM users WHERE id = %s", (r["invitee_id"],))
        ev = SimpleNamespace(**r)
        ev.creator = SimpleNamespace(**creator) if creator else None
        ev.invitee = SimpleNamespace(**invitee) if invitee else None
        events.append(ev)
    return events


@events_bp.route("/")
@login_required
def index():
    created = _load_events(
        "SELECT * FROM events WHERE creator_id = %s ORDER BY event_date DESC",
        (current_user.id,),
    )
    invited = _load_events(
        "SELECT * FROM events WHERE invitee_id = %s ORDER BY event_date DESC",
        (current_user.id,),
    )
    return render_template("events/index.html", created=created, invited=invited)


@events_bp.route("/create/<int:user_id>", methods=["GET", "POST"])
@login_required
def create(user_id):
    if user_id == current_user.id:
        flash("You cannot create an event with yourself.", "error")
        return redirect(url_for("events.index"))
    user_row = query_one("SELECT id, first_name, username FROM users WHERE id = %s", (user_id,))
    if not user_row:
        flash("User not found.", "error")
        return redirect(url_for("events.index"))
    user = SimpleNamespace(**user_row)
    blocked = query_one(
        "SELECT id FROM blocks WHERE "
        "(blocker_id=%s AND blocked_id=%s) OR (blocker_id=%s AND blocked_id=%s)",
        (current_user.id, user_id, user_id, current_user.id),
    )
    if blocked:
        flash("Cannot create event with this user.", "error")
        return redirect(url_for("events.index"))
    if not are_matched(current_user.id, user_id):
        flash("You can only create events with matched users.", "error")
        return redirect(url_for("events.index"))
    if request.method == "POST":
        title = sanitize_string(request.form.get("title"), 200)
        description = sanitize_string(request.form.get("description"), 2000)
        date_str = request.form.get("event_date")
        time_str = request.form.get("event_time", "12:00")
        location = sanitize_string(request.form.get("location"), 300)
        if not title or not date_str:
            flash("Title and date are required.", "error")
            return render_template("events/create.html", user=user)
        try:
            event_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Invalid date format.", "error")
            return render_template("events/create.html", user=user)
        if event_datetime < datetime.now(timezone.utc).replace(tzinfo=None):
            flash("Event date must be in the future.", "error")
            return render_template("events/create.html", user=user)
        execute(
            "INSERT INTO events (creator_id, invitee_id, title, description, event_date, location, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, 'pending')",
            (current_user.id, user_id, title, description, event_datetime, location),
        )
        execute(
            "INSERT INTO notifications (user_id, type, related_user_id) VALUES (%s, 'event', %s)",
            (user_id, current_user.id),
        )
        commit()
        emit_notification(user_id, "event", current_user)
        flash("Event invitation sent!", "success")
        return redirect(url_for("events.index"))
    return render_template("events/create.html", user=user)


@events_bp.route("/view/<int:event_id>")
@login_required
def view(event_id):
    row = query_one("SELECT * FROM events WHERE id = %s", (event_id,))
    if not row:
        flash("Event not found.", "error")
        return redirect(url_for("events.index"))
    event = SimpleNamespace(**row)
    if event.creator_id != current_user.id and event.invitee_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("events.index"))
    creator = query_one("SELECT id, first_name, username FROM users WHERE id = %s", (event.creator_id,))
    invitee = query_one("SELECT id, first_name, username FROM users WHERE id = %s", (event.invitee_id,))
    event.creator = SimpleNamespace(**creator) if creator else None
    event.invitee = SimpleNamespace(**invitee) if invitee else None
    other_user = event.invitee if event.creator_id == current_user.id else event.creator
    is_creator = event.creator_id == current_user.id
    return render_template("events/view.html", event=event, other_user=other_user, is_creator=is_creator)


@events_bp.route("/respond/<int:event_id>", methods=["POST"])
@login_required
def respond(event_id):
    row = query_one("SELECT * FROM events WHERE id = %s", (event_id,))
    if not row:
        flash("Event not found.", "error")
        return redirect(url_for("events.index"))
    if row["invitee_id"] != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("events.index"))
    action = request.form.get("action")
    if action == "accept":
        execute("UPDATE events SET status='accepted' WHERE id=%s", (event_id,))
        flash("Event accepted!", "success")
    elif action == "decline":
        execute("UPDATE events SET status='declined' WHERE id=%s", (event_id,))
        flash("Event declined.", "info")
    execute(
        "INSERT INTO notifications (user_id, type, related_user_id) VALUES (%s, 'event', %s)",
        (row["creator_id"], current_user.id),
    )
    commit()
    emit_notification(row["creator_id"], "event", current_user)
    return redirect(url_for("events.view", event_id=event_id))


@events_bp.route("/cancel/<int:event_id>", methods=["POST"])
@login_required
def cancel(event_id):
    row = query_one("SELECT * FROM events WHERE id = %s", (event_id,))
    if not row:
        flash("Event not found.", "error")
        return redirect(url_for("events.index"))
    if row["creator_id"] != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("events.index"))
    execute("UPDATE events SET status='cancelled' WHERE id=%s", (event_id,))
    execute(
        "INSERT INTO notifications (user_id, type, related_user_id) VALUES (%s, 'event', %s)",
        (row["invitee_id"], current_user.id),
    )
    commit()
    emit_notification(row["invitee_id"], "event", current_user)
    flash("Event cancelled.", "info")
    return redirect(url_for("events.index"))


@events_bp.route("/api/matches")
@login_required
def api_matches():
    rows = query_all(
        "SELECT u.id, u.username, u.first_name FROM users u "
        "WHERE u.id IN ("
        "  SELECT l1.liked_id FROM likes l1 "
        "  JOIN likes l2 ON l1.liker_id = l2.liked_id AND l1.liked_id = l2.liker_id "
        "  WHERE l1.liker_id = %s"
        ") AND u.id != %s",
        (current_user.id, current_user.id),
    )
    return jsonify([{"id": r["id"], "username": r["username"], "first_name": r["first_name"]} for r in rows])
