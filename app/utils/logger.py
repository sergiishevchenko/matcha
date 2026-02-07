import logging
from datetime import datetime
from flask import request
from flask_login import current_user


def setup_logger(app):
    handler = logging.FileHandler("app.log")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def log_action(action, details=None):
    from flask import current_app
    user_id = current_user.id if current_user.is_authenticated else "anonymous"
    ip = request.remote_addr if request else "unknown"
    message = f"[{action}] user={user_id} ip={ip}"
    if details:
        message += f" {details}"
    current_app.logger.info(message)


def log_auth(action, username, success=True):
    from flask import current_app
    ip = request.remote_addr if request else "unknown"
    status = "success" if success else "failed"
    current_app.logger.info(f"[AUTH] {action} user={username} status={status} ip={ip}")


def log_error(error, context=None):
    from flask import current_app
    user_id = current_user.id if current_user.is_authenticated else "anonymous"
    ip = request.remote_addr if request else "unknown"
    message = f"[ERROR] user={user_id} ip={ip} error={error}"
    if context:
        message += f" context={context}"
    current_app.logger.error(message)
