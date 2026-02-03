import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()


def create_app(config_class=None):
    app = Flask(__name__)
    if config_class is None:
        app.config.from_object("app.config.Config")
    else:
        app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    mail.init_app(app)

    upload_folder = app.config.get("UPLOAD_FOLDER", "./app/uploads")
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    from app.routes.auth import auth_bp
    from app.routes.profile import profile_bp
    from app.routes.browse import browse_bp
    from app.routes.chat import chat_bp
    from app.routes.notifications import notifications_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(browse_bp, url_prefix="/browse")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    @app.route("/")
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for("browse.suggestions"))
        return redirect(url_for("auth.login"))

    return app
