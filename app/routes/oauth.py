from flask import Blueprint, redirect, url_for, flash, current_app
from flask_login import login_user
from authlib.integrations.flask_client import OAuth
from app.database import query_one, execute_returning, execute, commit
from app.models import make_user

oauth_bp = Blueprint("oauth", __name__)

oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        access_token_url="https://oauth2.googleapis.com/token",
        access_token_params=None,
        authorize_url="https://accounts.google.com/o/oauth2/auth",
        authorize_params=None,
        api_base_url="https://www.googleapis.com/oauth2/v1/",
        client_kwargs={"scope": "email profile"},
    )


@oauth_bp.route("/google")
def google_login():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("Google OAuth is not configured.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("oauth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@oauth_bp.route("/google/callback")
def google_callback():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("Google OAuth is not configured.", "error")
        return redirect(url_for("auth.login"))
    try:
        oauth.google.authorize_access_token()
        resp = oauth.google.get("userinfo")
        user_info = resp.json()
    except Exception:
        flash("OAuth authentication failed.", "error")
        return redirect(url_for("auth.login"))
    email = user_info.get("email")
    if not email:
        flash("Could not get email from Google.", "error")
        return redirect(url_for("auth.login"))
    row = query_one(
        "SELECT u.*, ui.filename AS pp_filename, ui.id AS pp_id "
        "FROM users u LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.email = %s",
        (email,),
    )
    if row:
        user = make_user(row)
        login_user(user)
        execute("UPDATE users SET is_online = true WHERE id = %s", (user.id,))
        commit()
        flash("Logged in with Google.", "success")
        return redirect(url_for("browse.suggestions"))
    google_id = user_info.get("id")
    first_name = user_info.get("given_name", "User")
    last_name = user_info.get("family_name", "")
    username = email.split("@")[0]
    existing = query_one("SELECT id FROM users WHERE username = %s", (username,))
    if existing:
        username = f"{username}_{google_id[:6]}"
    new_row = execute_returning(
        "INSERT INTO users (username, email, first_name, last_name, password_hash, "
        "email_verified, is_online) VALUES (%s, %s, %s, %s, 'oauth_google', true, true) "
        "RETURNING id",
        (username, email, first_name, last_name),
    )
    commit()
    user_row = query_one(
        "SELECT u.*, ui.filename AS pp_filename, ui.id AS pp_id "
        "FROM users u LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.id = %s",
        (new_row["id"],),
    )
    user = make_user(user_row)
    login_user(user)
    flash("Account created with Google. Please complete your profile.", "success")
    return redirect(url_for("profile.edit"))
