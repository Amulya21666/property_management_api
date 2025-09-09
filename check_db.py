from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Property, Floor, Appliance
from app.utils import get_password_hash  # Import your hash function
from datetime import date

def seed_data():
    db: Session = SessionLocal()

    print("\n🔁 Seeding database...\n")

    # ---- USERS ----
    def get_or_create_user(username, role, plain_password="password"):
        user = db.query(User).filter_by(username=username).first()
        hashed_password = get_password_hash(plain_password)

        if not user:
            user = User(username=username, password_hash=hashed_password, role=role)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created user: {username} ({role}) with password '{plain_password}'")
        else:
            # Update password if changed
            if user.password_hash != hashed_password:
                user.password_hash = hashed_password
                db.commit()
                print(f"🔄 Updated password for {username}")
            else:
                print(f"ℹ️ User already exists: {username} ({role})")
        return user

    # ✅ Now you can create users with custom passwords
    owner1 = get_or_create_user("owner1", "owner", "owner111")
    manager1 = get_or_create_user("manager1", "manager", "managerpass")
    manager2 = get_or_create_user("manager2", "manager", "manager222")

    # ---- PROPERTY 1 ----
    prop1 = db.query(Property).filter_by(name="Greenview Apartments").first()
    if not prop1:
        prop1 = Property(
            name="Greenview Apartments",
            address="MG Road, Indiranagar, Bangalore, Karnataka",
            owner_id=owner1.id
        )
        db.add(prop1)
        db.commit()
        db.refresh(prop1)
        print("✅ Created property: Greenview Apartments")
    else:
        print("ℹ️ Property already exists: Greenview Apartments")

    # ---- FLOORS for prop1 ----
    def get_or_create_floor(number, property_obj):
        floor = db.query(Floor).filter_by(floor_number=number, property_id=property_obj.id).first()
        if not floor:
            floor = Floor(floor_number=number, property_id=property_obj.id)
            db.add(floor)
            db.commit()
            db.refresh(floor)
            print(f"✅ Created floor: {number}")
        else:
            print(f"ℹ️ Floor already exists: {number}")
        return floor

    ground = get_or_create_floor("Ground floor", prop1)
    first = get_or_create_floor("1st floor", prop1)

    # ---- APPLIANCES: Ground floor ----
    appliances_ground = [
        ("TV", "SamsungQ7000", "black", "working", "Living Room", date(2030, 2, 3)),
        ("Washing Machine", "LMSQ11", "silver", "working", "Utility", date(2027, 12, 9)),
        ("TV", "LGTVGround", "black", "working", "Living Room", date(2030, 12, 8)),
        ("Microwave Oven", "IFB-30L-GF", "black", "working", "Kitchen", date(2029, 2, 2)),
        ("Water Purifier", "Bosch-7837-GF", "blue", "working", "Kitchen", date(2028, 2, 1)),
    ]

    for name, model, color, status, location, warranty in appliances_ground:
        exists = db.query(Appliance).filter_by(model=model, floor_id=ground.id).first()
        if not exists:
            db.add(Appliance(
                name=name,
                model=model,
                color=color,
                status=status,
                location=location,
                warranty_expiry=warranty,
                floor_id=ground.id,
                property_id=ground.property_id
            ))
            print(f"✅ Added appliance on Ground floor: {name} ({model})")
        else:
            print(f"ℹ️ Appliance already exists on Ground floor: {model}")

    # ---- APPLIANCES: 1st floor ----
    appliances_first = [
        ("Refrigerator", "SamsungQ7000-F1", "black", "working", "Kitchen", date(2030, 2, 3)),
        ("Refrigerator", "SamsungQ7000-F2", "black", "working", "Kitchen", date(2030, 2, 3)),
        ("Refrigerator", "SamsungQ7000-F3", "black", "working", "Kitchen", date(2030, 2, 3)),
        ("AC", "LG-1.5ton-AC-F1", "white", "under maintenance", "Bedroom", date(2027, 3, 3)),
        ("TV", "LGTVFirst", "black", "working", "Bedroom", date(2026, 5, 8)),
    ]

    for name, model, color, status, location, warranty in appliances_first:
        exists = db.query(Appliance).filter_by(model=model, floor_id=first.id).first()
        if not exists:
            db.add(Appliance(
                name=name,
                model=model,
                color=color,
                status=status,
                location=location,
                warranty_expiry=warranty,
                floor_id=first.id,
                property_id=first.property_id
            ))
            print(f"✅ Added appliance on 1st floor: {name} ({model})")
        else:
            print(f"ℹ️ Appliance already exists on 1st floor: {model}")

    # ---- PROPERTY 2 ----
    prop2 = db.query(Property).filter_by(name="Blue Apartment").first()
    if not prop2:
        prop2 = Property(
            name="Blue Apartment",
            address="15 MG Road, Vijayanagara, Bangalore, Karnataka",
            owner_id=owner1.id
        )
        db.add(prop2)
        db.commit()
        print("✅ Created property: Blue Apartment")
    else:
        print("ℹ️ Property already exists: Blue Apartment")

    db.commit()
    db.close()

    print("\n🎉 Seeding complete!\n")


if __name__ == "__main__":
    seed_data()
