from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os
from models import db, User
from sqlalchemy import text

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
POSTGRES_URL = "postgresql://groceryshop_ej5r_user:BPaNF1NQL9L8VPKCN835WaZmJFB0kuj3@dpg-d5l2klngi27c738heh2g-a.oregon-postgres.render.com/groceryshop_ej5r"

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



def fix_column_types():
    try:
        print("\n🔧 Starting full PostgreSQL column fix...\n")

        fixes = [
            # orders table
            ("orders", "total_amount", "DOUBLE PRECISION"),
            ("orders", "amount", "DOUBLE PRECISION"),
            ("orders", "created_at", "TIMESTAMP"),
            ("orders", "updated_at", "TIMESTAMP"),

            # order_items table
            ("order_items", "unit_price", "DOUBLE PRECISION"),
            ("order_items", "total_price", "DOUBLE PRECISION"),
            ("order_items", "quantity", "INTEGER"),

            # users table
            ("users", "created_at", "TIMESTAMP"),
            ("users", "updated_at", "TIMESTAMP"),

            # products table
            ("products", "price", "DOUBLE PRECISION"),
            ("products", "gst", "DOUBLE PRECISION"),
            ("products", "stock", "INTEGER"),
            ("products", "created_at", "TIMESTAMP"),
            ("products", "updated_at", "TIMESTAMP"),

            # cart table
            ("cart", "quantity", "INTEGER"),
            ("cart", "created_at", "TIMESTAMP"),
            ("cart", "updated_at", "TIMESTAMP"),

            # reviews table
            ("reviews", "rating", "INTEGER"),
            ("reviews", "created_at", "TIMESTAMP"),
            ("reviews", "updated_at", "TIMESTAMP"),

            # wishlist / notification
            ("wishlist", "added_at", "TIMESTAMP"),
            ("notifications", "created_at", "TIMESTAMP"),
        ]

        with db.engine.connect() as conn:
            for table, column, new_type in fixes:

                # check table exists
                exists = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='{table}' AND column_name='{column}'
                    );
                """)).scalar()

                if not exists:
                    continue

                # get current type
                current = conn.execute(text(f"""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name='{table}' AND column_name='{column}'
                """)).scalar()

                if current is None:
                    continue

                # ONLY fix if TEXT (text = type OID 25)
                if current != "text":
                    continue

                print(f"🔄 Fixing {table}.{column} (was TEXT) → {new_type}")

                # Add temp column
                conn.execute(text(f"""
                    ALTER TABLE {table}
                    ADD COLUMN {column}_temp {new_type};
                """))

                # Copy data safely
                if "TIMESTAMP" in new_type:
                    conn.execute(text(f"""
                        UPDATE {table}
                        SET {column}_temp = 
                            CASE 
                                WHEN {column} ~ '^[0-9]{4}-' THEN {column}::timestamp
                                ELSE NULL
                            END;
                    """))
                elif "DOUBLE" in new_type:
                    conn.execute(text(f"""
                        UPDATE {table}
                        SET {column}_temp = 
                            CASE 
                                WHEN {column} ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN {column}::DOUBLE PRECISION
                                ELSE 0
                            END;
                    """))
                elif "INTEGER" in new_type:
                    conn.execute(text(f"""
                        UPDATE {table}
                        SET {column}_temp = 
                            CASE 
                                WHEN {column} ~ '^[0-9]+$' THEN {column}::INTEGER
                                ELSE 0
                            END;
                    """))

                # Replace old column
                conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {column};"))
                conn.execute(text(f"ALTER TABLE {table} RENAME COLUMN {column}_temp TO {column};"))

            conn.commit()

        print("\n✅ All TEXT numeric/timestamp columns fixed successfully!\n")

    except Exception as e:
        print(f"\n❌ ERROR in fix_column_types(): {e}\n")

def fix_postgres_sequences():
    """
    Fix AUTOINCREMENT issue after SQLite → PostgreSQL migration
    Safe to run multiple times
    """
    try:
        with db.engine.begin() as conn:
            print("🔧 Fixing PostgreSQL sequences for all tables...")

            tables = conn.execute(text("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
            """)).fetchall()

            for (table_name,) in tables:
                # Skip Alembic table if exists
                if table_name == 'alembic_version':
                    continue

                # Check if table has an id column
                has_id = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :table
                    AND column_name = 'id'
                """), {'table': table_name}).fetchone()

                if not has_id:
                    continue

                seq_name = f"{table_name}_id_seq"

                print(f"   🔹 Processing {table_name}.id")

                # Create sequence if missing
                conn.execute(text(f"""
                    CREATE SEQUENCE IF NOT EXISTS {seq_name}
                """))

                # Attach sequence to column
                conn.execute(text(f"""
                    ALTER TABLE {table_name}
                    ALTER COLUMN id
                    SET DEFAULT nextval('{seq_name}')
                """))

                # Sync sequence with max(id)
                conn.execute(text(f"""
                    SELECT setval(
                        '{seq_name}',
                        COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1,
                        false
                    )
                """))

            print("✅ PostgreSQL AUTOINCREMENT fixed successfully")

    except Exception as e:
        print("❌ Error fixing sequences:", e)


def add_missing_columns():
    """Add missing payment columns if they don't exist"""
    try:
        with db.engine.connect() as conn:
            print("🔧 Adding missing payment columns...")
            
            columns_to_add = [
                ('payment_id', 'VARCHAR(100)', 'UNIQUE'),
                ('order_payment_id', 'VARCHAR(100)', ''),
                ('signature', 'VARCHAR(200)', ''),
                ('amount', 'DOUBLE PRECISION', 'NOT NULL DEFAULT 0'),
                ('currency', 'VARCHAR(10)', "DEFAULT 'INR'"),
                ('payment_method', 'VARCHAR(50)', ''),
                ('payment_status_detail', 'VARCHAR(20)', "DEFAULT 'Pending'"),
            ]
            
            for column_name, data_type, constraints in columns_to_add:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'orders' 
                    AND column_name = :column_name
                """), {'column_name': column_name})
                
                if not result.fetchone():
                    alter_query = f"ALTER TABLE orders ADD COLUMN {column_name} {data_type}"
                    if constraints:
                        alter_query += f" {constraints}"
                    
                    print(f"   Adding: {column_name}")
                    conn.execute(text(alter_query))
                else:
                    print(f"   ✓ {column_name} exists")
            
            conn.commit()
            print("✅ Missing columns added!")
            
    except Exception as e:
        print(f"⚠️ Error adding columns: {e}")


def fix_boolean_columns():
    """Fix boolean columns if they are incorrectly typed as text"""
    try:
        with db.engine.connect() as conn:
            boolean_columns = [
                ('carousel', 'is_active'),
                ('categories', 'is_active'),
                ('products', 'is_active'),
                ('reviews', 'is_approved'),
                ('notifications', 'is_read')
            ]

            for table, column in boolean_columns:
                result = conn.execute(text("""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = :table AND column_name = :column
                """), {'table': table, 'column': column})
                
                row = result.fetchone()
                if row and row[0] != 'boolean':
                    print(f"🔧 Fixing {table}.{column} to boolean")
                    
                    conn.execute(text(f"""
                        ALTER TABLE {table} 
                        ALTER COLUMN {column} TYPE BOOLEAN 
                        USING (CASE 
                            WHEN {column} IN ('true', 't', '1', 'yes') THEN true 
                            WHEN {column} IN ('false', 'f', '0', 'no') THEN false 
                            ELSE false 
                        END)
                    """))
            
            conn.commit()
            print("✅ Boolean columns fixed")
    except Exception as e:
        print(f"⚠️ Could not fix boolean columns: {e}")


def initialize_app():
    with app.app_context():
        try:
            # Step 1: Create all tables (if they don't exist)
            db.create_all()
            print("✅ Database tables created/verified")

            fix_postgres_sequences()
            
            # Step 2: Fix column types AFTER tables exist
            fix_column_types()
            
            # Step 3: Add missing columns
            add_missing_columns()
            
            # Step 4: Fix boolean columns
            fix_boolean_columns()
            
        except Exception as e:
            print("❌ Error during DB init:", str(e))
            raise

        # Create default admin user
        from werkzeug.security import generate_password_hash

        admin = User.query.filter_by(username="admin").first()

        if not admin:
            print("👑 Creating default admin user...")
            admin = User(
                username="admin",
                password=generate_password_hash("admin123"),
                role="admin",
                full_name="Admin User",
                email="admin@example.com"
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created: admin / admin123")
        else:
            print("👑 Admin user already exists")

        # Create upload folders
        create_upload_dirs()
        print("📁 Upload directories ready")


# ------------------ Register Blueprints ------------------
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(seller_bp, url_prefix='/api/api')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(product_bp, url_prefix='/api/products')
app.register_blueprint(category_bp, url_prefix='/api/categories')
app.register_blueprint(order_bp, url_prefix='/api/orders')
app.register_blueprint(cart_bp, url_prefix='/api/cart')
app.register_blueprint(review_bp, url_prefix='/api/reviews')
app.register_blueprint(carousel_bp, url_prefix='/api/carousel')


if __name__ == "__main__":
    initialize_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
