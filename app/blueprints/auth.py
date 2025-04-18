# blueprints/auth.py
from datetime import datetime
from flask import Blueprint, abort, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import case
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import db, User
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


bp = Blueprint('auth', __name__)

limiter = Limiter(key_func=get_remote_address)


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('auth.login'))

        if not user.active:
            flash('Account disabled')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        return redirect(url_for('parts.gallery'))

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


# Admin-only user management
@bp.route('/users')
@login_required
def user_list():
    if not current_user.is_admin:
        abort(403)

    users = User.query.order_by(
        db.case(
            (User.role == 'superadmin', 0),
            (User.role == 'admin', 1),
            (User.role == 'member', 2),
            (User.role == 'user', 3),
            else_=4
        ),
        User.last_name.asc()
    ).all()

    # Counts for each section
    counts = {
        'superadmin': len([u for u in users if u.role == 'superadmin']),
        'admin': len([u for u in users if u.role == 'admin' and not u.is_member]),
        'member': len([u for u in users if u.is_member and u.role not in ['superadmin', 'admin']]),
        'user': len([u for u in users if not u.is_member and u.role == 'user'])
    }

    return render_template('user_list.html', users=users, counts=counts)


@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Manual form handling
        current_user.username = request.form.get('username', current_user.username)
        current_user.email = request.form.get('email', current_user.email)

        # Add validation if you want
        if not current_user.email or '@' not in current_user.email:
            flash('Invalid email', 'error')
        else:
            db.session.commit()
            flash('Profile updated!', 'success')
            return redirect(url_for('auth.profile'))

    # GET request - show current values
    return render_template('edit_profile.html', 
                           username=current_user.username,
                           email=current_user.email)


@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Basic validation
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'error')
        elif len(new_password) < 8:
            flash('Password must be at least 8 characters', 'error')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('auth.profile'))

    return render_template('change_password.html')


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per hour")
def register():
    if request.method == 'POST':
        # Validate form data
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))

        # Generate membership number (VRPYYYYMMDD0001 format)
        today = datetime.now().strftime('%Y%m%d')
        last_member = User.query.filter(
            User.membership_number.like(f'VRP{today}%')
        ).order_by(User.membership_number.desc()).first()

        seq_num = int(last_member.membership_number[-4:]) + 1 if last_member else 1
        membership_number = f'VRP{today}{seq_num:04d}'

        # Create user
        user = User(
            username=email,  # Using email as username
            email=email,
            role='member',
            membership_number=membership_number,
            first_name=request.form.get('first_name'),
            last_name=request.form.get('last_name'),
            phone=request.form.get('phone'),
            address_line1=request.form.get('address_line1'),
            address_line2=request.form.get('address_line2'),
            city=request.form.get('city'),
            postcode=request.form.get('postcode'),
            country=request.form.get('country')
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(f'Registration successful! Your membership number is {membership_number}', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@login_required
def user_detail(user_id):
    if not current_user.is_superadmin:
        abort(403)

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        # Handle form submission
        action = request.form.get('action')

        if action == 'update_profile':
            user.email = request.form.get('email', user.email)
            user.first_name = request.form.get('first_name', user.first_name)
            user.last_name = request.form.get('last_name', user.last_name)
            user.phone = request.form.get('phone', user.phone)
            user.active = 'active' in request.form
            db.session.commit()
            flash('Profile updated', 'success')

        elif action == 'change_role':
            new_role = request.form.get('role')
            if new_role in ['user', 'member', 'admin', 'superadmin']:
                user.role = new_role
                db.session.commit()
                flash(f'Role changed to {new_role}', 'success')

        elif action == 'reset_password':
            new_password = request.form.get('new_password')
            if len(new_password) >= 8:
                user.set_password(new_password)
                db.session.commit()
                flash('Password reset successfully', 'success')
            else:
                flash('Password must be at least 8 characters', 'error')

        return redirect(url_for('auth.user_detail', user_id=user.id))

    return render_template('user_detail.html', user=user)


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_superadmin:
        abort(403)

    user = User.query.get_or_404(user_id)

    # Prevent self-deletion
    if user.id == current_user.id:
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('auth.user_list'))

    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.email} deleted', 'success')
    return redirect(url_for('auth.user_list'))


@bp.route('/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if not current_user.is_superadmin:
        abort(403)
    user = User.query.get_or_404(user_id)
    user.active = not user.active
    db.session.commit()

    flash(f'User {user.email} has been {"activated" if user.active else "deactivated"}', 'success')
    return redirect(url_for('auth.user_list'))
