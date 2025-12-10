"""Authentication routes (login, logout, user management)"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, current_user
from datetime import datetime
from models import db, User, APIKey
from auth import login_required_web, admin_required

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.active:
                flash('Your account is inactive. Please contact an administrator.', 'error')
                return render_template('auth/login.html')
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('routes.index')
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required_web
def logout():
    """Logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/users')
@admin_required
def users_list():
    """List all users (admin only)"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/users.html', users=users)


@auth_bp.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    """Create new user (admin only)"""
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'
    
    if not username or not email or not password:
        flash('Username, email, and password are required.', 'error')
        return redirect(url_for('auth.users_list'))
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('auth.users_list'))
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'error')
        return redirect(url_for('auth.users_list'))
    
    # Create user
    user = User(
        username=username,
        email=email,
        is_admin=is_admin,
        active=True
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    flash(f'User {username} created successfully.', 'success')
    return redirect(url_for('auth.users_list'))


@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user (admin only)"""
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('auth.users_list'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.username} deleted successfully.', 'success')
    return redirect(url_for('auth.users_list'))


@auth_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    """Toggle user active status (admin only)"""
    if user_id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('auth.users_list'))
    
    user = User.query.get_or_404(user_id)
    user.active = not user.active
    db.session.commit()
    
    status = 'activated' if user.active else 'deactivated'
    flash(f'User {user.username} {status} successfully.', 'success')
    return redirect(url_for('auth.users_list'))


@auth_bp.route('/api-keys')
@login_required_web
def api_keys_list():
    """List API keys for current user"""
    api_keys = APIKey.query.filter_by(user_id=current_user.id).order_by(APIKey.created_at.desc()).all()
    return render_template('auth/api_keys.html', api_keys=api_keys)


@auth_bp.route('/api-keys/create', methods=['POST'])
@login_required_web
def create_api_key():
    """Create new API key"""
    name = request.form.get('name')
    description = request.form.get('description', '')
    can_write = request.form.get('can_write') == 'on'
    can_delete = request.form.get('can_delete') == 'on'
    
    if not name:
        flash('API key name is required.', 'error')
        return redirect(url_for('auth.api_keys_list'))
    
    # Generate new API key
    api_key = APIKey(
        key=APIKey.generate_key(),
        name=name,
        description=description,
        user_id=current_user.id,
        can_read=True,  # Always allow read
        can_write=can_write,
        can_delete=can_delete,
        active=True
    )
    
    db.session.add(api_key)
    db.session.commit()
    
    flash(f'API key created: {api_key.key}', 'success')
    flash('Make sure to copy your API key now. You won\'t be able to see it again!', 'warning')
    return redirect(url_for('auth.api_keys_list'))


@auth_bp.route('/api-keys/<int:key_id>/delete', methods=['POST'])
@login_required_web
def delete_api_key(key_id):
    """Delete API key"""
    api_key = APIKey.query.get_or_404(key_id)
    
    # Ensure user owns this key or is admin
    if api_key.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to delete this API key.', 'error')
        return redirect(url_for('auth.api_keys_list'))
    
    db.session.delete(api_key)
    db.session.commit()
    
    flash(f'API key {api_key.name} deleted successfully.', 'success')
    return redirect(url_for('auth.api_keys_list'))


@auth_bp.route('/api-keys/<int:key_id>/toggle', methods=['POST'])
@login_required_web
def toggle_api_key(key_id):
    """Toggle API key active status"""
    api_key = APIKey.query.get_or_404(key_id)
    
    # Ensure user owns this key or is admin
    if api_key.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to modify this API key.', 'error')
        return redirect(url_for('auth.api_keys_list'))
    
    api_key.active = not api_key.active
    db.session.commit()
    
    status = 'activated' if api_key.active else 'deactivated'
    flash(f'API key {api_key.name} {status} successfully.', 'success')
    return redirect(url_for('auth.api_keys_list'))
