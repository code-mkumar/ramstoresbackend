from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
import os

db = SQLAlchemy()

# ------------------ Carousel ------------------
class Carousel(db.Model):
    __tablename__ = 'carousel'

    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200))
    subtitle = db.Column(db.String(300))
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Carousel {self.id} - {self.title}>"


# ------------------ Users ------------------
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
    profile_image = db.Column(db.String(500),default='./uploads/users/profile.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders = db.relationship('Order', backref='customer', lazy=True)
    cart_items = db.relationship('Cart', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)

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


# ------------------ Categories ------------------
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete="CASCADE"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Corrected self-referential relationship
    subcategories = db.relationship(
        'Category',
        backref=db.backref('parent', remote_side=[id]),
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="dynamic"
    )

    # Corrected products relationship
    products = db.relationship(
        'Product',
        backref='category',
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Category {self.name}>"

# ------------------ Products ------------------
class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    sku = db.Column(db.String(50), unique=True, index=True)
    category_id = db.Column(
    db.Integer, 
    db.ForeignKey('categories.id', ondelete="CASCADE"), 
    nullable=False, 
    index=True
    )
    stock = db.Column(db.Integer, default=0, nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    images = db.Column(db.Text, nullable=True) 
    gst = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    
    cart_entries = db.relationship('Cart', backref='product', lazy='dynamic')
    reviews = db.relationship('Review', backref='product', lazy='dynamic')

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

    def average_rating(self):
        """Calculate average rating from approved reviews"""
        from models import Review  # Import here to avoid circular imports
        approved_reviews = Review.query.filter_by(
            product_id=self.id, 
            is_approved=True
        ).all()
        
        if not approved_reviews:
            return 0
        return round(sum(review.rating for review in approved_reviews) / len(approved_reviews), 1)

    def calculate_gst_amount(self):
        """Calculate GST amount for this product"""
        from utils.helper import calculate_gst
        return calculate_gst(self.price, self.gst)

    def calculate_total_with_gst(self, quantity=1):
        """Calculate total price including GST for given quantity"""
        from utils.helper import calculate_total
        return calculate_total(self.price, quantity, self.gst)

    def __repr__(self):
        return f"<Product {self.name} (₹{self.price})>"
# ------------------ Orders ------------------
class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    order_number = db.Column(db.String(50), unique=True, index=True)  # Human-readable order ID
    total_amount = db.Column(db.Float, nullable=False)  # Calculated from order items
    status = db.Column(db.String(20), default='Pending', index=True)  # Pending / Confirmed / Shipped / Delivered / Cancelled
    payment_status = db.Column(db.String(10), default='Unpaid', index=True)  # Unpaid / Paid / Refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Validators
    @validates('status')
    def validate_status(self, key, status):
        valid_statuses = ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled']
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return status

    @validates('payment_status')
    def validate_payment_status(self, key, payment_status):
        valid_payment_statuses = ['Unpaid', 'Paid', 'Refunded']
        if payment_status not in valid_payment_statuses:
            raise ValueError(f"Payment status must be one of {valid_payment_statuses}")
        return payment_status

    def __repr__(self):
        return f"<Order {self.order_number} - User {self.user_id}>"


# ------------------ Order Items ------------------
class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    order = db.relationship('Order', backref='items')
    product = db.relationship('Product', backref='order_items')

    @validates('quantity')
    def validate_quantity(self, key, quantity):
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")
        return quantity

    def __repr__(self):
        return f"<OrderItem Order:{self.order_id} Product:{self.product_id}>"


# ------------------ Payments ------------------
class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Razorpay fields
    payment_id = db.Column(db.String(100), unique=True, nullable=True)   # Razorpay payment ID
    order_payment_id = db.Column(db.String(100), nullable=True)          # Razorpay order ID
    signature = db.Column(db.String(200), nullable=True)                 # Verification signature
    
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    status = db.Column(db.String(20), default='Pending', index=True)     # Pending / Completed / Failed / Refunded
    payment_method = db.Column(db.String(50), nullable=True)             # card / upi / etc.

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = db.relationship("Order", backref=db.backref("payments", lazy=True))
    user = db.relationship("User", backref=db.backref("payments", lazy=True))

    @validates('status')
    def validate_status(self, key, status):
        valid_statuses = ['Pending', 'Completed', 'Failed', 'Refunded']
        if status not in valid_statuses:
            raise ValueError(f"Payment status must be one of {valid_statuses}")
        return status

    def __repr__(self):
        return f"<Payment {self.id} - Order {self.order_id} - Status {self.status}>"

# ------------------ Cart ------------------
class Cart(db.Model):
    __tablename__ = 'cart'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='_user_product_uc'),)

    @validates('quantity')
    def validate_quantity(self, key, quantity):
        if quantity < 1:
            raise ValueError("Quantity must be at least 1")
        return quantity

    def __repr__(self):
        return f"<Cart User:{self.user_id} Product:{self.product_id} Qty:{self.quantity}>"


# ------------------ Reviews ------------------
class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    

    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='_user_product_review_uc'),)

    @validates('rating')
    def validate_rating(self, key, rating):
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return rating

    def __repr__(self):
        return f"<Review User:{self.user_id} Product:{self.product_id} Rating:{self.rating}>"
    
# ------------------ Notifications ------------------
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Notification User:{self.user_id} Title:{self.title}>"


# ------------------ Wishlist ------------------
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

