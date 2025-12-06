from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ---------------------------------------------------------
# CAROUSEL
# ---------------------------------------------------------
class Carousel(db.Model):
    __tablename__ = 'carousel'

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200))
    subtitle = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    display_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Carousel {self.id} - {self.title}>"

# ---------------------------------------------------------
# USERS
# ---------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user', index=True)

    full_name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, index=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    store_name = db.Column(db.String(120))
    gst_number = db.Column(db.String(50))

    profile_image = db.Column(db.String(500), default='uploads/users/profile.png')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = db.relationship('Order', backref='customer', lazy=True)
    cart_items = db.relationship('Cart', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    payments = db.relationship("Payment", backref="user", lazy=True)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @validates('role')
    def validate_role(self, key, role):
        assert role in ['admin', 'user']
        return role

    @validates('email')
    def validate_email(self, key, email):
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        return email

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

# ---------------------------------------------------------
# CATEGORIES
# ---------------------------------------------------------
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))

    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete="CASCADE"), nullable=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Self relationship
    subcategories = db.relationship(
        'Category',
        backref=db.backref('parent', remote_side=[id]),
        cascade="all,delete",
        lazy="dynamic"
    )

    # Category → Products
    products = db.relationship(
        'Product',
        backref='category',
        cascade="all,delete",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Category {self.name}>"

# ---------------------------------------------------------
# PRODUCTS
# ---------------------------------------------------------
class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    sku = db.Column(db.String(50), unique=True, index=True)

    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete="CASCADE"), nullable=False, index=True)

    stock = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)

    images = db.Column(db.Text, nullable=True)
    gst = db.Column(db.Float, default=0.0)

    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cart_entries = db.relationship('Cart', backref='product', lazy='dynamic')
    reviews = db.relationship('Review', backref='product', lazy='dynamic')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    @validates('price', 'gst')
    def validate_positive_values(self, key, value):
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value

    @validates('stock')
    def validate_stock(self, key, stock):
        if stock < 0:
            raise ValueError("Stock cannot be negative")
        return stock

    def __repr__(self):
        return f"<Product {self.name} (₹{self.price})>"

# ---------------------------------------------------------
# ORDERS
# ---------------------------------------------------------
class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    order_number = db.Column(db.String(50), unique=True, index=True)
    total_amount = db.Column(db.Float, nullable=False)

    status = db.Column(db.String(20), default='Pending', index=True)
    payment_status = db.Column(db.String(10), default='Unpaid', index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('OrderItem', backref='order', lazy=True)
    payments = db.relationship("Payment", backref="order", lazy=True)

    def __repr__(self):
        return f"<Order {self.order_number}>"

# ---------------------------------------------------------
# ORDER ITEMS
# ---------------------------------------------------------
class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)

    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<OrderItem Order:{self.order_id} Product:{self.product_id}>"

# ---------------------------------------------------------
# PAYMENTS
# ---------------------------------------------------------
class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    payment_id = db.Column(db.String(100), unique=True)
    order_payment_id = db.Column(db.String(100))
    signature = db.Column(db.String(200))

    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')

    status = db.Column(db.String(20), default='Pending', index=True)
    payment_method = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Payment {self.id} - Order {self.order_id}>"

# ---------------------------------------------------------
# CART
# ---------------------------------------------------------
class Cart(db.Model):
    __tablename__ = 'cart'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)

    quantity = db.Column(db.Integer, nullable=False, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='_user_product_uc'),
    )

    def __repr__(self):
        return f"<Cart User:{self.user_id} Product:{self.product_id}>"

# ---------------------------------------------------------
# REVIEWS
# ---------------------------------------------------------
class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)

    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)

    is_approved = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='_user_product_review_uc'),
    )

    def __repr__(self):
        return f"<Review User:{self.user_id} Product:{self.product_id}>"

# ---------------------------------------------------------
# NOTIFICATIONS
# ---------------------------------------------------------
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)

    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Notification User:{self.user_id}>"

# ---------------------------------------------------------
# WISHLIST
# ---------------------------------------------------------
class Wishlist(db.Model):
    __tablename__ = 'wishlist'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='_user_product_wishlist_uc'),
    )

    def __repr__(self):
        return f"<Wishlist User:{self.user_id} Product:{self.product_id}>"
