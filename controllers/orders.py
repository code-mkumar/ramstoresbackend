from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Review, db, Order, User, Product, OrderItem
from utils.helper import generate_qrcode, calculate_total
import random
import string
import datetime
from utils.email_services import send_order_confirmation_email

order_bp = Blueprint('order', __name__)

def generate_order_number():
    """Generate unique order number"""
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD{timestamp}{random_str}"

# Create order
@order_bp.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    try:
        # ✅ FIX: Cast JWT identity to int
        current_user_id = int(get_jwt_identity())
        data = request.get_json()

        items = data.get("items")
        if not items:
            return jsonify({'success': False, 'message': 'No items found'}), 400

        # ✅ Fetch user safely
        user = User.query.get_or_404(current_user_id)

        # Create order
        order_number = generate_order_number()
        order = Order(
            user_id=current_user_id,
            order_number=order_number,
            total_amount=0
        )

        db.session.add(order)
        db.session.flush()  # ✅ get order.id

        total_amount = 0
        created_items = []

        for item in items:
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])

            product = Product.query.get_or_404(product_id)

            if product.stock < quantity:
                db.session.rollback()
                return jsonify({
                    "success": False,
                    "message": f"Insufficient stock for {product.name}"
                }), 400

            unit_price = product.price
            gst_amount = (unit_price * product.gst) / 100
            total_price = (unit_price + gst_amount) * quantity

            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )

            db.session.add(order_item)
            created_items.append(order_item)

            total_amount += total_price
            product.stock -= quantity  # ✅ reduce stock

        order.total_amount = total_amount
        db.session.commit()

        # ✅ Send mail & track status
        mail_status = False
        mail_message = "Email not sent"

        try:
            mail_res = send_order_confirmation_email(
                total_amount=total_amount,
                order_number=order_number,
                user_name=user.full_name or user.username,
                to_email=user.email
            )
            mail_status = True
            mail_message = "Order confirmation email sent"
            print(mail_res)

        except Exception as mail_error:
            mail_message = str(mail_error)
            print("Mail Error:", mail_error)

        return jsonify({
            "success": True,
            "message": "Order placed successfully",
            "mail_sent": mail_status,
            "mail_message": mail_message,
            "order": {
                "order_id": order.id,
                "order_number": order.order_number,
                "total_amount": order.total_amount,
                "items": [
                    {
                        "product_id": oi.product_id,
                        "product_name": oi.product.name,
                        "quantity": oi.quantity,
                        "unit_price": oi.unit_price,
                        "total_price": oi.total_price
                    } for oi in created_items
                ]
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Order creation failed",
            "error": str(e)
        }), 500

@order_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_user_orders():
    try:
        current_user_id = get_jwt_identity()

        orders = (
            Order.query.filter_by(user_id=current_user_id)
            .order_by(Order.created_at.desc())
            .all()
        )

        result = []

        for order in orders:
            order_items = OrderItem.query.filter_by(order_id=order.id).all()

            items_data = []
            for item in order_items:

                # Check if user already reviewed this product
                has_reviewed = Review.query.filter_by(
                    user_id=current_user_id,
                    product_id=item.product_id
                ).first() is not None

                items_data.append({
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price,
                    "has_reviewed": has_reviewed
                })

            result.append({
                "id": order.id,
                "order_number": order.order_number,
                "total_amount": order.total_amount,
                "status": order.status,
                "payment_status": order.payment_status,
                "created_at": order.created_at.isoformat(),
                "items": items_data
            })

        return jsonify({"success": True, "orders": result}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Generate payment QR code for order
@order_bp.route('/orders/<int:order_id>/payment-qr', methods=['GET'])
@jwt_required()
def get_payment_qr(order_id):
    try:
        current_user_id = get_jwt_identity()
        order = Order.query.get_or_404(order_id)
        
        # Check if user owns the order or is admin
        user = User.query.get(current_user_id)
       
        # Generate UPI payment QR code
        upi_id = "your-store@upi"  # Replace with your UPI ID
        upi_url = f"upi://pay?pa={upi_id}&pn=Your%20Store&am={order.total_amount}&cu=INR&tn=Order%20{order.order_number}"
        
        qr_code = generate_qrcode(upi_url)

        return jsonify({
            'success': True,
            'qr_code': qr_code,
            'order_number': order.order_number,
            'total_amount': order.total_amount
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500