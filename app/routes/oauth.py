import os
from flask import Blueprint, redirect, url_for, flash, current_app, session
from flask_login import login_user
from authlib.integrations.flask_client import OAuth
from app import db
from app.models import User

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
        token = oauth.google.authorize_access_token()
        resp = oauth.google.get("userinfo")
        user_info = resp.json()
    except Exception as e:
        flash("OAuth authentication failed.", "error")
        return redirect(url_for("auth.login"))
    email = user_info.get("email")
    if not email:
        flash("Could not get email from Google.", "error")
        return redirect(url_for("auth.login"))
    user = User.query.filter_by(email=email).first()
    if user:
        login_user(user)
        user.is_online = True
        db.session.commit()
        flash("Logged in with Google.", "success")
        return redirect(url_for("browse.suggestions"))
    google_id = user_info.get("id")
    first_name = user_info.get("given_name", "User")
    last_name = user_info.get("family_name", "")
    username = email.split("@")[0]
    existing = User.query.filter_by(username=username).first()
    if existing:
        username = f"{username}_{google_id[:6]}"
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        password_hash="oauth_google",
        email_verified=True,
        is_online=True
    )
    db.session.add(user)
    db.session.commit()
    login_user(user)
    flash("Account created with Google. Please complete your profile.", "success")
    return redirect(url_for("profile.edit"))
