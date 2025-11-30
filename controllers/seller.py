from flask import Blueprint, request, jsonify
from models import db, Product, User

seller_bp = Blueprint("seller", __name__, url_prefix="/api/seller")

# Get all products by seller
@seller_bp.route("/products/<int:seller_id>", methods=["GET"])
def get_products(seller_id):
    products = Product.query.filter_by(seller_id=seller_id).all()
    return jsonify([{
        "id": p.id, "name": p.name, "category": p.category, "price": p.price,
        "stock": p.stock, "description": p.description, "gst": p.gst, "img": p.img
    } for p in products])

# Add product
@seller_bp.route("/products", methods=["POST"])
def add_product():
    data = request.json
    product = Product(
        name=data["name"],
        category=data.get("category"),
        stock=data.get("stock",0),
        price=data["price"],
        description=data.get("description"),
        img=data.get("img"),
        gst=data.get("gst",0),
        seller_id=data["seller_id"]
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({"message":"Product added"})

# Update stock
@seller_bp.route("/products/<int:product_id>/stock", methods=["PUT"])
def update_stock(product_id):
    data = request.json
    stock = data.get("stock")
    product = Product.query.get_or_404(product_id)
    product.stock = stock
    db.session.commit()
    return jsonify({"message":"Stock updated"})
