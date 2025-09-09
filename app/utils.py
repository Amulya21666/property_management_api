# app/utils.py
import os
import random
import requests
from passlib.context import CryptContext
from dotenv import load_dotenv
from datetime import datetime
from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

# --------------------------
# Load environment variables
# --------------------------
load_dotenv()
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")  # Must match your verified sender email

# --------------------------
# Password hashing
# --------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plain password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

# --------------------------
# OTP generation & verification
# --------------------------
def generate_otp(length: int = 6) -> str:
    if length < 4:
        length = 4
    return str(random.randint(10**(length-1), 10**length - 1))

def send_otp_email(to_email: str, otp: str) -> bool:
    """Send OTP email using Brevo API"""
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }
        payload = {
            "sender": {"name": "Your App", "email": SENDER_EMAIL},
            "to": [{"email": to_email}],
            "subject": "Your OTP Code",
            "htmlContent": f"<html><body><h3>Your OTP is: {otp}</h3></body></html>"
        }
        response = requests.post(url, headers=headers, json=payload)
        print(f"Brevo API Response [{response.status_code}]: {response.text}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Exception while sending email: {e}")
        return False

def verify_otp(user, input_otp: str) -> bool:
    """Verify if user's OTP is correct and not expired"""
    if not user.otp or not user.otp_expiry:
        return False
    if user.otp != input_otp:
        return False
    if user.otp_expiry < datetime.utcnow():
        return False
    return True

# --------------------------
# Tenant activation email
# --------------------------
def send_activation_email(to_email: str, token: str) -> bool:
    """Send tenant account activation email"""
    try:
        activation_link = f"http://localhost:8000/activate/{token}"  # Change domain in production
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }
        payload = {
            "sender": {"name": "Your App", "email": SENDER_EMAIL},
            "to": [{"email": to_email}],
            "subject": "Activate Your Tenant Account",
            "htmlContent": f"""
            <html><body>
                <p>Hello,</p>
                <p>Please activate your account by clicking the link below:</p>
                <a href="{activation_link}">Activate Account</a>
                <p>Thank you!</p>
            </body></html>
            """
        }
        response = requests.post(url, headers=headers, json=payload)
        print(f"Brevo API Response [{response.status_code}]: {response.text}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Exception while sending activation email: {e}")
        return False

# --------------------------
# Get current user (session-based)
# --------------------------
def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
