# app/routes/otp_routes.py
from fastapi import APIRouter, Form, Depends
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.utils import send_otp_email, generate_otp
from app.database import get_db
from app.models import User
from app.auth import create_access_token

router = APIRouter()

# ====== Request OTP for forgot password ======
@router.post("/forgot-password")
def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "User not found"}

    otp_code = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    user.otp = otp_code
    user.otp_expiry = otp_expiry
    db.commit()

    send_otp_email(email, otp_code)
    return {"message": "OTP sent to your email"}

# ====== Verify OTP for forgot password ======
@router.post("/verify_otp")
def verify_otp(email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "User not found"}

    if user.otp != otp or datetime.utcnow() > user.otp_expiry:
        return {"error": "Invalid or expired OTP"}

    # Clear OTP after verification
    user.otp = None
    user.otp_expiry = None
    db.commit()

    return {"message": "OTP verified. You can now reset your password."}

# ====== Request OTP for login ======
@router.post("/login_request_otp")
def login_request_otp(email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_verified == True).first()
    if not user:
        return {"error": "User not found or not verified"}

    otp_code = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    user.otp = otp_code
    user.otp_expiry = otp_expiry
    db.commit()

    send_otp_email(email, otp_code)
    return {"message": "OTP sent to your email"}

# ====== Verify OTP for login ======
@router.post("/login_verify_otp")
def login_verify_otp(email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_verified == True).first()
    if not user:
        return {"error": "User not found or not verified"}

    if user.otp != otp or datetime.utcnow() > user.otp_expiry:
        return {"error": "Invalid or expired OTP"}

    # Clear OTP after successful login
    user.otp = None
    user.otp_expiry = None
    db.commit()

    # Generate JWT access token
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}
