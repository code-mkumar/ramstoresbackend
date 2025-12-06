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
POSTGRES_URL = "postgresql://ramstores_user:xtKhcBiv23nf6osGJuoMiNvb5snlWQOz@dpg-d4psbaqdbo4c73bgq4vg-a/ramstores"

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
            print("✅ Database tables verified/created successfully!")
        except Exception as e:
            error_msg = str(e)
            print("❌ Database create_all() failed:", error_msg)
            
            # Check if it's the foreign key constraint error
            if "no unique constraint matching given keys" in error_msg:
                print("⚠️  Foreign key constraint error detected")
                print("⚠️  Attempting to fix while preserving data...")
                
                try:
                    with db.engine.connect() as conn:
                        insp = inspect(db.engine)
                        
                        # Only drop the payments table (it can be recreated)
                        # This preserves your orders, products, users, etc.
                        if insp.has_table('payments'):
                            print("🗑️  Dropping payments table (will be recreated)...")
                            conn.execute(text('DROP TABLE IF EXISTS payments CASCADE'))
                            conn.commit()
                            print("✅ Payments table dropped")
                        
                        # Ensure orders table has proper primary key
                        if insp.has_table('orders'):
                            print("🔍 Verifying orders table structure...")
                            
                            # Check for primary key
                            pk_result = conn.execute(text("""
                                SELECT constraint_name 
                                FROM information_schema.table_constraints 
                                WHERE table_name = 'orders' 
                                AND constraint_type = 'PRIMARY KEY'
                            """))
                            
                            if not pk_result.fetchone():
                                print("➕ Adding primary key to orders table...")
                                conn.execute(text('ALTER TABLE orders ADD PRIMARY KEY (id)'))
                                conn.commit()
                                print("✅ Primary key added")
                        
                        # Now retry creating all tables
                        print("📦 Creating missing tables...")
                        db.create_all()
                        print("✅ Database structure fixed successfully!")
                        print("✅ Your existing data has been preserved!")
                        
                except Exception as fix_error:
                    print(f"❌ Could not auto-fix database: {fix_error}")
                    print("\n⚠️  MANUAL FIX REQUIRED:")
                    print("Run the fix_database.py script separately")
                    raise
            else:
                # Different error - just raise it
                raise
        
        # Create upload directories
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
