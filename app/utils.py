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
import shutil
from fastapi import UploadFile


# --------------------------
# Constants for email sending
# --------------------------
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# Force hosted URL (ignore .env)
HOSTED_URL = "https://property-management-api-e08h.onrender.com"

# --------------------------
# Password hashing
# --------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --------------------------
# OTP generation & verification
# --------------------------
def generate_otp(length: int = 6) -> str:
    if length < 4:
        length = 4
    return str(random.randint(10**(length-1), 10**length - 1))

def send_otp_email(to_email: str, otp: str) -> bool:
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
    if not user.otp or not user.otp_expiry:
        return False
    if user.otp != input_otp:
        return False
    if user.otp_expiry < datetime.utcnow():
        return False
    return True

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

# --------------------------
# Send activation email
# --------------------------
def send_activation_email(to_email: str, token: str):
    activation_link = f"{HOSTED_URL}/activate/{token}"

    subject = "Activate Your Tenant Account"
    body = f"""
    Hello,

    You have been invited as a tenant. Click the link below to activate your account:

    {activation_link}

    If you didn't expect this email, you can ignore it.

    Thanks,
    Property Management Team
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
            "htmlContent": f"<html><body><p>{body.replace(chr(10), '<br>')}</p></body></html>"
        }
        response = requests.post(url, headers=headers, json=payload)
        print(f"Brevo API Response [{response.status_code}]: {response.text}")
        print(f"✅ Activation link sent: {activation_link}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Exception while sending activation email: {e}")
        return False

# --------------------------
# FILE UPLOAD / IMAGE SAVING
# --------------------------
UPLOADS_DIR = "app/static/images"
os.makedirs(UPLOADS_DIR, exist_ok=True)

def save_file(upload_file: UploadFile, name: str, suffix: str) -> str | None:
    """
    Save an uploaded file to static/images folder.
    Returns the saved filename or None if no file provided.
    """
    if upload_file and upload_file.filename:
        safe_filename = f"{name}_{suffix}_{upload_file.filename}".replace(" ", "_")
        file_path = os.path.join(UPLOADS_DIR, safe_filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)
        upload_file.file.close()
        return safe_filename
    return None
