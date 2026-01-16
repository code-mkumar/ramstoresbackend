from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Carousel, User
from utils.fileupload import FileUpload
from utils.helper import iso
import os

carousel_bp = Blueprint('carousel', __name__)

# Get active carousel images
@carousel_bp.route('', methods=['GET'])
def get_carousel():
    try:
        carousel_items = Carousel.query.filter_by(is_active=True)\
            .order_by(Carousel.display_order).all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': item.id,
                'image_url': item.image_url,
                'title': item.title,
                'subtitle': item.subtitle,
                'display_order': item.display_order
            } for item in carousel_items]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Get all carousel items (Admin only)
@carousel_bp.route('/admin/carousel', methods=['GET'])
@jwt_required()
def get_all_carousel():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        carousel_items = Carousel.query.order_by(Carousel.display_order).all()
        
        return jsonify({
            'success': True,
            'carousel': [{
                'id': item.id,
                'image_url': item.image_url,
                'title': item.title,
                'subtitle': item.subtitle,
                'is_active': item.is_active,
                'display_order': item.display_order,
                'created_at': iso(item.created_at)
            } for item in carousel_items]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Add carousel item (Admin only)
@carousel_bp.route('/admin/carousel', methods=['POST'])
@jwt_required()
def add_carousel_item():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        # Check if file is present
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image file provided'}), 400
        
        file = request.files['image']
        if not file or file.filename == '':
            return jsonify({'success': False, 'message': 'No image selected'}), 400

        # Save file
        filename = FileUpload.save_file(file, 'carousel')
        if not filename:
            return jsonify({'success': False, 'message': 'Invalid file type'}), 400

        image_url = FileUpload.get_file_url(filename, 'carousel')
        
        # Get form data
        title = request.form.get('title', '')
        subtitle = request.form.get('subtitle', '')
        display_order = request.form.get('display_order', 0, type=int)
        is_active = request.form.get('is_active', 'true').lower() == 'true'

        carousel_item = Carousel(
            image_url=image_url,
            title=title,
            subtitle=subtitle,
            display_order=display_order,
            is_active=is_active
        )

        db.session.add(carousel_item)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Carousel item added successfully',
            'item': {
                'id': carousel_item.id,
                'image_url': carousel_item.image_url,
                'title': carousel_item.title,
                'subtitle': carousel_item.subtitle
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Update carousel item (Admin only)
@carousel_bp.route('/admin/carousel/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_carousel_item(item_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        carousel_item = Carousel.query.get_or_404(item_id)
        
        # Handle file upload if new image is provided
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                # Delete old image
                if carousel_item.image_url:
                    old_filename = carousel_item.image_url.split('/')[-1]
                    FileUpload.delete_file(old_filename, 'carousel')
                
                # Save new image
                filename = FileUpload.save_file(file, 'carousel')
                if filename:
                    carousel_item.image_url = FileUpload.get_file_url(filename, 'carousel')

        # Update other fields
        data = request.form
        if 'title' in data:
            carousel_item.title = data['title']
        if 'subtitle' in data:
            carousel_item.subtitle = data['subtitle']
        if 'display_order' in data:
            carousel_item.display_order = data['display_order']
        if 'is_active' in data:
            carousel_item.is_active = data['is_active'].lower() == 'true'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Carousel item updated successfully',
            'item': {
                'id': carousel_item.id,
                'image_url': carousel_item.image_url,
                'title': carousel_item.title,
                'subtitle': carousel_item.subtitle
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Delete carousel item (Admin only)
@carousel_bp.route('/admin/carousel/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_carousel_item(item_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        carousel_item = Carousel.query.get_or_404(item_id)
        
        # Delete image file
        if carousel_item.image_url:
            filename = carousel_item.image_url.split('/')[-1]
            FileUpload.delete_file(filename, 'carousel')
        
        db.session.delete(carousel_item)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Carousel item deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500