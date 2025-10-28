from flask import request, jsonify
from database import db, User
import re

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Password should be at least 6 characters"""
    return len(password) >= 6

def register_user(username, email, password):
    """Register a new user"""
    try:
        # Validation
        if not username or len(username) < 3:
            return {'success': False, 'error': 'Username must be at least 3 characters'}
        
        if not validate_email(email):
            return {'success': False, 'error': 'Invalid email format'}
        
        if not validate_password(password):
            return {'success': False, 'error': 'Password must be at least 6 characters'}
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return {'success': False, 'error': 'Username already exists'}
        
        if User.query.filter_by(email=email).first():
            return {'success': False, 'error': 'Email already registered'}
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return {'success': True, 'message': 'User registered successfully', 'user': user.to_dict()}
    
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}

def login_user(username, password):
    """Authenticate user login"""
    try:
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return {'success': False, 'error': 'Username not found'}
        
        if not user.check_password(password):
            return {'success': False, 'error': 'Invalid password'}
        
        return {'success': True, 'message': 'Login successful', 'user': user.to_dict(), 'user_id': user.id}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        user = User.query.get(user_id)
        if user:
            return {'success': True, 'user': user.to_dict()}
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
