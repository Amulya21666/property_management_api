import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_URL = os.getenv("APP_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

# Test printing (safe)
print("BREVO_API_KEY:", "*" * 8)  # hide actual key
print("SENDER_EMAIL:", SENDER_EMAIL)
print("APP_URL:", APP_URL)
print("DATABASE_URL:", DATABASE_URL[:40] + "...")
