import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Test printing (safe)
print("SMTP_SERVER:", SMTP_SERVER)
print("SMTP_PORT:", SMTP_PORT)
print("SMTP_EMAIL:", SMTP_EMAIL)
print("SMTP_PASSWORD:", "*" * 8)  # Hides the actual password
