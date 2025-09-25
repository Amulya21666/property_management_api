from datetime import datetime, date, timedelta
import uuid
from fastapi import HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi import UploadFile


from app.models import (
    Property, User, Appliance, Floor, ActivityLog,
    PendingTenant, ApplianceImage
)
from app.schemas import PropertyCreate
from app.utils import hash_password, send_otp_email  # ✅ Import from utils



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --------------------------
# PROPERTY MANAGEMENT
# --------------------------
def create_property(db: Session, property: PropertyCreate, user_id: int):
    db_property = Property(
        name=property.name,
        address=property.address,
        property_type=property.property_type,
        owner_id=user_id
    )
    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    return db_property

def get_properties_by_owner(db: Session, owner_id: int):
    return db.query(Property).filter(Property.owner_id == owner_id).all()

def get_property_by_id(db: Session, property_id: int):
    return db.query(Property).filter(Property.id == property_id).first()

def update_property(db: Session, property_id: int, name: str, address: str, property_type: str):
    property_obj = get_property_by_id(db, property_id)
    if property_obj:
        property_obj.name = name
        property_obj.address = address
        property_obj.property_type = property_type
        db.commit()
        db.refresh(property_obj)
    return property_obj

# --------------------------
# MANAGER ASSIGNMENT
# --------------------------
def get_all_managers(db: Session):
    return db.query(User).filter(User.role == "manager").all()

def assign_property_to_manager(db: Session, property_id: int, manager_id: int):
    property_obj = get_property_by_id(db, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    manager = db.query(User).filter(User.id == manager_id, User.role == "manager").first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")

    property_obj.manager_id = manager.id
    db.commit()
    db.refresh(property_obj)
    return property_obj

def get_properties_assigned_to_manager(db: Session, manager_id: int):
    return db.query(Property).filter(Property.manager_id == manager_id).all()

# --------------------------
# USER MANAGEMENT
# --------------------------
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


from app.crud import get_user_by_email  # make sure this exists


def create_user(db: Session, username: str, email: str, password: str, role: str, **kwargs):
    """
    Create a user: OTP for owner/manager, no OTP for tenant.
    """
    # Check if email already exists
    if get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password
    hashed_password = hash_password(password)

    # Remove conflicting keys from kwargs to avoid "multiple values" error
    for key in ["otp", "otp_expiry", "is_verified"]:
        if key in kwargs:
            kwargs.pop(key)

    if role.lower() in ["owner", "manager"]:
        # Generate OTP for owner/manager
        otp = str(uuid.uuid4())[:6]  # 6-character OTP
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)

        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role=role.lower(),
            otp=otp,
            otp_expiry=otp_expiry,
            is_verified=False,  # OTP pending
            **kwargs
        )

        # Send OTP email
        send_otp_email(to_email=email, otp=otp)

    else:
        # Tenant registration (no OTP)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            role=role.lower(),
            is_verified=True,  # already verified
            **kwargs
        )

    # Save to DB
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# --------------------------
# APPLIANCE MANAGEMENT
# --------------------------
def create_appliance(
    db: Session, user_id: int, name: str, model: str, color: str,
    status: str, warranty_expiry: date, property_id: int, floor_id: int,
    location: str, front_image: str = None, detail_image: str = None
):
    appliance = Appliance(
        user_id=user_id,
        name=name,
        model=model,
        color=color,
        status=status,
        warranty_expiry=warranty_expiry,
        property_id=property_id,
        floor_id=floor_id,
        location=location,
        front_image=front_image,
        detail_image=detail_image
    )
    db.add(appliance)
    db.commit()
    db.refresh(appliance)
    log_activity(db, user_id=user_id, action=f"Added appliance '{name}' to property {property_id}, floor {floor_id}")
    return appliance

def get_appliance_by_id(db: Session, appliance_id: int):
    return db.query(Appliance).filter(Appliance.id == appliance_id).first()

def update_appliance(db: Session, appliance, name: str, model: str, color: str,
                     status: str, warranty_expiry, location: str):
    appliance.name = name
    appliance.model = model
    appliance.color = color
    appliance.status = status
    appliance.warranty_expiry = warranty_expiry
    appliance.location = location
    db.commit()
    db.refresh(appliance)
    return appliance

def get_appliances_by_property(db: Session, property_id: int):
    return db.query(Appliance).filter(Appliance.property_id == property_id).all()

def get_appliances_grouped_by_property(db: Session, owner_id: int):
    properties = get_properties_by_owner(db, owner_id)
    return {prop.id: get_appliances_by_property(db, prop.id) for prop in properties}

