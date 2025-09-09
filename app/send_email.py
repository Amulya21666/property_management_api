from config import SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Hello, this is a test email!")
msg['Subject'] = "Test Email"
msg['From'] = SMTP_EMAIL
msg['To'] = "recipient@example.com"

with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    server.starttls()
    server.login(SMTP_EMAIL, SMTP_PASSWORD)
    server.send_message(msg)

print("Email sent successfully!")
