import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Conversation

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('chat.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        # Validation
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return render_template('login.html', email=email)

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password. Please try again.', 'error')
            return render_template('login.html', email=email)

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('chat.index'))

    return render_template('login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle new user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('chat.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not name:
            flash('Full Name is required.', 'error')
            return render_template('signup.html', name=name, email=email)

        if not email or not re.match(EMAIL_REGEX, email):
            flash('Please enter a valid email address.', 'error')
            return render_template('signup.html', name=name, email=email)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('signup.html', name=name, email=email)

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html', name=name, email=email)

        # Check existing user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists. Please log in.', 'error')
            return render_template('signup.html', name=name, email=email)

        # Create new user
        new_user = User(name=name, email=email)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Automatically log in new user
            login_user(new_user)
            flash('Your account has been created successfully!', 'success')
            return redirect(url_for('chat.index'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during account creation. Please try again.', 'error')
            return render_template('signup.html', name=name, email=email)

    return render_template('signup.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/settings')
@login_required
def settings_page():
    """Render the user settings page."""
    return render_template('settings.html', user=current_user)


@auth_bp.route('/api/user/profile', methods=['POST'])
@login_required
def update_profile():
    """API endpoint to update user display name and email."""
    data = request.get_json() or {}
    new_name = data.get('name', '').strip()
    new_email = data.get('email', '').strip().lower()

    if not new_name:
        return jsonify({'error': 'Name cannot be empty.'}), 400

    if new_email and new_email != current_user.email:
        if not re.match(EMAIL_REGEX, new_email):
            return jsonify({'error': 'Invalid email format.'}), 400
        existing = User.query.filter_by(email=new_email).first()
        if existing:
            return jsonify({'error': 'Email is already in use by another account.'}), 409
        current_user.email = new_email

    current_user.name = new_name
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully.',
            'user': current_user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error while saving profile.'}), 500


@auth_bp.route('/api/user/password', methods=['POST'])
@login_required
def change_password():
    """API endpoint to change password."""
    data = request.get_json() or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_user.check_password(current_password):
        return jsonify({'error': 'Incorrect current password.'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters.'}), 400

    current_user.set_password(new_password)
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Password changed successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error while updating password.'}), 500