def add_appliance_image(db: Session, appliance_id: int, image_path: str):
    img = ApplianceImage(appliance_id=appliance_id, image_path=image_path)
    db.add(img)
    db.commit()
    db.refresh(img)
    return img

# --------------------------
# FLOOR MANAGEMENT
# --------------------------
def create_floor(db: Session, floor_number: str, property_id: int):
    floor = Floor(floor_number=floor_number, property_id=property_id)
    db.add(floor)
    db.commit()
    db.refresh(floor)
    return floor

def get_floors_by_property(db: Session, property_id: int):
    return db.query(Floor).filter(Floor.property_id == property_id).all()

def floor_exists(db: Session, property_id: int, floor_number: str):
    return db.query(Floor).filter_by(property_id=property_id, floor_number=floor_number).first() is not None

def get_floors_with_appliances(db: Session, property_id: int):
    floors = get_floors_by_property(db, property_id)
    return [{"floor_number": f.floor_number, "appliances": f.appliances} for f in floors]

# --------------------------
# ACTIVITY LOG
# --------------------------
def log_activity(db: Session, user_id: int, action: str):
    log = ActivityLog(user_id=user_id, action=action)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_recent_logs(db: Session, limit: int = 10):
    return db.query(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(limit).all()

# --------------------------
# TENANT MANAGEMENT
# --------------------------
def get_all_tenants(db: Session):
    return db.query(User).filter(User.role == "tenant", User.property_id == None).all()

def create_pending_tenant(db: Session, name: str, email: str, property_id: int = None,
                          flat_no: str = None, room_no: str = None):
    token = str(uuid.uuid4())
    tenant = PendingTenant(
        name=name,
        email=email,
        property_id=property_id,
        flat_no=flat_no,
        room_no=room_no,
        activation_token=token
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

def activate_tenant(db: Session, pending_tenant, password: str, name: str, phone: str):
    """Convert PendingTenant -> User (tenant) without OTP."""
    hashed_password = hash_password(password)
    tenant_user = User(
        username=name,
        name=name,
        email=pending_tenant.email,
        phone=phone,
        password_hash=hashed_password,
        role="tenant",
        property_id=pending_tenant.property_id,
        flat_no=pending_tenant.flat_no,
        room_no=pending_tenant.room_no,
        is_verified=True
    )
    db.add(tenant_user)
    pending_tenant.is_activated = True
    pending_tenant.activation_token = None
    db.commit()
    db.refresh(tenant_user)
    return tenant_user

# --------------------------
# TENANT ASSIGNMENT
# --------------------------
def get_unassigned_tenants(db: Session):
    return db.query(User).filter(User.role == "tenant", User.property_id == None).all()

def assign_tenant_to_property(db: Session, tenant_id: int, property_id: int,
                              flat_no: str = None, room_no: str = None):
    tenant = db.query(User).filter(User.id == tenant_id, User.role == "tenant").first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    property_obj = get_property_by_id(db, property_id)
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    tenant.property_id = property_obj.id
    tenant.flat_no = flat_no
    tenant.room_no = room_no
    db.commit()
    db.refresh(tenant)
    return tenant

# --------------------------
# PASSWORD / UTILS
# --------------------------

def get_tenant_property(db, tenant_id: int):
    tenant = db.query(User).filter(User.id == tenant_id).first()
    if not tenant or not tenant.property_id:
        return None
    return db.query(Property).filter(Property.id == tenant.property_id).first()

from app.utils import save_file

import os
import shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.models import Appliance

# Helper function to save uploaded files
def save_uploaded_file(file: UploadFile, prefix: str):
    if file and file.filename:
        filename = f"{prefix}_{file.filename}".replace(" ", "_")
        save_dir = "app/static/images"
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        file.file.close()
        return filename
    return None

# Function to create appliance with images
def create_appliance_with_images(
    db: Session,
    user_id: int,
    name: str,
    model: str,
    color: str,
    status: str,
    warranty_expiry,
    property_id: int,
    floor_id: int,
    location: str,
    front_file: UploadFile = None,
    detail_file: UploadFile = None
):
    # Save images and get filenames
    front_filename = save_uploaded_file(front_file, "front")
    detail_filename = save_uploaded_file(detail_file, "detail")

    # Create appliance record
    new_appliance = Appliance(
        user_id=user_id,
        name=name,
        model=model,
        color=color,
        status=status,
        warranty_expiry=warranty_expiry,
        property_id=property_id,
        floor_id=floor_id,
        location=location,
        front_image=front_filename,
        detail_image=detail_filename
    )

    db.add(new_appliance)
    db.commit()
    db.refresh(new_appliance)
    return new_appliance
