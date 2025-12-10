"""Authentication and authorization utilities"""
from functools import wraps
from flask import request, jsonify, redirect, url_for, flash
from flask_login import current_user
from datetime import datetime
from models import db, APIKey


def api_key_required(read=True, write=False, delete_perm=False):
    """Decorator to require valid API key for API endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get API key from header
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                return jsonify({'error': 'API key required. Include X-API-Key header.'}), 401
            
            # Validate API key
            key_obj = APIKey.query.filter_by(key=api_key, active=True).first()
            
            if not key_obj:
                return jsonify({'error': 'Invalid or inactive API key'}), 401
            
            # Check if key is expired
            if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
                return jsonify({'error': 'API key has expired'}), 401
            
            # Check permissions
            if read and not key_obj.can_read:
                return jsonify({'error': 'API key lacks read permission'}), 403
            
            if write and not key_obj.can_write:
                return jsonify({'error': 'API key lacks write permission'}), 403
            
            if delete_perm and not key_obj.can_delete:
                return jsonify({'error': 'API key lacks delete permission'}), 403
            
            # Update last used timestamp
            key_obj.last_used = datetime.utcnow()
            db.session.commit()
            
            # Store API key object in request context for access in route
            request.api_key = key_obj
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def login_required_web(f):
    """Decorator to require login for web interface routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # For AJAX requests, return JSON error instead of redirect
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required. Please log in.'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.active:
            # For AJAX requests, return JSON error instead of redirect
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return jsonify({'error': 'Your account is inactive.'}), 403
            flash('Your account is inactive. Please contact an administrator.', 'error')
            return redirect(url_for('auth.logout'))
        
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges for web interface routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.active:
            flash('Your account is inactive. Please contact an administrator.', 'error')
            return redirect(url_for('auth.logout'))
        
        if not current_user.is_admin:
            flash('Administrator privileges required.', 'error')
            return redirect(url_for('routes.index'))
        
        return f(*args, **kwargs)
    return decorated_function
