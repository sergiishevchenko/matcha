import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import bcrypt
from app.models import User, make_user
from app.database import query_one, execute, execute_returning, commit
from app.utils.security import is_password_strong, sanitize_string
from app.utils.email import send_verification_email, send_password_reset_email
from app.utils.validators import is_valid_email, is_valid_username, is_valid_name
from app.utils.logger import log_auth

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
    if query_one("SELECT id FROM users WHERE email = %s", (email,)):
        flash("Email already registered.", "error")
        return render_template("auth/register.html")
    if query_one("SELECT id FROM users WHERE username = %s", (username,)):
        flash("Username already taken.", "error")
        return render_template("auth/register.html")
    verification_token = secrets.token_urlsafe(32)
    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    row = execute_returning(
        "INSERT INTO users (email, username, first_name, last_name, password_hash, verification_token) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (email, username, first_name, last_name, password_hash, verification_token),
    )
    commit()
    log_auth("register", username, success=True)
    user_obj = User(id=row["id"], email=email, first_name=first_name)
    verify_url = url_for("auth.verify_email", token=verification_token, _external=True)
    from flask import current_app
    # Demo/evaluation mode: always show the verification link on screen
    if current_app.config.get("SHOW_VERIFICATION_LINK"):
        flash("Account created. Email verification link is shown below (demo mode).", "success")
        flash(f"Verification link: {verify_url}", "success")
    else:
        try:
            send_verification_email(user_obj, verification_token)
        except Exception:
            flash("Account created, but verification email could not be sent. Ask admin or try again later.", "error")
            return redirect(url_for("auth.login"))
        flash("Account created. Please check your email to verify your account.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/verify/<token>")
def verify_email(token):
    row = query_one("SELECT id FROM users WHERE verification_token = %s", (token,))
    if not row:
        flash("Invalid or expired verification link.", "error")
        return redirect(url_for("auth.login"))
    execute(
        "UPDATE users SET email_verified = true, verification_token = NULL WHERE id = %s",
        (row["id"],),
    )
    commit()
    flash("Email verified. You can now log in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if current_user.is_authenticated:
        return redirect(url_for("browse.suggestions"))
    if request.method != "POST":
        return render_template("auth/resend_verification.html")
    email = sanitize_string(request.form.get("email"), 120)
    if not email:
        flash("Email is required.", "error")
        return render_template("auth/resend_verification.html")
    row = query_one("SELECT id, email_verified, first_name FROM users WHERE email = %s", (email,))
    if row and not row["email_verified"]:
        new_token = secrets.token_urlsafe(32)
        execute("UPDATE users SET verification_token = %s WHERE id = %s", (new_token, row["id"]))
        commit()
        user_obj = User(id=row["id"], email=email, first_name=row["first_name"])
        from flask import current_app
        verify_url = url_for("auth.verify_email", token=new_token, _external=True)
        if current_app.config.get("SHOW_VERIFICATION_LINK"):
            flash(f"Verification link: {verify_url}", "success")
        else:
            try:
                send_verification_email(user_obj, new_token)
            except Exception:
                pass
    flash("If an unverified account exists with that email, a verification link has been sent.", "success")
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
    row = query_one(
        "SELECT u.*, ui.filename AS pp_filename, ui.id AS pp_id "
        "FROM users u LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.username = %s",
        (username,),
    )
    if not row or not bcrypt.check_password_hash(row["password_hash"], password):
        log_auth("login", username, success=False)
        flash("Invalid username or password.", "error")
        return render_template("auth/login.html")
    if not row["email_verified"]:
        flash("Please verify your email before logging in. You can request a new verification email.", "error")
        return render_template("auth/login.html")
    user = make_user(row)
    login_user(user)
    log_auth("login", username, success=True)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    execute("UPDATE users SET is_online = true, last_seen = %s WHERE id = %s", (now, user.id))
    commit()
    next_page = request.args.get("next")
    return redirect(next_page or url_for("browse.suggestions"))


@auth_bp.route("/logout")
@login_required
def logout():
    if current_user.is_authenticated:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        execute("UPDATE users SET is_online = false, last_seen = %s WHERE id = %s", (now, current_user.id))
        commit()
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
    row = query_one("SELECT id, first_name, email FROM users WHERE email = %s", (email,))
    if row:
        from flask import current_app
        token = secrets.token_urlsafe(32)
        expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            hours=current_app.config.get("RESET_TOKEN_EXPIRY_HOURS", 1)
        )
        execute(
            "UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE id = %s",
            (token, expiry, row["id"]),
        )
        commit()
        user_obj = User(id=row["id"], email=row["email"], first_name=row["first_name"])
        try:
            send_password_reset_email(user_obj, token)
        except Exception:
            pass
    flash("If an account exists with that email, you will receive a password reset link.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_confirm(token):
    if current_user.is_authenticated:
        return redirect(url_for("browse.suggestions"))
    row = query_one("SELECT id, reset_token_expiry FROM users WHERE reset_token = %s", (token,))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not row or not row["reset_token_expiry"] or row["reset_token_expiry"] < now:
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
    new_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    execute(
        "UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL WHERE id = %s",
        (new_hash, row["id"]),
    )
    commit()
    flash("Password has been reset. You can now log in.", "success")
    return redirect(url_for("auth.login"))
