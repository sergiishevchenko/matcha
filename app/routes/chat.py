from flask import Blueprint, redirect, url_for
from flask_login import login_required

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/")
@login_required
def index():
    return redirect(url_for("browse.suggestions"))
