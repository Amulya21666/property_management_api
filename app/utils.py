# app/utils.py
import os
import random
import requests
from passlib.context import CryptContext
from datetime import datetime
from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

# ===================================================================
# CONSTANTS & ENVIRONMENT VARIABLES
# ===================================================================

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# Use .env if available, fallback to default — safer than forcing overwrite
HOSTED_URL = os.getenv("HOSTED_URL", "https://property-management-api-e08h.onrender.com")

# ===================================================================
# PASSWORD HASHING
# ===================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ===================================================================
# OTP GENERATION & VERIFICATION
# ===================================================================

def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP."""
    length = max(4, length)
    return str(random.randint(10**(length-1), 10**length - 1))


def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Sends OTP email using Brevo API.
    Returns True on success, False on failure.
    """
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        # Beautiful email template
        html_body = f"""
        <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2 style="color:#2b6cb0;">Your OTP Code</h2>
            <p style="font-size: 18px;">Your One-Time Password is:</p>
            <h1 style="font-size: 32px; color:#2b6cb0;">{otp}</h1>
            <p>This OTP is valid for <b>10 minutes</b>.</p>
            <br>
            <p>If you did not request this code, please ignore this email.</p>
        </body>
        </html>
        """

        payload = {
            "sender": {"name": "Property Management", "email": SENDER_EMAIL},
            "to": [{"email": to_email}],
            "subject": "Your OTP Code",
            "htmlContent": html_body
        }

        response = requests.post(url, headers=headers, json=payload)

        # Remove OTP from logs — only status
        print(f"Brevo OTP Email Status: {response.status_code}")

        return response.status_code in [200, 201]

    except Exception as e:
        print(f"❌ Error sending OTP email: {e}")
        return False


def verify_otp(user, input_otp: str) -> bool:
    """Validates OTP & expiry."""
    if not user.otp or not user.otp_expiry:
        return False
    if user.otp != input_otp:
        return False
    if user.otp_expiry < datetime.utcnow():
        return False
    return True

# ===================================================================
# GET CURRENT USER (SESSION BASED)
# ===================================================================

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# ===================================================================
# SEND ACTIVATION EMAIL FOR TENANTS
# ===================================================================

def send_activation_email(to_email: str, token: str):
    """
    Sends tenant activation email.
    """
    activation_link = f"{HOSTED_URL}/activate/{token}"

    subject = "Activate Your Tenant Account"

    html_body = f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h2 style="color:#2b6cb0;">Activate Your Tenant Account</h2>

        <p>You have been invited as a tenant. Click the link below to activate your account:</p>

        <a href="{activation_link}" 
           style="background:#2b6cb0; color:white; padding:10px 20px; border-radius:5px; text-decoration:none;">
            Activate Account
        </a>

        <p style="margin-top: 20px;">
            If you didn’t expect this email, you can safely ignore it.
        </p>

        <br>
        <p>Thanks,<br>Property Management Team</p>
    </body>
    </html>
    """

    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }

        payload = {
            "sender": {"name": "Property Management", "email": SENDER_EMAIL},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_body
        }

        response = requests.post(url, headers=headers, json=payload)

        # Only log status, avoid showing sensitive info
        print(f"Brevo Activation Email Status: {response.status_code}")

        return response.status_code in [200, 201]

    except Exception as e:
        print(f"❌ Error sending activation email: {e}")
        return False
