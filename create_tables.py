# create_db.py
from app.database import Base, engine
from app import models  # this should import all your models

Base.metadata.create_all(bind=engine)
print("✅ Database and tables created successfully.")
