from app.database import Base, engine
from app import models  # 👈 this is important so it knows your tables

# Create the database and tables
Base.metadata.create_all(bind=engine)

print("✅ test.db created successfully.")
