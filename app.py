from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os
import base64 
from models import db, User, Order, OrderItem
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


def fix_boolean_columns():
    """Fix boolean columns if they are incorrectly typed as text in the database."""
    try:
        with db.engine.connect() as conn:
            # List of (table, column) pairs to check/fix
            boolean_columns = [
                ('carousel', 'is_active'),
                ('categories', 'is_active'),
                ('products', 'is_active'),
                ('reviews', 'is_approved'),
                ('notifications', 'is_read')
            ]

            for table, column in boolean_columns:
                # Check current type
                result = conn.execute(text("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = :table AND column_name = :column
                """), {'table': table, 'column': column})
                
                row = result.fetchone()
                if row and row[0] != 'boolean':
                    print(f"🔧 Fixing {table}.{column} from {row[0]} to boolean")
                    
                    # Alter the column
                    conn.execute(text(f"""
                        ALTER TABLE {table} 
                        ALTER COLUMN {column} TYPE BOOLEAN 
                        USING (CASE 
                            WHEN {column} IN ('true', 't', '1', 'yes') THEN true 
                            WHEN {column} IN ('false', 'f', '0', 'no') THEN false 
                            ELSE NULL 
                        END)
                    """))
            
            conn.commit()
            print("✅ Boolean columns fixed")
    except Exception as e:
        print(f"⚠️ Could not fix boolean columns: {e}")
        # Don't raise; continue with app init

def add_missing_order_columns():
    """Add missing payment-related columns to orders table"""
    try:
        with db.engine.connect() as conn:
            print("🔧 Checking and adding missing columns to orders table...")
            
            # List of columns to add: (column_name, data_type, constraints)
            columns_to_add = [
                ('payment_id', 'VARCHAR(255)', 'UNIQUE'),
                ('order_payment_id', 'VARCHAR(255)', ''),
                ('signature', 'VARCHAR(500)', ''),
                ('amount', 'DECIMAL(10, 2)', ''),
                ('currency', 'VARCHAR(10)', "DEFAULT 'INR'"),
                ('payment_method', 'VARCHAR(50)', ''),
                ('payment_status_detail', 'TEXT', ''),
            ]
            
            for column_name, data_type, constraints in columns_to_add:
                # Check if column exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'orders' 
                    AND column_name = :column_name
                """), {'column_name': column_name})
                
                if not result.fetchone():
                    # Column doesn't exist, add it
                    alter_query = f"ALTER TABLE orders ADD COLUMN {column_name} {data_type}"
                    if constraints:
                        alter_query += f" {constraints}"
                    
                    print(f"   Adding column: {column_name}")
                    conn.execute(text(alter_query))
                else:
                    print(f"   ✓ Column {column_name} already exists")
            
            conn.commit()
            print("✅ All missing columns added successfully!")
            
            # Verify the columns
            print("\n📋 Current orders table structure:")
            result = conn.execute(text("""
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'orders'
                ORDER BY ordinal_position
            """))
            
            for row in result:
                nullable = "NULL" if row[3] == 'YES' else "NOT NULL"
                length = f"({row[2]})" if row[2] else ""
                print(f"   - {row[0]}: {row[1]}{length} {nullable}")
                
    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        raise


def ensure_primary_keys_and_constraints():
    """Ensure primary keys and unique constraints exist for referenced tables."""
    try:
        with db.engine.connect() as conn:
            # List of tables to ensure PRIMARY KEY on 'id'
            tables_with_pk = ['users', 'orders', 'categories', 'products', 'carousel']
            
            for table in tables_with_pk:
                # Check if PRIMARY KEY exists on 'id'
                result = conn.execute(text("""
                    SELECT conname 
                    FROM pg_constraint 
                    WHERE conrelid = :table::regclass 
                    AND contype = 'p' 
                    AND conkey = ARRAY[1]::int2[]
                """), {'table': table})
                
                if not result.fetchone():
                    print(f"🔧 Adding PRIMARY KEY to {table}.id")
                    conn.execute(text(f"ALTER TABLE {table} ADD PRIMARY KEY (id);"))
                
                # Also ensure 'id' is NOT NULL if not already (should be, but just in case)
                result = conn.execute(text("""
                    SELECT is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = :table AND column_name = 'id'
                """), {'table': table})
                
                row = result.fetchone()
                if row and row[0] == 'YES':
                    print(f"🔧 Making {table}.id NOT NULL")
                    conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN id SET NOT NULL;"))
            
            # Specific UNIQUE constraints if needed
            # For users.username UNIQUE
            result = conn.execute(text("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'users'::regclass 
                AND contype = 'u' 
                AND conkey = ARRAY[2]::int2[]  -- Assuming username is 2nd column
            """))
            if not result.fetchone():
                print("🔧 Adding UNIQUE constraint to users.username")
                conn.execute(text("ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username);"))
            
            # For products.sku
            result = conn.execute(text("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'products'::regclass 
                AND contype = 'u' 
                AND conkey = ARRAY[3]::int2[]  -- Adjust index if needed
            """))
            if not result.fetchone():
                print("🔧 Adding UNIQUE constraint to products.sku")
                conn.execute(text("ALTER TABLE products ADD CONSTRAINT products_sku_key UNIQUE (sku);"))
            
            # For orders.order_number
            result = conn.execute(text("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'orders'::regclass 
                AND contype = 'u' 
                AND conkey = ARRAY[3]::int2[]
            """))
            if not result.fetchone():
                print("🔧 Adding UNIQUE constraint to orders.order_number")
                conn.execute(text("ALTER TABLE orders ADD CONSTRAINT orders_order_number_key UNIQUE (order_number);"))
            
            # For orders.payment_id (newly added)
            result = conn.execute(text("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'orders'::regclass 
                AND contype = 'u' 
                AND conkey = ARRAY[8]::int2[]  -- Adjust based on column position
            """))
            if not result.fetchone():
                print("🔧 Adding UNIQUE constraint to orders.payment_id")
                conn.execute(text("ALTER TABLE orders ADD CONSTRAINT orders_payment_id_key UNIQUE (payment_id);"))
            
            conn.commit()
            print("✅ Primary keys and constraints ensured")
    except Exception as e:
        print(f"⚠️ Could not ensure primary keys/constraints: {e}")


def initialize_app():
    with app.app_context():
        add_missing_order_columns()
        try:
            # Drop specific tables: order_items first (depends on orders), then orders
            with db.engine.connect() as conn:
                print("🗑️ Dropping order_items table...")
                conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE;"))
                
                print("🗑️ Dropping orders table...")
                conn.execute(text("DROP TABLE IF EXISTS orders CASCADE;"))
            
            db.create_all()
            print("✅ Database tables ready")
            
            # Ensure primary keys and constraints (fixes existing schema issues)
            ensure_primary_keys_and_constraints()
            
            # Fix any boolean type mismatches
            fix_boolean_columns()
            
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