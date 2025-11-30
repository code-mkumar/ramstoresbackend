from flask import Blueprint, request, jsonify
from models import db, Cart, Product
from utils.helper import calculate_total

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")

# Get user's cart
@cart_bp.route("/<int:user_id>", methods=["GET"])
def get_cart(user_id):
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    result = []
    for item in cart_items:
        product = item.product
        total_price = calculate_total(product.price, item.quantity, product.gst)
        result.append({
            "cart_id": item.id,
            "product_id": product.id,
            "name": product.name,
            "price": product.price,
            "quantity": item.quantity,
            "gst": product.gst,
            "total": total_price
        })
    return jsonify(result)


# Add item to cart
@cart_bp.route("/add", methods=["POST"])
def add_to_cart():
    data = request.json
    user_id = data["user_id"]
    product_id = data["product_id"]
    quantity = data.get("quantity", 1)

    cart_item = Cart.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()
    return jsonify({"message": "Item added to cart"})


# Update cart quantity
@cart_bp.route("/update/<int:cart_id>", methods=["PUT"])
def update_cart(cart_id):
    data = request.json
    quantity = data.get("quantity")
    cart_item = Cart.query.get_or_404(cart_id)
    cart_item.quantity = quantity
    db.session.commit()
    return jsonify({"message": "Cart updated"})


# Remove item from cart
@cart_bp.route("/remove/<int:cart_id>", methods=["DELETE"])
def remove_from_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({"message": "Item removed from cart"})


# Clear cart (after order is placed)
@cart_bp.route("/clear/<int:user_id>", methods=["DELETE"])
def clear_cart(user_id):
    Cart.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({"message": "Cart cleared"})
