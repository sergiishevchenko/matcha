from flask import current_app, url_for
from flask_mail import Message


def send_verification_email(user, token):
    verify_url = url_for("auth.verify_email", token=token, _external=True)
    msg = Message(
        subject="Verify your Matcha account",
        recipients=[user.email],
        body=f"Hello {user.first_name},\n\nPlease verify your email by clicking the link below:\n\n{verify_url}\n\nThis link expires in 24 hours.\n\nIf you did not create an account, ignore this email.",
    )
    current_app.extensions["mail"].send(msg)


def send_password_reset_email(user, token):
    reset_url = url_for("auth.reset_password_confirm", token=token, _external=True)
    msg = Message(
        subject="Reset your Matcha password",
        recipients=[user.email],
        body=f"Hello {user.first_name},\n\nTo reset your password, click the link below:\n\n{reset_url}\n\nThis link expires in 1 hour.\n\nIf you did not request a password reset, ignore this email.",
    )
    current_app.extensions["mail"].send(msg)
