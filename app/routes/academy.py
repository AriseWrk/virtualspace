from flask import Blueprint, render_template
from flask_login import login_required

academy_bp = Blueprint("academy", __name__, url_prefix="/academy")


@academy_bp.route("/")
@login_required
def dashboard():
    return render_template("academy/dashboard.html")


@academy_bp.route("/courses")
@login_required
def courses():
    return render_template("academy/courses.html")


@academy_bp.route("/tests")
@login_required
def tests():
    return render_template("academy/tests.html")


@academy_bp.route("/knowledge")
@login_required
def knowledge():
    return render_template("academy/knowledge.html")