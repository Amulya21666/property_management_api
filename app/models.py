import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime,
    Boolean, Date, Text, UniqueConstraint, Float, Enum
)
from sqlalchemy.orm import relationship
from app.database import Base

# ----------------------
# Enums
# ----------------------
class IssueStatus(str, PyEnum):
    pending = "pending"
    assigned = "assigned"
    repaired = "repaired"
    in_progress = "in_progress"
    rejected = "rejected"
    paid = "paid"


class WorkerType(str, PyEnum):
    electrician = "Electrician"
    plumber = "Plumber"
    carpenter = "Carpenter"
    other = "Other"

class QueryStatus(str, PyEnum):
    pending = "pending"
    resolved = "resolved"

# ----------------------
# User model
# ----------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    service_type = Column(String, nullable=True)

    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(50), default="tenant")  # owner / manager / tenant / vendor

    otp = Column(String(20), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False)

    # Tenant assignment
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)
    flat_no = Column(String(50), nullable=True)
    room_no = Column(String(50), nullable=True)

    # Relationships
    properties_as_tenant = relationship("Property", back_populates="tenants", foreign_keys=[property_id])
    floor = relationship("Floor", foreign_keys=[floor_id])
    appliances = relationship("Appliance", back_populates="user", cascade="all, delete-orphan")
    properties_owned = relationship("Property", back_populates="owner", foreign_keys="Property.owner_id")
    properties_managed = relationship("Property", back_populates="manager", foreign_keys="Property.manager_id")
    activity_logs = relationship("ActivityLog", back_populates="user_obj", cascade="all, delete-orphan")

    # Issues reported by tenant
    issues_reported = relationship("Issue", back_populates="tenant", cascade="all, delete-orphan", foreign_keys="Issue.tenant_id")

    # Issues assigned as vendor
    issues_assigned = relationship("Issue", back_populates="vendor", cascade="all, delete-orphan", foreign_keys="Issue.vendor_id")

    # Queries raised by tenant
    tenant_queries = relationship("TenantQuery", back_populates="reported_by", cascade="all, delete-orphan")

# ----------------------
# Property model
# ----------------------
class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    property_type = Column(String(100), nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"))
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="properties_owned", foreign_keys=[owner_id])
    manager = relationship("User", back_populates="properties_managed", foreign_keys=[manager_id])
    tenants = relationship("User", back_populates="properties_as_tenant", foreign_keys=[User.property_id])

    appliances = relationship("Appliance", back_populates="property", cascade="all, delete-orphan")
    floors = relationship("Floor", back_populates="property", cascade="all, delete-orphan")
    tenant_queries = relationship("TenantQuery", back_populates="property", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="property", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('name', 'address', name='uix_name_address'),)

# ----------------------
# Floor model
# ----------------------
class Floor(Base):
    __tablename__ = "floors"

    id = Column(Integer, primary_key=True, index=True)
    floor_number = Column(String(50), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)

    floor_plan = Column(String(255), nullable=True)
    extracted_details = Column(Text, nullable=True)

    property = relationship("Property", back_populates="floors")
    appliances = relationship("Appliance", back_populates="floor", cascade="all, delete-orphan")

# ----------------------
# Appliance model
# ----------------------
class Appliance(Base):
    __tablename__ = "appliances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)

    name = Column(String(100), nullable=False)
    model = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    warranty_expiry = Column(Date, nullable=True)
    location = Column(String(255), nullable=True)

    front_image = Column(String(255), nullable=True)
    detail_image = Column(String(255), nullable=True)

    user = relationship("User", back_populates="appliances")
    property = relationship("Property", back_populates="appliances")
    floor = relationship("Floor", back_populates="appliances")
    images = relationship("ApplianceImage", back_populates="appliance", cascade="all, delete-orphan")
    queries = relationship("TenantQuery", back_populates="appliance", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="appliance")

# ----------------------
# ApplianceImage model
# ----------------------
class ApplianceImage(Base):
    __tablename__ = "appliance_images"

    id = Column(Integer, primary_key=True, index=True)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=False)
    image_path = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    appliance = relationship("Appliance", back_populates="images")

# ----------------------
# ActivityLog model
# ----------------------
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user_obj = relationship("User", back_populates="activity_logs")

# ----------------------
# Issue model
# ----------------------
class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    status = Column(Enum(IssueStatus), default=IssueStatus.pending, nullable=False)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    bill_amount = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    tenant = relationship("User", back_populates="issues_reported", foreign_keys=[tenant_id])
    property = relationship("Property", back_populates="issues", foreign_keys=[property_id])
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    vendor = relationship("User", back_populates="issues_assigned", foreign_keys=[vendor_id])
    appliance = relationship("Appliance", back_populates="issues", foreign_keys=[appliance_id])

# ----------------------
# TenantQuery model
# ----------------------
class TenantQuery(Base):
    __tablename__ = "tenant_queries"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    status = Column(Enum(QueryStatus), default=QueryStatus.pending)
    reported_by_id = Column(Integer, ForeignKey("users.id"))
    property_id = Column(Integer, ForeignKey("properties.id"))
    appliance_id = Column(Integer, ForeignKey("appliances.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reported_by = relationship("User", back_populates="tenant_queries")
    property = relationship("Property", back_populates="tenant_queries")
    appliance = relationship("Appliance", back_populates="queries")

# ----------------------
# PendingTenant model
# ----------------------
class PendingTenant(Base):
    __tablename__ = "pending_tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    flat_no = Column(String(50), nullable=True)
    room_no = Column(String(50), nullable=True)
    activation_token = Column(String(255), unique=True, default=lambda: str(uuid.uuid4()))
    is_activated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)
    floor_id = Column(Integer, ForeignKey("floors.id"), nullable=True)

    property = relationship("Property")
    floor = relationship("Floor")
