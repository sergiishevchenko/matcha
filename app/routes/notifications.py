from flask import Blueprint, redirect, url_for
from flask_login import login_required

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/")
@login_required
def index():
    return redirect(url_for("browse.suggestions"))
