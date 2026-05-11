from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user

from config import Config


def admin_required(f):
    """Decorator to require admin role for access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        
        if current_user.role != 'admin':
            flash("Admin access required for this operation.", "danger")
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def can_edit_data(f):
    """Decorator to require edit permissions based on configuration."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        
        if not Config.is_editing_enabled(current_user.role):
            flash("You don't have permission to modify data. Read-only access.", "warning")
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function
