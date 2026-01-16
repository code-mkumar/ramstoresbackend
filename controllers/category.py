from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Category, User
from utils.fileupload import FileUpload
from utils.helper import iso
from sqlalchemy import or_

category_bp = Blueprint('category', __name__)

# ------------------ Get all categories ------------------
@category_bp.route('', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'data': [{
                'id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'image_url': cat.image_url,
                'parent_id': cat.parent_id,
                'subcategories': [{
                    'id': sub.id,
                    'name': sub.name
                } for sub in cat.subcategories.filter_by(is_active=True).all()],
                'product_count': cat.products.filter_by(is_active=True).count()
            } for cat in categories]
        }), 200  # CHANGED: Use 'data' key for consistency
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Search categories ------------------ (NEW)
@category_bp.route('/search', methods=['GET'])
def search_categories():
    try:
        q = request.args.get('q', '').strip().lower()
        if not q:
            return get_categories()  # Fallback to all if no query

        categories = Category.query.filter(
            Category.is_active == True,
            or_(
                Category.name.ilike(f'%{q}%'),
                Category.description.ilike(f'%{q}%')
            )
        ).all()

        return jsonify({
            'success': True,
            'data': [{
                'id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'image_url': cat.image_url,
                'parent_id': cat.parent_id,
            } for cat in categories]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Get single category ------------------
@category_bp.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    try:
        category = Category.query.get_or_404(category_id)
        return jsonify({
            'success': True,
            'data': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'image_url': category.image_url,
                'parent_id': category.parent_id,
                'is_active': category.is_active,
                'created_at': iso(category.created_at)
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Create category ------------------
@category_bp.route('/', methods=['POST'])
@jwt_required()
def create_category():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = FileUpload.save_file(file, 'categories')
                image_url = FileUpload.get_file_url(filename, 'categories')

        data = request.form
        name = data.get('name')
        description = data.get('description')
        parent_id = data.get('parent_id')

        if Category.query.filter_by(name=name).first():
            return jsonify({'success': False, 'message': 'Category already exists'}), 400

        category = Category(
            name=name,
            description=description,
            image_url=image_url,
            parent_id=parent_id
        )

        db.session.add(category)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Category created successfully',
            'data': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'image_url': category.image_url,
                'parent_id': category.parent_id
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Update category ------------------
@category_bp.route('/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        category = Category.query.get_or_404(category_id)

        # Image upload
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                if category.image_url:
                    old_filename = category.image_url.split('/')[-1]
                    FileUpload.delete_file(old_filename, 'categories')

                filename = FileUpload.save_file(file, 'categories')
                category.image_url = FileUpload.get_file_url(filename, 'categories')

        data = request.form
        category.name = data.get('name', category.name)
        category.description = data.get('description', category.description)
        category.parent_id = data.get('parent_id', category.parent_id)

        if 'is_active' in data:
            category.is_active = data.get('is_active').lower() == 'true'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Category updated successfully',
            'data': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'image_url': category.image_url,
                'parent_id': category.parent_id,
                'is_active': category.is_active
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Delete category ------------------
@category_bp.route('/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        category = Category.query.get_or_404(category_id)

        if category.products.filter_by(is_active=True).count() > 0:
            return jsonify({
                'success': False,
                'message': 'Cannot delete category with active products'
            }), 400

        category.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500