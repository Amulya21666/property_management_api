from pydantic import BaseModel, ConfigDict
from typing import Optional

# ======================
# 🔐 Auth Schemas
# ======================

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginSchema(BaseModel):
    email: str
    password: str

# ======================
# 👤 User Schemas
# ======================

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserOut(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)  # Pydantic v2

# ======================
# 🏠 Property Schemas
# ======================

class PropertyBase(BaseModel):
    name: str
    address: str

class PropertyCreate(PropertyBase):  # ✅ Remove user_id here
    pass

class PropertyOut(PropertyBase):
    id: int
    user_id: Optional[int]

    class Config:
        from_attributes = True



