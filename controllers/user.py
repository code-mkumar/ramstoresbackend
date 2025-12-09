from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Notification, Wishlist, Product,Order
from utils.fileupload import FileUpload
from werkzeug.security import generate_password_hash
from datetime import datetime

user_bp = Blueprint('user', __name__)

# ------------------ Get User Profile ------------------
@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'phone': user.phone,
                'address': user.address,
                'profile_image': user.profile_image,
                'role': user.role,
                'created_at': user.created_at.isoformat()
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Update User Profile ------------------
@user_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        # Handle file upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and file.filename != '':
                # Delete old image if exists
                if user.profile_image and user.profile_image != './uploads/users/profile.png':
                    old_filename = user.profile_image.split('/')[-1]
                    FileUpload.delete_file(old_filename, 'users')
                
                # Save new image
                filename = FileUpload.save_file(file, 'users')
                user.profile_image = FileUpload.get_file_url(filename, 'users')
        
        # Update other fields
        data = request.form
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'address' in data:
            user.address = data['address']
        if 'email' in data:
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
                'full_name': user.full_name,
                'phone': user.phone,
                'address': user.address,
                'profile_image': user.profile_image
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Change Password ------------------
@user_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({
                'success': False,
                'message': 'Old and new password required'
            }), 400
        
        if not user.check_password(old_password):
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 400
        
        if len(new_password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters'
            }), 400
        
        user.password = generate_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Get User Notifications ------------------
@user_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        user_id = get_jwt_identity()
        notifications = Notification.query.filter_by(user_id=user_id)\
            .order_by(Notification.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'notifications': [{
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat()
            } for notif in notifications]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Mark Notification as Read ------------------
@user_bp.route('/notifications/<int:notif_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notif_id):
    try:
        user_id = get_jwt_identity()
        notification = Notification.query.get_or_404(notif_id)
        
        if notification.user_id != int(user_id):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification marked as read'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Get Wishlist ------------------
@user_bp.route('/wishlist', methods=['GET'])
@jwt_required()
def get_wishlist():
    try:
        user_id = get_jwt_identity()
        wishlist_items = Wishlist.query.filter_by(user_id=user_id).all()
        
        result = []
        for item in wishlist_items:
            product = Product.query.get(item.product_id)
            if product and product.is_active:
                result.append({
                    'wishlist_id': item.id,
                    'product_id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'images': product.images,
                    'description': product.description,
                    'stock': product.stock,
                    'average_rating': product.average_rating(),
                    'added_at': item.added_at.isoformat()
                })
        
        return jsonify({
            'success': True,
            'wishlist': result
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Add to Wishlist ------------------
@user_bp.route('/wishlist', methods=['POST'])
@jwt_required()
def add_to_wishlist():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        product_id = data.get('product_id')
        
        # Check if product exists
        product = Product.query.get(product_id)
        if not product or not product.is_active:
            return jsonify({
                'success': False,
                'message': 'Product not found'
            }), 404
        
        # Check if already in wishlist
        existing = Wishlist.query.filter_by(
            user_id=user_id,
            product_id=product_id
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'Product already in wishlist'
            }), 400
        
        wishlist_item = Wishlist(user_id=user_id, product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Added to wishlist'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Remove from Wishlist ------------------
@user_bp.route('/wishlist/<int:wishlist_id>', methods=['DELETE'])
@jwt_required()
def remove_from_wishlist(wishlist_id):
    try:
        user_id = get_jwt_identity()
        wishlist_item = Wishlist.query.get_or_404(wishlist_id)
        
        if wishlist_item.user_id != int(user_id):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        db.session.delete(wishlist_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Removed from wishlist'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ------------------ Get User Orders ------------------
@user_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    try:
        user_id = int(get_jwt_identity())
        orders = Order.query.filter_by(user_id=user_id)\
            .order_by(Order.created_at.desc()).all()
        
        # Calculate pending count for badge (e.g., 'Pending' status)
        pending_count = len([order for order in orders if order.status == 'Pending'])
        
        result = [{
            'id': order.id,
            'order_number': order.order_number,
            'total_amount': order.total_amount,
            'status': order.status,
            'payment_status': order.payment_status,
            'created_at': order.created_at.isoformat()
        } for order in orders]
        
        return jsonify({
            'success': True,
            'orders': result,
            'pending_count': pending_count
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500