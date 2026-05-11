from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user, current_user
from sqlalchemy import func

from models import User, db
from security import bcrypt
from theme import THEME

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("login.html", theme=THEME)


@bp.post("/login")
def login_post():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    remember = True if request.form.get("remember") == "on" else False

    user = db.session.query(User).filter(func.lower(User.username) == username.lower()).first()
    if not user:
        flash("Invalid username or password.", "danger")
        return redirect(url_for("auth.login"))

    if not bcrypt.check_password_hash(user.password_hash, password):
        flash("Invalid username or password.", "danger")
        return redirect(url_for("auth.login"))

    login_user(user, remember=remember)
    flash("Welcome back.", "success")
    return redirect(url_for("main.dashboard"))


@bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("auth.login"))

