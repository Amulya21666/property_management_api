from app.database import SessionLocal
from app.models import User
from werkzeug.security import generate_password_hash

def seed_users():
    db = SessionLocal()

    # Check if users already exist
    existing_user = db.query(User).filter(User.username == "user1").first()
    if existing_user:
        print("Users already seeded.")
        return

    # Create users
    user1 = User(username="user1", password_hash=generate_password_hash("user1password"))
    user2 = User(username="user2", password_hash=generate_password_hash("user2password"))
    user3 = User(username="user3", password_hash=generate_password_hash("user3password"))
    user4 = User(username="user4", password_hash=generate_password_hash("user4password"))

    db.add_all([user1, user2, user3, user4])
    db.commit()
    db.close()

    print("✅ Users user1, user2, user3 and user4 created.")

if __name__ == "__main__":
    seed_users()
