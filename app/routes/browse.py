from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Like, Block, Report, Notification, UserImage, Tag
from app.utils.fame import update_user_fame
from app.utils.matching import get_suggestions, search_users, calculate_age
from app.utils.notifications import emit_notification

browse_bp = Blueprint("browse", __name__)


@browse_bp.route("/")
@browse_bp.route("/suggestions")
@login_required
def suggestions():
    sort_by = request.args.get("sort", "score")
    filters = {
        "age_min": request.args.get("age_min"),
        "age_max": request.args.get("age_max"),
        "fame_min": request.args.get("fame_min"),
        "fame_max": request.args.get("fame_max"),
        "location_max": request.args.get("location_max"),
        "tags": request.args.get("tags"),
    }
    filters = {k: v for k, v in filters.items() if v}
    results = get_suggestions(current_user, sort_by=sort_by, filters=filters, limit=50)
    my_likes = set(l.liked_id for l in Like.query.filter_by(liker_id=current_user.id).all())
    return render_template(
        "browse/suggestions.html",
        results=results,
        my_likes=my_likes,
        sort_by=sort_by,
        filters=filters,
        calculate_age=calculate_age,
    )


@browse_bp.route("/search")
@login_required
def search():
    sort_by = request.args.get("sort", "score")
    filters = {
        "age_min": request.args.get("age_min"),
        "age_max": request.args.get("age_max"),
        "fame_min": request.args.get("fame_min"),
        "fame_max": request.args.get("fame_max"),
        "location_max": request.args.get("location_max"),
        "tags": request.args.get("tags"),
    }
    filters = {k: v for k, v in filters.items() if v}
    results = []
    searched = any(filters.values())
    if searched:
        results = search_users(current_user, filters=filters, sort_by=sort_by, limit=50)
    my_likes = set(l.liked_id for l in Like.query.filter_by(liker_id=current_user.id).all())
    all_tags = Tag.query.order_by(Tag.name).limit(100).all()
    return render_template(
        "browse/search.html",
        results=results,
        my_likes=my_likes,
        sort_by=sort_by,
        filters=filters,
        searched=searched,
        all_tags=all_tags,
        calculate_age=calculate_age,
    )


@browse_bp.route("/like/<int:user_id>", methods=["POST"])
@login_required
def like(user_id):
    if user_id == current_user.id:
        flash("You cannot like yourself.", "error")
        return redirect(url_for("browse.suggestions"))
    user = User.query.get_or_404(user_id)
    if not current_user.profile_picture_id:
        flash("You need a profile picture to like someone.", "error")
        return redirect(url_for("profile.view", user_id=user_id))
    if not user.profile_picture_id:
        flash("You cannot like a user without a profile picture.", "error")
        return redirect(url_for("profile.view", user_id=user_id))
    existing = Like.query.filter_by(liker_id=current_user.id, liked_id=user_id).first()
    if existing:
        flash("You already liked this user.", "error")
        return redirect(url_for("profile.view", user_id=user_id))
    blocked = Block.query.filter_by(blocker_id=user_id, blocked_id=current_user.id).first()
    i_blocked = Block.query.filter_by(blocker_id=current_user.id, blocked_id=user_id).first()
    if blocked or i_blocked:
        flash("You cannot like this user.", "error")
        return redirect(url_for("browse.suggestions"))
    new_like = Like(liker_id=current_user.id, liked_id=user_id)
    db.session.add(new_like)
    they_liked = Like.query.filter_by(liker_id=user_id, liked_id=current_user.id).first()
    if they_liked:
        notif = Notification(user_id=user_id, type="match", related_user_id=current_user.id)
        db.session.add(notif)
        notif_me = Notification(user_id=current_user.id, type="match", related_user_id=user_id)
        db.session.add(notif_me)
        db.session.commit()
        emit_notification(user_id, "match", current_user)
        flash("It's a match! You can now chat.", "success")
    else:
        notif = Notification(user_id=user_id, type="like", related_user_id=current_user.id)
        db.session.add(notif)
        db.session.commit()
        emit_notification(user_id, "like", current_user)
        flash("You liked this user.", "success")
    update_user_fame(user_id)
    update_user_fame(current_user.id)
    return redirect(url_for("profile.view", user_id=user_id))


@browse_bp.route("/unlike/<int:user_id>", methods=["POST"])
@login_required
def unlike(user_id):
    if user_id == current_user.id:
        return redirect(url_for("browse.suggestions"))
    existing = Like.query.filter_by(liker_id=current_user.id, liked_id=user_id).first()
    if not existing:
        flash("You have not liked this user.", "error")
        return redirect(url_for("profile.view", user_id=user_id))
    was_match = Like.query.filter_by(liker_id=user_id, liked_id=current_user.id).first() is not None
    db.session.delete(existing)
    db.session.commit()
    if was_match:
        notif = Notification(user_id=user_id, type="unlike", related_user_id=current_user.id)
        db.session.add(notif)
        db.session.commit()
        emit_notification(user_id, "unlike", current_user)
    update_user_fame(user_id)
    update_user_fame(current_user.id)
    flash("You unliked this user.", "success")
    return redirect(url_for("profile.view", user_id=user_id))


@browse_bp.route("/block/<int:user_id>", methods=["POST"])
@login_required
def block(user_id):
    if user_id == current_user.id:
        return redirect(url_for("browse.suggestions"))
    user = User.query.get_or_404(user_id)
    existing = Block.query.filter_by(blocker_id=current_user.id, blocked_id=user_id).first()
    if existing:
        flash("User already blocked.", "error")
        return redirect(url_for("browse.suggestions"))
    new_block = Block(blocker_id=current_user.id, blocked_id=user_id)
    db.session.add(new_block)
    Like.query.filter_by(liker_id=current_user.id, liked_id=user_id).delete()
    Like.query.filter_by(liker_id=user_id, liked_id=current_user.id).delete()
    db.session.commit()
    flash("User blocked.", "success")
    return redirect(url_for("browse.suggestions"))


@browse_bp.route("/report/<int:user_id>", methods=["POST"])
@login_required
def report(user_id):
    if user_id == current_user.id:
        return redirect(url_for("browse.suggestions"))
    user = User.query.get_or_404(user_id)
    reason = request.form.get("reason", "Reported as fake account")
    new_report = Report(reporter_id=current_user.id, reported_id=user_id, reason=reason)
    db.session.add(new_report)
    db.session.commit()
    flash("User reported. Thank you.", "success")
    return redirect(url_for("browse.suggestions"))
