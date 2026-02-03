from flask import Blueprint, redirect, url_for
from flask_login import login_required

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/")
@profile_bp.route("/edit")
@login_required
def edit():
    return redirect(url_for("browse.suggestions"))


@profile_bp.route("/view/<int:user_id>")
@login_required
def view(user_id):
    return redirect(url_for("browse.suggestions"))


@profile_bp.route("/visitors")
@login_required
def visitors():
    return redirect(url_for("browse.suggestions"))
