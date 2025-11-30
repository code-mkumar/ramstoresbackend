from app import app, db  # Import your Flask app and database
from models import User  # Import User model

with app.app_context():
    # Check if admin already exists
    existing_admin = User.query.filter_by(username='admin').first()
    if existing_admin:
        print("Admin user already exists.")
    else:
        # Create a new admin
        admin_user = User(
            username='admin',
            full_name='Administrator',
            email='admin@example.com',
            role='admin'
        )
        admin_user.set_password('Admin@123')  # Secure hashed password

        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created successfully.")
