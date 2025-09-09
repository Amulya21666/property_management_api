from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models import User
from app.database import get_db
from app import crud  # Make sure crud has get_user_by_id


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Optional: attach any session info to user object
    user.is_admin = request.session.get("is_admin", False)
    return user
from datetime import datetime, timedelta
import jwt

SECRET_KEY = "your-secret-key"  # Change this to a strong secret and keep it private
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
