import re
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, UserImage, Tag, UserTag, ProfileView, Like, Notification
from app.utils.security import sanitize_string
from app.utils.images import save_image, delete_image_file
from app.utils.fame import update_user_fame
from app.utils.matching import calculate_age

profile_bp = Blueprint("profile", __name__)

MAX_IMAGES = 5
MAX_TAGS = 10


def get_user_tags(user_id):
    tags = db.session.query(Tag).join(UserTag).filter(UserTag.user_id == user_id).all()
    return [t.name for t in tags]


def set_user_tags(user_id, tag_names):
    UserTag.query.filter_by(user_id=user_id).delete()
    seen = set()
    for name in tag_names[:MAX_TAGS]:
        name = re.sub(r"[^a-z0-9_-]", "", name.lower().strip())
        if not name or name in seen:
            continue
        seen.add(name)
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
            db.session.flush()
        ut = UserTag(user_id=user_id, tag_id=tag.id)
        db.session.add(ut)
    db.session.commit()


@profile_bp.route("/")
@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    user = current_user
    if request.method == "POST":
        first_name = sanitize_string(request.form.get("first_name"), 80)
        last_name = sanitize_string(request.form.get("last_name"), 80)
        email = sanitize_string(request.form.get("email"), 120)
        birth_date_str = request.form.get("birth_date", "")
        gender = request.form.get("gender")
        sexual_preference = request.form.get("sexual_preference")
        biography = sanitize_string(request.form.get("biography"), 2000)
        tags_raw = request.form.get("tags", "")
        birth_date = None
        if birth_date_str:
            try:
                birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        if not first_name or not last_name or not email:
            flash("First name, last name and email are required.", "error")
            return render_template("profile/edit.html", user=user, tags=get_user_tags(user.id))
        if gender not in ("male", "female", "other", ""):
            gender = None
        if sexual_preference not in ("heterosexual", "homosexual", "bisexual", ""):
            sexual_preference = None
        if email != user.email:
            existing = User.query.filter(User.email == email, User.id != user.id).first()
            if existing:
                flash("Email already in use.", "error")
                return render_template("profile/edit.html", user=user, tags=get_user_tags(user.id))
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.birth_date = birth_date
        user.gender = gender if gender else None
        user.sexual_preference = sexual_preference if sexual_preference else None
        user.biography = biography
        db.session.commit()
        tag_names = [t.strip() for t in tags_raw.split(",") if t.strip()]
        set_user_tags(user.id, tag_names)
        flash("Profile updated.", "success")
        return redirect(url_for("profile.edit"))
    tags = get_user_tags(user.id)
    images = UserImage.query.filter_by(user_id=user.id).order_by(UserImage.upload_order).all()
    return render_template("profile/edit.html", user=user, tags=tags, images=images)


@profile_bp.route("/upload-image", methods=["POST"])
@login_required
def upload_image():
    count = UserImage.query.filter_by(user_id=current_user.id).count()
    if count >= MAX_IMAGES:
        flash(f"Maximum {MAX_IMAGES} images allowed.", "error")
        return redirect(url_for("profile.edit"))
    file = request.files.get("image")
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "./app/uploads")
    filename, err = save_image(file, upload_folder)
    if err:
        flash(err, "error")
        return redirect(url_for("profile.edit"))
    is_first = count == 0
    img = UserImage(
        user_id=current_user.id,
        filename=filename,
        is_profile_picture=is_first,
        upload_order=count
    )
    db.session.add(img)
    db.session.flush()
    if is_first:
        current_user.profile_picture_id = img.id
    db.session.commit()
    flash("Image uploaded.", "success")
    return redirect(url_for("profile.edit"))


@profile_bp.route("/delete-image/<int:image_id>", methods=["POST"])
@login_required
def delete_image(image_id):
    img = UserImage.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not img:
        flash("Image not found.", "error")
        return redirect(url_for("profile.edit"))
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "./app/uploads")
    delete_image_file(img.filename, upload_folder)
    was_profile = img.is_profile_picture
    db.session.delete(img)
    if was_profile:
        current_user.profile_picture_id = None
        next_img = UserImage.query.filter_by(user_id=current_user.id).order_by(UserImage.upload_order).first()
        if next_img:
            next_img.is_profile_picture = True
            current_user.profile_picture_id = next_img.id
    db.session.commit()
    flash("Image deleted.", "success")
    return redirect(url_for("profile.edit"))


@profile_bp.route("/set-profile-picture/<int:image_id>", methods=["POST"])
@login_required
def set_profile_picture(image_id):
    img = UserImage.query.filter_by(id=image_id, user_id=current_user.id).first()
    if not img:
        flash("Image not found.", "error")
        return redirect(url_for("profile.edit"))
    UserImage.query.filter_by(user_id=current_user.id).update({"is_profile_picture": False})
    img.is_profile_picture = True
    current_user.profile_picture_id = img.id
    db.session.commit()
    flash("Profile picture updated.", "success")
    return redirect(url_for("profile.edit"))


@profile_bp.route("/update-location", methods=["POST"])
@login_required
def update_location():
    data = request.get_json() or {}
    lat = data.get("latitude")
    lng = data.get("longitude")
    manual = data.get("manual", False)
    if lat is not None and lng is not None:
        try:
            lat = float(lat)
            lng = float(lng)
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                current_user.latitude = lat
                current_user.longitude = lng
                current_user.location_enabled = True
                db.session.commit()
                return jsonify({"success": True})
        except (ValueError, TypeError):
            pass
    return jsonify({"success": False, "error": "Invalid coordinates"}), 400


@profile_bp.route("/view/<int:user_id>")
@login_required
def view(user_id):
    if user_id == current_user.id:
        return redirect(url_for("profile.edit"))
    user = User.query.get_or_404(user_id)
    if not user.email_verified:
        flash("User not found.", "error")
        return redirect(url_for("browse.suggestions"))
    pv = ProfileView(viewer_id=current_user.id, viewed_id=user.id, viewed_at=datetime.utcnow())
    db.session.add(pv)
    notif = Notification(user_id=user.id, type="view", related_user_id=current_user.id)
    db.session.add(notif)
    db.session.commit()
    update_user_fame(user.id)
    images = UserImage.query.filter_by(user_id=user.id).order_by(UserImage.upload_order).all()
    tags = get_user_tags(user.id)
    i_liked = Like.query.filter_by(liker_id=current_user.id, liked_id=user.id).first() is not None
    they_liked = Like.query.filter_by(liker_id=user.id, liked_id=current_user.id).first() is not None
    is_match = i_liked and they_liked
    age = calculate_age(user.birth_date)
    return render_template(
        "profile/view.html",
        user=user,
        images=images,
        tags=tags,
        i_liked=i_liked,
        they_liked=they_liked,
        is_match=is_match,
        age=age
    )


@profile_bp.route("/visitors")
@login_required
def visitors():
    views = db.session.query(ProfileView, User).join(
        User, ProfileView.viewer_id == User.id
    ).filter(
        ProfileView.viewed_id == current_user.id
    ).order_by(ProfileView.viewed_at.desc()).limit(100).all()
    return render_template("profile/visitors.html", views=views)


@profile_bp.route("/likes")
@login_required
def likes():
    likes_list = db.session.query(Like, User).join(
        User, Like.liker_id == User.id
    ).filter(
        Like.liked_id == current_user.id
    ).order_by(Like.created_at.desc()).limit(100).all()
    my_likes = set(
        l.liked_id for l in Like.query.filter_by(liker_id=current_user.id).all()
    )
    return render_template("profile/likes.html", likes=likes_list, my_likes=my_likes)
