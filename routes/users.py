from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import func

from decorators import admin_required
from models import User, db
from security import bcrypt
from theme import THEME

bp = Blueprint("users", __name__)


@bp.get("/users")
@login_required
@admin_required
def users():
    users = db.session.query(User).order_by(User.created_at.desc()).all()
    return render_template("users.html", theme=THEME, users=users)


@bp.post("/users/create")
@login_required
@admin_required
def create_user():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    role = (request.form.get("role") or "user").strip()
    
    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for("users.users"))
    
    if role not in ("admin", "user"):
        role = "user"
    
    if db.session.query(User).filter(func.lower(User.username) == username.lower()).first():
        flash("A user with that username already exists.", "danger")
        return redirect(url_for("users.users"))
    
    user = User(
        username=username,
        role=role,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
    )
    db.session.add(user)
    db.session.commit()
    flash(f"User '{username}' created successfully.", "success")
    return redirect(url_for("users.users"))


@bp.post("/users/<int:user_id>/delete")
@login_required
@admin_required
def delete_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("users.users"))
    
    if user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("users.users"))
    
    if user.username == "admin":
        flash("Cannot delete the admin account.", "danger")
        return redirect(url_for("users.users"))
    
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' deleted successfully.", "success")
    return redirect(url_for("users.users"))


@bp.post("/users/<int:user_id>/toggle-role")
@login_required
@admin_required
def toggle_user_role(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("users.users"))
    
    if user.id == current_user.id:
        flash("You cannot change your own role.", "danger")
        return redirect(url_for("users.users"))
    
    if user.username == "admin":
        flash("Cannot change the admin account role.", "danger")
        return redirect(url_for("users.users"))
    
    new_role = "user" if user.role == "admin" else "admin"
    user.role = new_role
    db.session.commit()
    flash(f"User '{user.username}' role changed to {new_role}.", "success")
    return redirect(url_for("users.users"))
