from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Event, User, Like, Notification, Block
from app.utils.security import sanitize_string
from app.utils.notifications import emit_notification

events_bp = Blueprint("events", __name__)


def are_matched(user1_id, user2_id):
    like1 = Like.query.filter_by(liker_id=user1_id, liked_id=user2_id).first()
    like2 = Like.query.filter_by(liker_id=user2_id, liked_id=user1_id).first()
    return like1 is not None and like2 is not None


@events_bp.route("/")
@login_required
def index():
    created = Event.query.filter_by(creator_id=current_user.id).order_by(Event.event_date.desc()).all()
    invited = Event.query.filter_by(invitee_id=current_user.id).order_by(Event.event_date.desc()).all()
    return render_template("events/index.html", created=created, invited=invited)


@events_bp.route("/create/<int:user_id>", methods=["GET", "POST"])
@login_required
def create(user_id):
    if user_id == current_user.id:
        flash("You cannot create an event with yourself.", "error")
        return redirect(url_for("events.index"))
    user = db.get_or_404(User, user_id)
    blocked = Block.query.filter(
        ((Block.blocker_id == current_user.id) & (Block.blocked_id == user_id)) |
        ((Block.blocker_id == user_id) & (Block.blocked_id == current_user.id))
    ).first()
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
        event = Event(
            creator_id=current_user.id,
            invitee_id=user_id,
            title=title,
            description=description,
            event_date=event_datetime,
            location=location,
            status="pending"
        )
        db.session.add(event)
        notif = Notification(user_id=user_id, type="event", related_user_id=current_user.id)
        db.session.add(notif)
        db.session.commit()
        emit_notification(user_id, "event", current_user)
        flash("Event invitation sent!", "success")
        return redirect(url_for("events.index"))
    return render_template("events/create.html", user=user)


@events_bp.route("/view/<int:event_id>")
@login_required
def view(event_id):
    event = db.get_or_404(Event, event_id)
    if event.creator_id != current_user.id and event.invitee_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("events.index"))
    other_user = event.invitee if event.creator_id == current_user.id else event.creator
    is_creator = event.creator_id == current_user.id
    return render_template("events/view.html", event=event, other_user=other_user, is_creator=is_creator)


@events_bp.route("/respond/<int:event_id>", methods=["POST"])
@login_required
def respond(event_id):
    event = db.get_or_404(Event, event_id)
    if event.invitee_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("events.index"))
    action = request.form.get("action")
    if action == "accept":
        event.status = "accepted"
        flash("Event accepted!", "success")
    elif action == "decline":
        event.status = "declined"
        flash("Event declined.", "info")
    db.session.commit()
    notif = Notification(user_id=event.creator_id, type="event", related_user_id=current_user.id)
    db.session.add(notif)
    db.session.commit()
    emit_notification(event.creator_id, "event", current_user)
    return redirect(url_for("events.view", event_id=event_id))


@events_bp.route("/cancel/<int:event_id>", methods=["POST"])
@login_required
def cancel(event_id):
    event = db.get_or_404(Event, event_id)
    if event.creator_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("events.index"))
    event.status = "cancelled"
    db.session.commit()
    notif = Notification(user_id=event.invitee_id, type="event", related_user_id=current_user.id)
    db.session.add(notif)
    db.session.commit()
    emit_notification(event.invitee_id, "event", current_user)
    flash("Event cancelled.", "info")
    return redirect(url_for("events.index"))


@events_bp.route("/api/matches")
@login_required
def api_matches():
    my_likes = db.session.query(Like.liked_id).filter_by(liker_id=current_user.id).subquery()
    liked_me = db.session.query(Like.liker_id).filter_by(liked_id=current_user.id).subquery()
    matches = User.query.filter(
        User.id.in_(my_likes),
        User.id.in_(liked_me),
        User.id != current_user.id
    ).all()
    return jsonify([{"id": u.id, "username": u.username, "first_name": u.first_name} for u in matches])
