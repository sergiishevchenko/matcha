from flask import Blueprint, render_template
from flask_login import login_required

browse_bp = Blueprint("browse", __name__)


@browse_bp.route("/")
@browse_bp.route("/suggestions")
@login_required
def suggestions():
    return render_template("browse/suggestions.html")


@browse_bp.route("/search")
@login_required
def search():
    return render_template("browse/search.html")
