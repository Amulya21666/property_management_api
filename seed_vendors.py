from app.database import SessionLocal
from app.models import Vendor

def seed_vendors():
    db = SessionLocal()

    if db.query(Vendor).count() > 0:
        print("Vendors already seeded")
        return

    # Add both service_type and category
    electrician = Vendor(
        name="Ramesh Electrician",
        service_type="Electrical Repair",  # <- must provide this
        contact="9876543210",
        category="Electrician"
    )

    plumber = Vendor(
        name="Suresh Plumber",
        service_type="Plumbing",  # <- must provide this
        contact="9123456780",
        category="Plumber"
    )

    db.add_all([electrician, plumber])
    db.commit()
    db.close()
    print("Vendors seeded successfully")

if __name__ == "__main__":
    seed_vendors()
