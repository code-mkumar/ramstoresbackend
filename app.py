from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os

from models import db, User

# Import all blueprints
from controllers.auth import auth_bp
from controllers.admin import admin_bp
from controllers.seller import seller_bp
from controllers.user import user_bp
from controllers.products import product_bp
from controllers.orders import order_bp
from controllers.cart import cart_bp
from controllers.category import category_bp
from controllers.review import review_bp
from controllers.cursol import carousel_bp

app = Flask(__name__)

# ------------------ Database Configuration ------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ------------------ JWT Configuration ------------------
app.config['JWT_SECRET_KEY'] = 'oiuyigvgfiwgvbpoiwfgwoifbwoiygfb88gy9y9y9y'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

# ------------------ Upload Settings ------------------
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# ------------------ Initialize Extensions ------------------
db.init_app(app)
CORS(app, resources={r"/api/*": {
    "origins": ["https://ramstoress.netlify.app"],
    "methods": ["GET", "POST", "PUT", "DELETE","OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"]
}})
jwt = JWTManager(app)


# ------------------ Utility: Create Upload Folders ------------------
def create_upload_dirs():
    upload_dirs = ['carousel', 'categories', 'products', 'users']
    for dir_name in upload_dirs:
        dir_path = os.path.join(app.config['UPLOAD_FOLDER'], dir_name)
        os.makedirs(dir_path, exist_ok=True)


# ------------------ Serve Uploaded Files ------------------
@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# ------------------ Initialize DB and Create Default Admin ------------------
def initialize_app():
    with app.app_context():
        db.create_all()
        create_upload_dirs()

# ------------------ Register Blueprints ------------------
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(seller_bp, url_prefix='/api/seller')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(product_bp, url_prefix='/api/products')
app.register_blueprint(category_bp, url_prefix='/api/categories')
app.register_blueprint(order_bp, url_prefix='/api/orders')
app.register_blueprint(cart_bp, url_prefix='/api/cart')
app.register_blueprint(review_bp, url_prefix='/api/reviews')
app.register_blueprint(carousel_bp,url_prefix='/api/carousel')


# ------------------ Run Application ------------------
if __name__ == "__main__":
    initialize_app()
    app.run(debug=True)
