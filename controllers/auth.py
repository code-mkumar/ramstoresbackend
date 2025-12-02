import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from datetime import datetime
from utils.helper import *
import re
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from utils.email_services import *

GOOGLE_CLIENT_ID = "369885088133-j9n7d76p6aukqljpb76fpsfu68bq76mj.apps.googleusercontent.com"
auth_bp = Blueprint('auth', __name__)

# Helper: validate email
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ----------------- REGISTER -----------------
@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()

        # Required fields
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')

        if not username or not email or not password:
            return jsonify({'success': False, 'message': 'Username, email, and password are required'}), 400

        if len(username) < 3:
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters'}), 400

        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400

        if not is_valid_email(email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400

        # Check duplicates
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400

        # Create user
        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role=role,
            full_name=data.get('full_name', ''),
            phone=data.get('phone', ''),
            address=data.get('address', '')
        )
        db.session.add(user)
        db.session.commit()

        # JWT token
        # After creating/finding the user
        access_token = create_access_token(identity=str(user.id))

        res = send_welcome_email(email,username)

        print(res)


        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'full_name': user.full_name
            },
            'token': access_token
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ----------------- LOGIN -----------------
# In your auth controller
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        print(f"Login attempt for username: {data.get('username')}")  # Debug log
        
        user = User.query.filter_by(username=data.get('username')).first()
        
        if user and check_password_hash(user.password, data.get('password')):
            # Create access token
            access_token = create_access_token(identity=str(user.id))

            
            print(f"Login successful for user: {user.username}, role: {user.role}")  # Debug log
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'full_name': user.full_name,
                    'profile_image':user.profile_image
                }
            }), 200
        else:
            print("Login failed: Invalid credentials")  # Debug log
            return jsonify({
                'success': False, 
                'message': 'Invalid username or password'
            }), 401
            
    except Exception as e:
        print(f"Login error: {str(e)}")  # Debug log
        return jsonify({
            'success': False, 
            'message': str(e)
        }), 500
# ----------------- CURRENT USER -----------------
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'full_name': user.full_name,
                'store_name': user.store_name,
                'phone': user.phone,
                'address': user.address
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ----------------- UPDATE PROFILE -----------------
@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        data = request.get_json()

        # Update allowed fields
        for field in ['full_name', 'phone', 'address', 'store_name']:
            if field in data:
                setattr(user, field, data[field])

        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'success': False, 'message': 'Email already exists'}), 400
            if not is_valid_email(data['email']):
                return jsonify({'success': False, 'message': 'Invalid email format'}), 400
            user.email = data['email']

        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'full_name': user.full_name,
                'phone': user.phone,
                'address': user.address,
                'store_name': user.store_name
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500




# ----------------- FORGOT PASSWORD - SEND OTP -----------------
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': 'Email not found'}), 404
        
        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Store OTP with expiration time (10 minutes)
        otp_storage[email] = {
            'otp': otp,
            'expires_at': datetime.utcnow() + timedelta(minutes=10),
            'verified': False
        }
        
        # Send OTP via email
        if send_otp_email(email, otp,user.full_name):
            return jsonify({
                'success': True,
                'message': 'OTP sent to your email'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send OTP. Please try again.'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ----------------- VERIFY OTP -----------------
@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return jsonify({'success': False, 'message': 'Email and OTP are required'}), 400
        
        # Check if OTP exists for this email
        if email not in otp_storage:
            return jsonify({'success': False, 'message': 'OTP not found or expired'}), 404
        
        stored_data = otp_storage[email]
        
        # Check if OTP is expired
        if datetime.utcnow() > stored_data['expires_at']:
            del otp_storage[email]
            return jsonify({'success': False, 'message': 'OTP has expired'}), 400
        
        # Verify OTP
        if stored_data['otp'] != otp:
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
        
        # Mark OTP as verified
        otp_storage[email]['verified'] = True
        
        return jsonify({
            'success': True,
            'message': 'OTP verified successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ----------------- RESET PASSWORD -----------------
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        new_password = data.get('new_password')
        
        if not email or not otp or not new_password:
            return jsonify({'success': False, 'message': 'Email, OTP, and new password are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
        
        # Check if OTP exists and is verified
        if email not in otp_storage:
            return jsonify({'success': False, 'message': 'OTP not found or expired'}), 404
        
        stored_data = otp_storage[email]
        
        # Check if OTP is verified
        if not stored_data.get('verified', False):
            return jsonify({'success': False, 'message': 'OTP not verified'}), 400
        
        # Check if OTP matches
        if stored_data['otp'] != otp:
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
        
        # Find user and update password
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        user.password = generate_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Clear OTP from storage
        del otp_storage[email]
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    """
    Resend OTP if user didn't receive it
    """
    try:
        data = request.get_json()
        email = data.get("email")
        
        if not email:
            return jsonify({"success": False, "message": "Email is required"}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"success": False, "message": "Email not found"}), 404
        
        # Generate new OTP
        otp = str(random.randint(100000, 999999))
        
        # Update OTP storage
        otp_storage[email] = {
            "otp": otp,
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }
        
        # Send new OTP
        email_sent = send_otp_email(user.email, otp, user.full_name)
        
        if not email_sent:
            return jsonify({
                "success": False, 
                "message": "Failed to resend OTP. Please try again."
            }), 500
        
        return jsonify({
            "success": True,
            "message": "OTP resent successfully!"
        }), 200
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

@auth_bp.route('/google-login', methods=['POST'])
def google_login():
    try:
        token = request.json.get("token")

        # Verify Google token
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = idinfo["email"]
        name = idinfo.get("name", "")
        picture = idinfo.get("picture", "")

        # Check if user exists
        user = User.query.filter_by(email=email).first()

        if not user:
            # Create new user
            user = User(
                username=email.split("@")[0],
                email=email,
                full_name=name,
                password=generate_password_hash(os.urandom(16).hex()),
                role="user",
                profile_image=picture    # Save Google profile pic
            )
            db.session.add(user)
            db.session.commit()

        # Create JWT token
        access_token = create_access_token(identity=str(user.id))

        return jsonify({
            "success": True,
            "message": "Google login successful",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
                "profile_image": user.profile_image
            }
        })

    except ValueError:
        # Invalid Google token
        return jsonify({"success": False, "message": "Invalid Google token"}), 401

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400
