import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from models import db, Product, Category, User, Review

product_bp = Blueprint('product', __name__)

# Get all products with filtering and pagination
@product_bp.route('/products', methods=['GET'])
def get_products():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 4, type=int)
        category_id = request.args.get('category_id', type=int)
        search = request.args.get('search', '')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)

        query = Product.query.filter_by(is_active=True)

        # Apply filters
        if category_id:
            query = query.filter_by(category_id=category_id)

        if search:
            query = query.filter(
                or_(
                    Product.name.ilike(f'%{search}%'),
                    Product.description.ilike(f'%{search}%')
                )
            )
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        # Pagination
        products = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )

        return jsonify({
            'success': True,
            'products': [{
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': product.price,
                'stock': product.stock,
                'description': product.description,
                'images_files': json.loads(product.images) if product.images else [],
                'gst': product.gst,
                'category_id': product.category_id,
                'category_name': product.category.name,
                'category_img': product.category.image_url,  # Added category image
                'average_rating': product.average_rating(),
                'review_count': product.reviews.filter_by(is_approved=True).count(),
                'ratings': product.ratings(),                # ➤ Added
                'rating_breakdown': product.rating_breakdown(),  # ➤ Added
                'created_at': product.created_at.isoformat()
            } for product in products.items],
            'pagination': {
                'page': products.page,
                'per_page': products.per_page,
                'total': products.total,
                'pages': products.pages
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Get single product
@product_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        if not product.is_active:
            return jsonify({'success': False, 'message': 'Product not found'}), 404

        return jsonify({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': product.price,
                'stock': product.stock,
                'description': product.description,
                'images_files': json.loads(product.images) if product.images else [],
                'gst': product.gst,
                'category_id': product.category_id,
                'category_name': product.category.name,
                'category_img': product.category.image_url,  # Added category image
                'is_active': product.is_active,
                'average_rating': product.average_rating(),
                'review_count': product.reviews.filter_by(is_approved=True).count(),
                'created_at': product.created_at.isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ... rest of the product controller remains the same ...

# Create product (Seller only)
@product_bp.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        

        data = request.get_json()
        
        # Validate category exists
        category = Category.query.get(data.get('category_id'))
        if not category:
            return jsonify({'success': False, 'message': 'Invalid category'}), 400

        product = Product(
            name=data.get('name'),
            sku=data.get('sku'),
            category_id=data.get('category_id'),
            price=data.get('price'),
            stock=data.get('stock', 0),
            description=data.get('description'),
            images=data.get('img'),
            gst=data.get('gst', 0),
            seller_id=current_user_id
        )

        db.session.add(product)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Product created successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': product.price
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Update product (Seller only - only their own products)
@product_bp.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    try:
        current_user_id = get_jwt_identity()
        product = Product.query.get_or_404(product_id)

        # Check if user owns the product or is admin
        if product.seller_id != current_user_id:
            user = User.query.get(current_user_id)
            if user.role != 'admin':
                return jsonify({'success': False, 'message': 'Access denied'}), 403

        data = request.get_json()
        
        updatable_fields = ['name', 'price', 'stock', 'description', 'img', 'gst', 'category_id', 'is_active']
        for field in updatable_fields:
            if field in data:
                setattr(product, field, data[field])

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Product updated successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'stock': product.stock
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Delete product (Seller only - soft delete)
@product_bp.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    try:
        current_user_id = get_jwt_identity()
        product = Product.query.get_or_404(product_id)

        # Check if user owns the product or is admin
        
        user = User.query.get(current_user_id)
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403

        # Soft delete
        product.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Product deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Get seller's products
@product_bp.route('/seller/products', methods=['GET'])
@jwt_required()
def get_seller_products():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        products = Product.query.filter_by(seller_id=current_user_id).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )

        return jsonify({
            'success': True,
            'products': [{
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': product.price,
                'stock': product.stock,
                'category_name': product.category.name,
                'is_active': product.is_active,
                'total_orders': product.orders.count(),
                'average_rating': product.average_rating(),
                'created_at': product.created_at.isoformat()
            } for product in products.items],
            'pagination': {
                'page': products.page,
                'per_page': products.per_page,
                'total': products.total,
                'pages': products.pages
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500