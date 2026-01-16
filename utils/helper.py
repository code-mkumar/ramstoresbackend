import qrcode
from io import BytesIO
import base64

def fmt(dt, fmt="%Y-%m-%d %H:%M:%S"):
    return dt.strftime(fmt) if dt else None

def iso(dt):
    return dt.isoformat() if dt else None

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


# Helper function to get full URL
def get_full_image_url(image_url):
    if not image_url:
        return None
    if image_url.startswith('http'):
        return image_url
    # Remove leading slash if present
    clean_path = image_url.lstrip('/')
    return f"{clean_path}"

# Add these imports at the top of your auth.py file
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Store OTPs temporarily (in production, use Redis or database)
otp_storage = {}

# Email configuration - Add these to your environment variables
EMAIL_HOST = 'smtp.gmail.com'  # or your SMTP server
EMAIL_PORT = 587
EMAIL_USER = 'your-email@gmail.com'  # Your email
EMAIL_PASSWORD = 'your-app-password'  # Your app password

# Helper function to send email
def send_otp_email(to_email, otp):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = 'Password Reset OTP'
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #667eea;">Password Reset Request</h2>
            <p>You have requested to reset your password.</p>
            <p>Your OTP code is:</p>
            <h1 style="color: #667eea; letter-spacing: 5px;">{otp}</h1>
            <p>This OTP will expire in 10 minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {str(e)}")
        return False
