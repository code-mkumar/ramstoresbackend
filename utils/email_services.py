import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------------------------------------------------
#  Gmail SMTP Configuration
# ---------------------------------------------------------
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "codehunting2k24@gmail.com"   # your email
EMAIL_PASSWORD = "uwhk simq uiiy donj"      # your Gmail app password


# ---------------------------------------------------------
#  HTML Templates
# ---------------------------------------------------------
OTP_HTML = """
<div style="font-family: Arial, sans-serif; background:#f7f7f7; padding:20px;">
  <div style="
    max-width:600px;
    margin:auto;
    background:white;
    padding:25px;
    border-radius:15px;
    box-shadow:0 4px 12px rgba(0,0,0,0.1);
  ">

    <h2 style="color:#2d3748; text-align:center;">Ram Stores – Password Reset</h2>

    <p style="color:#4a5568; font-size:16px;">
      Hello <b>{user_name}</b>,
    </p>

    <p style="color:#4a5568; font-size:16px;">
      You requested to reset your password. Use the OTP below:
    </p>

    <div style="
      background:#edf2f7;
      padding:15px;
      border-radius:10px;
      text-align:center;
      font-size:24px;
      font-weight:bold;
      letter-spacing:5px;
      color:#2d3748;
      margin:20px 0;
    ">
      {otp}
    </div>

    <p style="color:#4a5568; font-size:15px;">
      This OTP is valid for <b>10 minutes</b>.
    </p>

    <p style="margin-top:20px; color:#4a5568;">
      If you didn't request this, please ignore this email.
    </p>

    <br>
    <p style="color:#667eea; font-weight:bold; text-align:center;">
      Ram Stores
    </p>

  </div>
</div>
"""


WELCOME_HTML = """
<div style="font-family: Arial, sans-serif; background:#f7f7f7; padding:20px;">
  <div style="
    max-width:600px;
    margin:auto;
    background:white;
    padding:25px;
    border-radius:15px;
    box-shadow:0 4px 12px rgba(0,0,0,0.1);
  ">

    <h2 style="color:#2d3748; text-align:center;">Welcome to Ram Stores!</h2>

    <p style="color:#4a5568; font-size:16px;">
      Hello <b>{user_name}</b>,
    </p>

    <p style="color:#4a5568; font-size:16px;">
      Your account has been successfully created.  
      We are excited to have you as part of our family!
    </p>

    <p style="color:#4a5568; font-size:16px; text-align:center; margin-top:20px;">
      Enjoy fresh groceries, daily essentials, premium categories and more.
    </p>

    <div style="text-align:center; margin-top:25px;">
      <a href="#" style="
        background:linear-gradient(135deg,#667eea,#764ba2);
        color:white;
        padding:12px 25px;
        border-radius:10px;
        text-decoration:none;
        font-size:16px;
      ">
        Visit Store
      </a>
    </div>

    <br>
    <p style="color:#667eea; font-weight:bold; text-align:center;">
      Ram Stores
    </p>

  </div>
</div>
"""


ORDER_CONFIRM_HTML = """
<div style="font-family: Arial, sans-serif; background:#f7f7f7; padding:20px;">
  <div style="
    max-width:600px;
    margin:auto;
    background:white;
    padding:25px;
    border-radius:15px;
    box-shadow:0 4px 12px rgba(0,0,0,0.1);
  ">

    <h2 style="color:#2d3748; text-align:center;">Your Order is Confirmed!</h2>

    <p style="color:#4a5568; font-size:16px;">
      Hello <b>{user_name}</b>,
    </p>

    <p style="color:#4a5568; font-size:16px;">
      Thank you for shopping with Ram Stores.
      Your order details are below:
    </p>

    <div style="
      background:#edf2f7;
      padding:15px;
      border-radius:10px;
      margin-top:20px;
    ">
      <p style="font-size:16px; color:#2d3748;">
        <b>Order Number:</b> {order_number}
      </p>
      <p style="font-size:16px; color:#2d3748;">
        <b>Total Amount:</b> ₹{total_amount}
      </p>
    </div>

    <p style="color:#4a5568; font-size:15px; margin-top:20px;">
      We will notify you once your order is shipped.
    </p>

    <br>
    <p style="color:#667eea; font-weight:bold; text-align:center;">
      Ram Stores
    </p>

  </div>
</div>
"""


# ---------------------------------------------------------
#  Base Email Sender
# ---------------------------------------------------------
# ---------------------------------------------------------
#  Base Email Sender with detailed error logging
# ---------------------------------------------------------
def send_email(to_email, subject, html_content):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True, "Email sent successfully!"

    except Exception as e:
        # Return the exception type and message
        return False, f"{type(e).__name__}: {str(e)}"



# ---------------------------------------------------------
#  OTP Email Function
# ---------------------------------------------------------
def send_otp_email(to_email, otp, user_name="User"):
    html = OTP_HTML.format(user_name=user_name, otp=otp)
    return send_email(to_email, "Password Reset OTP - Ram Stores", html)


# ---------------------------------------------------------
#  Welcome Email Function
# ---------------------------------------------------------
def send_welcome_email(to_email, user_name):
    html = WELCOME_HTML.format(user_name=user_name)
    return send_email(to_email, "Welcome to Ram Stores!", html)


# ---------------------------------------------------------
#  Order Confirmation Email Function
# ---------------------------------------------------------
def send_order_confirmation_email(*, to_email, user_name, order_number, total_amount):
    html = ORDER_CONFIRM_HTML.format(
        user_name=user_name,
        order_number=order_number,
        total_amount=total_amount
    )
    return send_email(to_email, f"Order Confirmation #{order_number}", html)
