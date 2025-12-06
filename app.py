from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os
import base64 
from models import db, User
from sqlalchemy import text, inspect

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

# # ------------------ Database Configuration ------------------
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ------------------ Database Configuration ------------------
# Render PostgreSQL URL (set in Render dashboard)
POSTGRES_URL = "postgresql://ramstores_user:xtKhcBiv23nf6osGJuoMiNvb5snlWQOz@dpg-d4psbaqdbo4c73bgq4vg-a.oregon-postgres.render.com/ramstores"

if not POSTGRES_URL:
    raise ValueError("❌ DATABASE_URL environment variable not set!")

# Fix SSL issue for Render PostgreSQL
if POSTGRES_URL.startswith("postgres://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgres://", "postgresql+psycopg://")
else:
    POSTGRES_URL = "postgresql+psycopg://" + POSTGRES_URL.split("://")[1]

app.config["SQLALCHEMY_DATABASE_URI"] = POSTGRES_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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


def initialize_app():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables ready")
        except Exception as e:
            print("❌ Error during DB init:", str(e))
            raise

        # ----------- CREATE DEFAULT ADMIN USER -----------
        from models import User
        from werkzeug.security import generate_password_hash

        admin = User.query.filter_by(username="admin").first()

        if not admin:
            print("👑 Creating default admin user...")
            admin = User(
                username="admin",
                password=generate_password_hash("admin123"),  # default password
                role="admin",
                full_name="Admin User",
                email="admin@example.com"
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created: admin / admin123")
        else:
            print("👑 Admin user already exists")

        # ----------- UPLOAD FOLDERS -----------
        create_upload_dirs()
        print("📁 Upload directories ready")



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


if __name__ == "__main__":
    initialize_app()
    port = int(os.environ.get("PORT", 5000))  # Render assigns a PORT
    app.run(host="0.0.0.0", port=port, debug=True)
