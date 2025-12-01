# controllers/admin_controller.py
import json
from flask import Blueprint, current_app, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Product, Order, Review, Category, Carousel,Notification
from werkzeug.security import generate_password_hash
from utils.fileupload import FileUpload
from utils.helper import *
import os
from werkzeug.utils import secure_filename
import shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
import io
from flask import send_file

from sqlalchemy import text


admin_bp = Blueprint('admin', __name__)

# ==================== ADMIN STATS ====================
@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    try:
        current_user_id = get_jwt_identity()
        print("JWT identity:", current_user_id)
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        stats = {
            'users': User.query.count(),
            'products': Product.query.filter_by(is_active=True).count(),
            'orders': Order.query.count(),
            'categories': Category.query.filter_by(is_active=True).count(),
            'reviews': Review.query.count(),
            'pending_reviews': Review.query.filter_by(is_approved=False).count(),
            'revenue': db.session.query(db.func.sum(Order.total_amount)).scalar() or 0,
        }

        return jsonify({'success': True, **stats}), 200

    except Exception as e:
        print("Stats error:", e)
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== USER MANAGEMENT ====================
@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        users = User.query.all()
        return jsonify({
            'success': True,
            'users': [{
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'full_name': u.full_name,
                'store_name': u.store_name,
                'phone': u.phone,
                'address': u.address,
                'created_at': u.created_at.isoformat()
            } for u in users]
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/users', methods=['POST'])
@jwt_required()
def create_user():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        data = request.get_json()
        
        # Check if user already exists
        if User.query.filter_by(username=data.get('username')).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        if User.query.filter_by(email=data.get('email')).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400

        # Create new user
        new_user = User(
            username=data.get('username'),
            email=data.get('email'),
            password=generate_password_hash(data.get('password')),
            role=data.get('role', 'user'),
            full_name=data.get('full_name', ''),
            store_name=data.get('store_name', ''),
            phone=data.get('phone', ''),
            address=data.get('address', '')
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'role': new_user.role
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        user = User.query.get_or_404(user_id)
        data = request.get_json()

        # Update fields
        if 'username' in data:
            existing_user = User.query.filter_by(username=data['username']).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'success': False, 'message': 'Username already taken'}), 400
            user.username = data['username']
        
        if 'email' in data:
            existing_email = User.query.filter_by(email=data['email']).first()
            if existing_email and existing_email.id != user_id:
                return jsonify({'success': False, 'message': 'Email already taken'}), 400
            user.email = data['email']
        
        if 'role' in data:
            user.role = data['role']
        
        if 'full_name' in data:
            user.full_name = data['full_name']
        
        if 'store_name' in data:
            user.store_name = data['store_name']
        
        if 'phone' in data:
            user.phone = data['phone']
        
        if 'address' in data:
            user.address = data['address']
        
        if 'password' in data and data['password']:
            user.password = generate_password_hash(data['password'])

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        user = User.query.get_or_404(user_id)
        
        if user.id == current_user_id:
            return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400

        db.session.delete(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== PRODUCT MANAGEMENT ====================
@admin_bp.route('/products', methods=['GET'])
@jwt_required()
def get_all_products():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        products = Product.query.all()
        return jsonify({
            'success': True,
            'products': [{
                'id': p.id,
                'name': p.name,
                'sku': p.sku,
                'price': p.price,
                'stock': p.stock,
                'description': p.description,
                'images_files': p.images,
                'gst': p.gst,
                'category_id': p.category_id,
                'category_name': p.category.name if p.category else None,
                'is_active': p.is_active,
                'created_at': p.created_at.isoformat()
            } for p in products]
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/products', methods=['POST'])
@jwt_required()
def create_product():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        # Get form data
        name = request.form.get("name")
        sku = request.form.get("sku")
        price = float(request.form.get("price"))
        stock = int(request.form.get("stock"))
        category_id = int(request.form.get("category_id"))
        
        gst = float(request.form.get("gst"))
        is_active = request.form.get("is_active") == "true"
        description = request.form.get("description")
        image_urls = request.form.get("images_files")

        # Create product
        new_product = Product(
            name=name,
            sku=sku,
            price=price,
            stock=stock,
            gst=gst,
            category_id=category_id,
            is_active=is_active,
            description=description,
            images = json.dumps(image_urls),
        )

        db.session.add(new_product)
        db.session.commit()

        # Create folder for product
        product_folder = f"uploads/products/{new_product.name}"
        os.makedirs(product_folder, exist_ok=True)

        # Handle multiple image uploads
        images_files = request.files.getlist("images_files")
        image_urls = []

        for file in images_files:
            if file:
                filename = secure_filename(file.filename)
                filepath = os.path.join(product_folder, filename)
                file.save(filepath)
                image_urls.append(f"/{filepath.replace('\\', '/')}")

        # Save image URLs as JSON
        new_product.images = json.dumps(image_urls)
        db.session.commit()

        # Serialize product manually
        product_data = {
            "id": new_product.id,
            "name": new_product.name,
            "sku": new_product.sku,
            "price": new_product.price,
            "stock": new_product.stock,
            "gst": new_product.gst,
            "category_id": new_product.category_id,
            "is_active": new_product.is_active,
            "description": new_product.description,
            "images": json.loads(new_product.images) if new_product.images else []
        }

        return jsonify({
            "success": True,
            "message": "Product created successfully",
            "product": product_data
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@admin_bp.route('/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        product = Product.query.get_or_404(product_id)

        name = request.form.get('name', product.name)
        sku = request.form.get('sku', product.sku)
        price = float(request.form.get('price', product.price))
        stock = int(request.form.get('stock', product.stock))
        description = request.form.get('description', product.description)
        gst = float(request.form.get('gst', product.gst))
        category_id = request.form.get('category_id', product.category_id)
        is_active = request.form.get('is_active', str(product.is_active)).lower() == 'true'

        # Check SKU uniqueness
        if sku != product.sku:
            if Product.query.filter_by(sku=sku).first():
                return jsonify({'success': False, 'message': 'SKU already exists'}), 400

        # Delete old folder (optional)
        old_folder = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            "products",
            secure_filename(product.name)
        )
        if os.path.exists(old_folder):
            try:
                for f in os.listdir(old_folder):
                    os.remove(os.path.join(old_folder, f))
                os.rmdir(old_folder)
            except:
                pass

        # MULTIPLE IMAGE SAVE
        uploaded_images = []
        files = request.files.getlist("images_files")

        for file in files:
            saved = FileUpload.save_file_in_subfolder(
                file=file,
                base_folder="products",
                subfolder=name
            )
            if saved:
                uploaded_images.append(saved)

        product.name = name
        product.sku = sku
        product.price = price
        product.stock = stock
        product.description = description
        product.gst = gst
        product.category_id = category_id
        product.is_active = is_active
        product.images = json.dumps(uploaded_images)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Product updated successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'images': uploaded_images
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        product = Product.query.get_or_404(product_id)

        # 🔥 DELETE PRODUCT IMAGE FOLDER
        product_folder = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            "products",
            secure_filename(product.name)
        )

        if os.path.exists(product_folder):
            try:
                shutil.rmtree(product_folder)   # deletes entire folder
                print(f"Deleted folder: {product_folder}")
            except Exception as e:
                print("Folder delete error:", e)

        # Delete product record
        db.session.delete(product)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Product and images deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500



import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

@admin_bp.route('/orders/confirm-all', methods=['POST'])
@jwt_required()
def confirm_all_orders():

    try:
        # Admin validation
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user or user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        pending_orders = Order.query.filter_by(status="Pending").all()
        if len(pending_orders) == 0:
            return jsonify({'success': False, 'message': 'No pending orders'}), 400

        # Create PDF
        pdf_buffer = io.BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=A4)

        for order in pending_orders:
            pdf.setFont("Helvetica-Bold", 20)
            pdf.drawString(200, 800, "RAM STORES")

            pdf.setFont("Helvetica", 12)
            pdf.drawString(50, 770, f"Order Number: {order.order_number}")
            pdf.drawString(50, 750, f"Customer: {order.customer.username}")
            pdf.drawString(50, 730, f"Order Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")

            pdf.line(50, 710, 550, 710)
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, 690, "Product")
            pdf.drawString(250, 690, "Qty")
            pdf.drawString(350, 690, "Price")
            pdf.drawString(450, 690, "Total")
            pdf.line(50, 680, 550, 680)

            y = 660
            pdf.setFont("Helvetica", 12)
            for item in order.items:
                pdf.drawString(50, y, item.product.name)
                pdf.drawString(250, y, str(item.quantity))
                pdf.drawString(350, y, f"₹{item.unit_price}")
                pdf.drawString(450, y, f"₹{item.total_price}")
                y -= 20

            pdf.line(50, y - 10, 550, y - 10)
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(50, y - 40, f"Grand Total: ₹{order.total_amount}")

            pdf.showPage()
            order.status = "Confirmed"

        db.session.commit()

        pdf.save()
        pdf_buffer.seek(0)

        # Base64 encode PDF
        pdf_base64 = base64.b64encode(pdf_buffer.read()).decode('utf-8')

        response = jsonify({
            'success': True,
            'pdf': pdf_base64,
            'filename': 'all_orders_bill.pdf'
        })
        return response

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ORDER MANAGEMENT ====================
@admin_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_all_orders():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        orders = Order.query.all()
        
        orders_data = []
        for o in orders:
            items = [{
                'product_id': item.product_id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total_price': item.total_price
            } for item in o.items]  # assuming relationship Order.items
            
            orders_data.append({
                'id': o.id,
                'order_number': o.order_number,
                'user_id': o.user_id,
                'user_name': o.customer.username,
                'total_amount': o.total_amount,
                'status': o.status,
                'payment_status': o.payment_status,
                'created_at': o.created_at.isoformat(),
                'items': items  # include the order items
            })
        
        return jsonify({'success': True, 'orders': orders_data}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/orders/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order(order_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        order = Order.query.get_or_404(order_id)
        data = request.get_json()

        # Update fields
        if 'status' in data:
            valid_statuses = ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled']
            if data['status'] not in valid_statuses:
                return jsonify({'success': False, 'message': 'Invalid status'}), 400
            order.status = data['status']
        
        if 'payment_status' in data:
            valid_payment_statuses = ['Unpaid', 'Paid', 'Refunded']
            if data['payment_status'] not in valid_payment_statuses:
                return jsonify({'success': False, 'message': 'Invalid payment status'}), 400
            order.payment_status = data['payment_status']
        
        if 'quantity' in data:
            order.quantity = data['quantity']
            # Recalculate total amount
            order.total_amount = order.quantity * order.unit_price

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Order updated successfully',
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'payment_status': order.payment_status
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/orders/<int:order_id>', methods=['DELETE'])
@jwt_required()
def delete_order(order_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        order = Order.query.get_or_404(order_id)

        db.session.delete(order)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Order deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== CATEGORY MANAGEMENT ====================
@admin_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_all_categories():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        categories = Category.query.all()
        
        
        
        return jsonify({
            'success': True,
            'categories': [{
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'image_url': request.host_url+get_full_image_url(c.image_url),
                'parent_id': c.parent_id,
                'parent_name': c.parent.name if c.parent else None,
                'is_active': c.is_active,
                'subcategories_count': c.subcategories.count(),
                'products_count': c.products.count(),
                'created_at': c.created_at.isoformat()
            } for c in categories]
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/categories', methods=['POST'])
@jwt_required()
def create_category():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        # Handle multipart form data for file upload
        image_file = request.files.get('image')
        name = request.form.get('name')
        description = request.form.get('description', '')
        parent_id = int(request.form.get('parent_id', 0)) if request.form.get('parent_id') else None
        is_active = request.form.get('is_active', 'true').lower() == 'true'
        
        if not name:
            return jsonify({'success': False, 'message': 'Category name is required'}), 401
        
        # Check if category name already exists
        if Category.query.filter_by(name=name).first():
            return jsonify({'success': False, 'message': 'Category name already exists'}), 402

        image_url = ''
        if image_file and image_file.filename:
            # Save using category name
            filename = FileUpload.save_file(image_file, 'categories', custom_name=name)
            if filename:
                image_url = FileUpload.get_file_url(filename, 'categories')
            else:
                return jsonify({'success': False, 'message': 'Failed to upload image'}), 400


        # Create new category
        new_category = Category(
            name=name,
            description=description,
            image_url=image_url,
            parent_id=parent_id,
            is_active=is_active
        )

        db.session.add(new_category)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Category created successfully',
            'category': {
                'id': new_category.id,
                'name': new_category.name,
                'description': new_category.description,
                'image_url': new_category.image_url
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/categories/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        category = Category.query.get_or_404(category_id)

        # Handle multipart form data for optional file upload
        image_file = request.files.get('image')
        name = request.form.get('name', category.name)
        description = request.form.get('description', category.description)
        parent_id = int(request.form.get('parent_id', category.parent_id)) if request.form.get('parent_id') else category.parent_id
        is_active = request.form.get('is_active', str(category.is_active)).lower() == 'true'
        existing_image_url = request.form.get('image_url', category.image_url)

        # Check name uniqueness if changed
        if name != category.name:
            existing_category = Category.query.filter_by(name=name).first()
            if existing_category and existing_category.id != category_id:
                return jsonify({'success': False, 'message': 'Category name already taken'}), 400
            category.name = name
        
        # Update description
        category.description = description
        
        # Handle new image upload if provided
        if image_file and image_file.filename:
            # Delete old image if exists
            if category.image_url:
                FileUpload.delete_file(category.image_url, 'categories')

            # Save using updated category name
            filename = FileUpload.save_file(image_file, 'categories', custom_name=name)
            if filename:
                category.image_url = FileUpload.get_file_url(filename, 'categories')
            else:
                return jsonify({'success': False, 'message': 'Failed to upload image'}), 401

        else:
            # Use existing or provided image_url
            category.image_url = existing_image_url
        
        # Prevent circular reference for parent_id
        # if parent_id and parent_id == category_id:
        #     return jsonify({'success': False, 'message': 'Category cannot be its own parent'}), 402
        category.parent_id = parent_id
        
        category.is_active = is_active

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Category updated successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'image_url': category.image_url
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        category = Category.query.get_or_404(category_id)
        
        # Check if category has products
        if len(category.products) > 0:
            return jsonify({
                'success': False, 
                'message': 'Cannot delete category with existing products'
            }), 400
        
        # Check if category has subcategories
        if len(category.subcategories) > 0:
            return jsonify({
                'success': False, 
                'message': 'Cannot delete category with existing subcategories'
            }), 400

        # Delete associated image file if exists
        if category.image_url and os.path.exists(category.image_url):
            try:
                os.remove(category.image_url)
            except OSError:
                pass  # Ignore if file doesn't exist

        db.session.delete(category)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Category deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    
# ------------------------------------------------------------
# GET ALL REVIEWS (Admin Panel)
# ------------------------------------------------------------
@admin_bp.route("/reviews", methods=["GET"])
@jwt_required()
def get_all_reviews():
    try:
        admin_id = get_jwt_identity()
        user = User.query.get(admin_id)

        if user.role != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403

        reviews = Review.query.all()

        return jsonify([{
            "id": r.id,
            "user_id": r.user_id,
            "user_name": r.user.username,
            "product_id": r.product_id,
            "product_name": r.product.name,
            "rating": r.rating,
            "comment": r.comment,
            "is_approved": r.is_approved,
            "created_at": r.created_at.isoformat()
        } for r in reviews]), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------------------------------------
# GET ONLY PENDING REVIEWS
# ------------------------------------------------------------
@admin_bp.route("/reviews/pending", methods=["GET"])
@jwt_required()
def get_pending_reviews():
    try:
        admin_id = get_jwt_identity()
        user = User.query.get(admin_id)

        if user.role != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403

        reviews = Review.query.filter_by(is_approved=False).all()

        return jsonify({
            "success": True,
            "reviews": [{
                "id": r.id,
                "user_id": r.user_id,
                "user_name": r.user.username,
                "product_id": r.product_id,
                "product_name": r.product.name,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": r.created_at.isoformat()
            } for r in reviews]
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------------------------------------
# CREATE A REVIEW (Admin manual creation)
# ------------------------------------------------------------
@admin_bp.route("/reviews", methods=["POST"])
@jwt_required()
def create_review():
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        if admin.role != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403

        data = request.get_json()

        new_review = Review(
            user_id=data["user_id"],
            product_id=data["product_id"],
            rating=data["rating"],
            comment=data.get("comment", ""),
            is_approved=data.get("is_approved", True)
        )

        db.session.add(new_review)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Review created successfully",
            "review": {
                "id": new_review.id,
                "rating": new_review.rating,
                "is_approved": new_review.is_approved
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------------------------------------
# UPDATE REVIEW (Admin)
# ------------------------------------------------------------
@admin_bp.route("/reviews/<int:review_id>", methods=["PUT"])
@jwt_required()
def update_review(review_id):
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        if admin.role != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403

        review = Review.query.get_or_404(review_id)
        data = request.get_json()

        if "rating" in data:
            if not (1 <= data["rating"] <= 5):
                return jsonify({"success": False, "message": "Rating must be 1–5"}), 400
            review.rating = data["rating"]

        if "comment" in data:
            review.comment = data["comment"]

        if "is_approved" in data:
            review.is_approved = data["is_approved"]

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Review updated",
            "review": {
                "id": review.id,
                "rating": review.rating,
                "is_approved": review.is_approved
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# ------------------------------------------------------------
# DELETE REVIEW (Admin)
# ------------------------------------------------------------
@admin_bp.route("/reviews/<int:review_id>", methods=["DELETE"])
@jwt_required()
def delete_review(review_id):
    try:
        admin_id = get_jwt_identity()
        admin = User.query.get(admin_id)

        if admin.role != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403

        review = Review.query.get_or_404(review_id)
        db.session.delete(review)
        db.session.commit()

        return jsonify({"success": True, "message": "Review deleted"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    
# ==================== CAROUSEL MANAGEMENT ====================
@admin_bp.route('/carousel', methods=['GET'])
@jwt_required()
def get_all_carousel():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        # Helper function to get full URL
        def get_full_image_url(image_url):
            if not image_url:
                return None
            if image_url.startswith('http'):
                return image_url
            clean_path = image_url.lstrip('/')
            return f"{request.host_url}{clean_path}"

        carousel_items = Carousel.query.order_by(Carousel.display_order).all()
        
        # Frontend expects 'data' key based on fetchCarousel logic
        return jsonify({
            'success': True,
            'data': [{
                'id': c.id,
                'image_url': get_full_image_url(c.image_url),  # ← Full URL
                'title': c.title,
                'subtitle': c.subtitle,
                'is_active': c.is_active,
                'display_order': c.display_order,
                'created_at': c.created_at.isoformat()
            } for c in carousel_items]
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/carousel', methods=['POST'])
@jwt_required()
def create_carousel():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        image_file = request.files.get('image')
        title = request.form.get('title', '')
        subtitle = request.form.get('subtitle', '')
        is_active = request.form.get('is_active', 'true').lower() == 'true'
        display_order = int(request.form.get('display_order', 0))

        image_url = ''
        if image_file and image_file.filename:
            # Use static method to save file and get filename
            filename = FileUpload.save_file(image_file, 'carousel')
            if filename:
                # Store full URL
                image_url = FileUpload.get_file_url(filename, 'carousel')
            else:
                return jsonify({'success': False, 'message': 'Failed to upload image'}), 400

        new_carousel = Carousel(
            image_url=image_url,
            title=title,
            subtitle=subtitle,
            is_active=is_active,
            display_order=display_order
        )

        db.session.add(new_carousel)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Carousel item created successfully',
            'carousel': {
                'id': new_carousel.id,
                'title': new_carousel.title,
                'image_url': new_carousel.image_url
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print(str(e))
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/carousel/<int:carousel_id>', methods=['PUT'])
@jwt_required()
def update_carousel(carousel_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        carousel = Carousel.query.get_or_404(carousel_id)

        image_file = request.files.get('image')
        title = request.form.get('title', carousel.title)
        subtitle = request.form.get('subtitle', carousel.subtitle)
        is_active = request.form.get('is_active', str(carousel.is_active)).lower() == 'true'
        display_order = int(request.form.get('display_order', carousel.display_order))
        existing_image_url = request.form.get('image_url', carousel.image_url)

        if image_file and image_file.filename:
            # Delete old image if exists (extract filename from URL)
            if carousel.image_url:
                old_filename = os.path.basename(carousel.image_url)
                FileUpload.delete_file(old_filename, 'carousel')

            # Upload new image
            filename = FileUpload.save_file(image_file, 'carousel')
            if filename:
                carousel.image_url = FileUpload.get_file_url(filename, 'carousel')
            else:
                return jsonify({'success': False, 'message': 'Failed to upload image'}), 400
        else:
            carousel.image_url = existing_image_url

        carousel.title = title
        carousel.subtitle = subtitle
        carousel.is_active = is_active
        carousel.display_order = display_order

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Carousel item updated successfully',
            'carousel': {
                'id': carousel.id,
                'title': carousel.title,
                'image_url': carousel.image_url
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/carousel/<int:carousel_id>', methods=['DELETE'])
@jwt_required()
def delete_carousel(carousel_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        carousel = Carousel.query.get_or_404(carousel_id)

        # Delete image file (extract filename from URL)
        if carousel.image_url:
            old_filename = os.path.basename(carousel.image_url)
            FileUpload.delete_file(old_filename, 'carousel')

        db.session.delete(carousel)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Carousel item deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    

@admin_bp.route('/dropdown/all', methods=['GET'])
@jwt_required()
def get_dropdown_options():
    print("=== /dropdown/all ROUTE HIT ===")  # This MUST appear in Flask console
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        categories = Category.query.filter_by(is_active=True).all()
        categories_data = [{'id': c.id, 'name': c.name} for c in categories]
        print(f"Queried {len(categories_data)} categories")  # Debug

        
        resp = jsonify({
            'success': True,
            'categories': categories_data,
        })
        resp.headers['Content-Type'] = 'application/json'  # Force JSON
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp, 200

    except Exception as e:
        print(f"Dropdown route error: {e}")  # Log exceptions
        return jsonify({'success': False, 'message': str(e)}), 500
    

# ------------------ Get all notifications ------------------
@admin_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_all_notifications():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        notifications = (
            db.session.query(Notification)
            .order_by(Notification.created_at.desc())
            .all()
        )

        notifications_data = []
        for n in notifications:
            # If sent to all users
            if n.user_id is None:
                username = "All Users"
            else:
                u = User.query.get(n.user_id)
                username = u.username if u else "Unknown User"

            notifications_data.append({
                'id': n.id,
                'username': username,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat()
            })

        return jsonify({'success': True, 'notifications': notifications_data}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ------------------ Update notification (mark as read/unread) ------------------
@admin_bp.route('/notifications/<int:id>', methods=['PUT'])
@jwt_required()
def update_notification(id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        notification = Notification.query.get(id)
        if not notification:
            return jsonify({'success': False, 'message': 'Notification not found'}), 404

        data = request.json
        if 'is_read' in data:
            notification.is_read = data['is_read']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Notification updated'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ------------------ Delete notification ------------------
@admin_bp.route('/notifications/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_notification(id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        notification = Notification.query.get(id)
        if not notification:
            return jsonify({'success': False, 'message': 'Notification not found'}), 404

        db.session.delete(notification)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Notification deleted'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
@admin_bp.route('/notifications', methods=['POST'])
@jwt_required()
def create_notification():
    try:
        current_user_id = get_jwt_identity()
        admin_user = User.query.get(current_user_id)

        if not admin_user or admin_user.role != "admin":
            return jsonify({'success': False, 'message': 'Admin access required'}), 403

        data = request.get_json()
        title = data.get('title')
        message = data.get('message')
        user_id = data.get('user_id')  # Can be a number or "all"

        if not title or not message:
            return jsonify({'success': False, 'message': 'Title and message are required'}), 400

        notifications_created = []

        if user_id == "all":
            users = User.query.all()
            for user in users:
                notif = Notification(
                    user_id=user.id,
                    title=title,
                    message=message,
                    created_at= datetime.utcnow() + timedelta(hours=5, minutes=30)
                )
                db.session.add(notif)
                notifications_created.append(user.id)
        else:
            # Single user notification
            target_user = User.query.get(user_id)
            if not target_user:
                return jsonify({'success': False, 'message': 'Target user not found'}), 404
            notif = Notification(
                user_id=target_user.id,
                title=title,
                message=message,
                created_at=datetime.utcnow()
            )
            db.session.add(notif)
            notifications_created.append(target_user.id)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Notification(s) created',
            'user_ids': notifications_created
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500