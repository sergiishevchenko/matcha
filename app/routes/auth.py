import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models import User
from app.utils.security import is_password_strong, sanitize_string
from app.utils.email import send_verification_email, send_password_reset_email
from app.utils.validators import is_valid_email, is_valid_username, is_valid_name

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("browse.suggestions"))
    if request.method != "POST":
        return render_template("auth/register.html")
    email = sanitize_string(request.form.get("email"), 120)
    username = sanitize_string(request.form.get("username"), 80)
    first_name = sanitize_string(request.form.get("first_name"), 80)
    last_name = sanitize_string(request.form.get("last_name"), 80)
    password = request.form.get("password")
    password_confirm = request.form.get("password_confirm")
    if not all([email, username, first_name, last_name, password]):
        flash("All fields are required.", "error")
        return render_template("auth/register.html")
    if not is_valid_email(email):
        flash("Invalid email format.", "error")
        return render_template("auth/register.html")
    if not is_valid_username(username):
        flash("Username must be 3-30 characters, alphanumeric or underscore only.", "error")
        return render_template("auth/register.html")
    if not is_valid_name(first_name) or not is_valid_name(last_name):
        flash("Names can only contain letters, spaces, hyphens, and apostrophes.", "error")
        return render_template("auth/register.html")
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("auth/register.html")
    ok, err = is_password_strong(password)
    if not ok:
        flash(err, "error")
        return render_template("auth/register.html")
    if User.query.filter_by(email=email).first():
        flash("Email already registered.", "error")
        return render_template("auth/register.html")
    if User.query.filter_by(username=username).first():
        flash("Username already taken.", "error")
        return render_template("auth/register.html")
    verification_token = secrets.token_urlsafe(32)
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(
        email=email,
        username=username,
        first_name=first_name,
        last_name=last_name,
        password_hash=password_hash,
        verification_token=verification_token,
    )
    db.session.add(user)
    db.session.commit()
    try:
        send_verification_email(user, verification_token)
    except Exception:
        pass
    flash("Account created. Please check your email to verify your account.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/verify/<token>")
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        flash("Invalid or expired verification link.", "error")
        return redirect(url_for("auth.login"))
    user.email_verified = True
    user.verification_token = None
    db.session.commit()
    flash("Email verified. You can now log in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("browse.suggestions"))
    if request.method != "POST":
        return render_template("auth/login.html")
    username = sanitize_string(request.form.get("username"), 80)
    password = request.form.get("password")
    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("auth/login.html")
    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        flash("Invalid username or password.", "error")
        return render_template("auth/login.html")
    if not user.email_verified:
        flash("Please verify your email before logging in.", "error")
        return render_template("auth/login.html")
    login_user(user)
    user.is_online = True
    user.last_seen = datetime.utcnow()
    db.session.commit()
    next_page = request.args.get("next")
    return redirect(next_page or url_for("browse.suggestions"))


@auth_bp.route("/logout")
@login_required
def logout():
    if current_user.is_authenticated:
        current_user.is_online = False
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("browse.suggestions"))
    if request.method != "POST":
        return render_template("auth/reset_password.html", step="request")
    email = sanitize_string(request.form.get("email"), 120)
    if not email:
        flash("Email is required.", "error")
        return render_template("auth/reset_password.html", step="request")
    user = User.query.filter_by(email=email).first()
    if user:
        from flask import current_app
        user.reset_token = secrets.token_urlsafe(32)
        user.reset_token_expiry = datetime.utcnow() + timedelta(
            hours=current_app.config.get("RESET_TOKEN_EXPIRY_HOURS", 1)
        )
        db.session.commit()
        try:
            send_password_reset_email(user, user.reset_token)
        except Exception:
            pass
    flash("If an account exists with that email, you will receive a password reset link.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_confirm(token):
    if current_user.is_authenticated:
        return redirect(url_for("browse.suggestions"))
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("auth.reset_password_request"))
    if request.method != "POST":
        return render_template("auth/reset_password.html", step="confirm", token=token)
    password = request.form.get("password")
    password_confirm = request.form.get("password_confirm")
    if not password or not password_confirm:
        flash("Password fields are required.", "error")
        return render_template("auth/reset_password.html", step="confirm", token=token)
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("auth/reset_password.html", step="confirm", token=token)
    ok, err = is_password_strong(password)
    if not ok:
        flash(err, "error")
        return render_template("auth/reset_password.html", step="confirm", token=token)
    user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()
    flash("Password has been reset. You can now log in.", "success")
    return redirect(url_for("auth.login"))
