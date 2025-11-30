import qrcode
from io import BytesIO
import base64

# ------------------ Generate QR Code ------------------
def generate_qrcode(data: str) -> str:
    """
    Generates a QR code in base64 PNG format.
    
    Args:
        data (str): The string to encode in QR code (e.g., payment info)
    
    Returns:
        str: Base64 string of the QR code image
    """
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert image to base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"


# ------------------ Calculate GST ------------------
def calculate_gst(price: float, gst_percent: float) -> float:
    """
    Calculate GST amount for a product
    
    Args:
        price (float): Base price
        gst_percent (float): GST percentage
    
    Returns:
        float: GST amount
    """
    return round((price * gst_percent) / 100, 2)


# ------------------ Calculate Total Price ------------------
def calculate_total(price: float, quantity: int, gst_percent: float) -> float:
    """
    Calculate total price including GST
    
    Args:
        price (float): Base price
        quantity (int): Quantity
        gst_percent (float): GST percentage
    
    Returns:
        float: Total price including GST
    """
    gst_amount = calculate_gst(price, gst_percent)
    total = (price + gst_amount) * quantity
    return round(total, 2)
# Add this to your Product model in models.py
def average_rating(self):
    approved_reviews = self.reviews.filter_by(is_approved=True).all()
    if not approved_reviews:
        return 0
    return sum(review.rating for review in approved_reviews) / len(approved_reviews)

import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image
import json

class FileUpload:
    # Allowed extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    # Max file size (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024

    @staticmethod
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in FileUpload.ALLOWED_EXTENSIONS

    @staticmethod
    def save_file(file, folder):
        """Save uploaded file to specified folder"""
        if file and FileUpload.allowed_file(file.filename):
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset seek
            if file_size > FileUpload.MAX_FILE_SIZE:
                raise ValueError("File size too large. Maximum 5MB allowed.")

            # Generate unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            
            # Create folder if not exists
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save file
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)
            
            # Optimize image
            FileUpload.optimize_image(file_path)
            
            return unique_filename
        return None

    @staticmethod
    def optimize_image(file_path):
        """Optimize image size and quality"""
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large (max width 1200px)
                if img.width > 1200:
                    ratio = 1200 / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((1200, new_height), Image.Resampling.LANCZOS)
                
                # Save optimized image
                img.save(file_path, 'JPEG', quality=85, optimize=True)
        except Exception as e:
            print(f"Image optimization failed: {e}")

    @staticmethod
    def delete_file(filename, folder):
        """Delete file from storage"""
        if filename:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
            if os.path.exists(file_path):
                os.remove(file_path)

    @staticmethod
    def get_file_url(filename, folder):
        """Get URL for stored file"""
        if filename:
            return f"/uploads/{folder}/{filename}"
        return None

    @staticmethod
    def save_multiple_files(files, folder):
        """Save multiple files and return list of filenames"""
        filenames = []
        for file in files:
            if file and file.filename:  # Check if file is not empty
                filename = FileUpload.save_file(file, folder)
                if filename:
                    filenames.append(filename)
        return filenames