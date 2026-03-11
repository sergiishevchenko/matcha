from flask import Blueprint, redirect, url_for, flash, current_app
from flask_login import login_user
from authlib.integrations.flask_client import OAuth
from app.database import query_one, execute_returning, execute, commit
from app.models import make_user

oauth_bp = Blueprint("oauth", __name__)

oauth = OAuth()


def _load_user_by_email(email):
    return query_one(
        "SELECT u.*, ui.filename AS pp_filename, ui.id AS pp_id "
        "FROM users u LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.email = %s",
        (email,),
    )


def _load_user_by_id(user_id):
    return query_one(
        "SELECT u.*, ui.filename AS pp_filename, ui.id AS pp_id "
        "FROM users u LEFT JOIN user_images ui ON u.profile_picture_id = ui.id "
        "WHERE u.id = %s",
        (user_id,),
    )


def _unique_username(base_username, provider_id):
    username = (base_username or "user").lower().replace(" ", "_")
    existing = query_one("SELECT id FROM users WHERE username = %s", (username,))
    if existing:
        suffix = str(provider_id)[:6] if provider_id else "oauth"
        username = f"{username}_{suffix}"
    return username


def _oauth_login_or_create(email, first_name, last_name, username_hint, provider_key, provider_id):
    row = _load_user_by_email(email)
    if row:
        user = make_user(row)
        login_user(user)
        execute("UPDATE users SET is_online = true WHERE id = %s", (user.id,))
        commit()
        flash(f"Logged in with {provider_key.title()}.", "success")
        return redirect(url_for("browse.suggestions"))

    username = _unique_username(username_hint, provider_id)
    new_row = execute_returning(
        "INSERT INTO users (username, email, first_name, last_name, password_hash, "
        "email_verified, is_online) VALUES (%s, %s, %s, %s, %s, true, true) "
        "RETURNING id",
        (username, email, first_name, last_name, f"oauth_{provider_key}"),
    )
    commit()
    user_row = _load_user_by_id(new_row["id"])
    user = make_user(user_row)
    login_user(user)
    flash(f"Account created with {provider_key.title()}. Please complete your profile.", "success")
    return redirect(url_for("profile.edit"))


def init_oauth(app):
    oauth.init_app(app)
    if app.config.get("GOOGLE_CLIENT_ID"):
        oauth.register(
            name="google",
            client_id=app.config.get("GOOGLE_CLIENT_ID"),
            client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
            access_token_url="https://oauth2.googleapis.com/token",
            authorize_url="https://accounts.google.com/o/oauth2/auth",
            api_base_url="https://www.googleapis.com/oauth2/v1/",
            client_kwargs={"scope": "email profile"},
        )
    if app.config.get("GITHUB_CLIENT_ID"):
        oauth.register(
            name="github",
            client_id=app.config.get("GITHUB_CLIENT_ID"),
            client_secret=app.config.get("GITHUB_CLIENT_SECRET"),
            access_token_url="https://github.com/login/oauth/access_token",
            authorize_url="https://github.com/login/oauth/authorize",
            api_base_url="https://api.github.com/",
            client_kwargs={"scope": "user:email"},
        )
    if app.config.get("INTRA42_CLIENT_ID"):
        oauth.register(
            name="intra42",
            client_id=app.config.get("INTRA42_CLIENT_ID"),
            client_secret=app.config.get("INTRA42_CLIENT_SECRET"),
            access_token_url="https://api.intra.42.fr/oauth/token",
            authorize_url="https://api.intra.42.fr/oauth/authorize",
            api_base_url="https://api.intra.42.fr/v2/",
            client_kwargs={"scope": "public"},
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
    return _oauth_login_or_create(
        email=email,
        first_name=user_info.get("given_name", "User"),
        last_name=user_info.get("family_name", ""),
        username_hint=email.split("@")[0],
        provider_key="google",
        provider_id=user_info.get("id"),
    )


@oauth_bp.route("/github")
def github_login():
    if not current_app.config.get("GITHUB_CLIENT_ID"):
        flash("GitHub OAuth is not configured.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("oauth.github_callback", _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@oauth_bp.route("/github/callback")
def github_callback():
    if not current_app.config.get("GITHUB_CLIENT_ID"):
        flash("GitHub OAuth is not configured.", "error")
        return redirect(url_for("auth.login"))
    try:
        oauth.github.authorize_access_token()
        user_info = oauth.github.get("user").json()
        email = user_info.get("email")
        if not email:
            emails_resp = oauth.github.get("user/emails").json()
            for item in emails_resp:
                if item.get("primary") and item.get("verified") and item.get("email"):
                    email = item.get("email")
                    break
        if not email:
            email = f"github_{user_info.get('id')}@oauth.local"
    except Exception:
        flash("OAuth authentication failed.", "error")
        return redirect(url_for("auth.login"))
    first_name = user_info.get("name") or user_info.get("login") or "User"
    last_name = ""
    return _oauth_login_or_create(
        email=email,
        first_name=first_name,
        last_name=last_name,
        username_hint=user_info.get("login") or email.split("@")[0],
        provider_key="github",
        provider_id=user_info.get("id"),
    )


@oauth_bp.route("/intra42")
def intra42_login():
    if not current_app.config.get("INTRA42_CLIENT_ID"):
        flash("42 Intra OAuth is not configured.", "error")
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("oauth.intra42_callback", _external=True)
    return oauth.intra42.authorize_redirect(redirect_uri)


@oauth_bp.route("/intra42/callback")
def intra42_callback():
    if not current_app.config.get("INTRA42_CLIENT_ID"):
        flash("42 Intra OAuth is not configured.", "error")
        return redirect(url_for("auth.login"))
    try:
        oauth.intra42.authorize_access_token()
        user_info = oauth.intra42.get("me").json()
    except Exception:
        flash("OAuth authentication failed.", "error")
        return redirect(url_for("auth.login"))
    provider_id = user_info.get("id")
    email = user_info.get("email") or f"intra42_{provider_id}@oauth.local"
    first_name = user_info.get("first_name") or user_info.get("usual_first_name") or "User"
    last_name = user_info.get("last_name") or ""
    username_hint = user_info.get("login") or email.split("@")[0]
    return _oauth_login_or_create(
        email=email,
        first_name=first_name,
        last_name=last_name,
        username_hint=username_hint,
        provider_key="intra42",
        provider_id=provider_id,
    )
