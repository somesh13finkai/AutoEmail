import os
import smtplib
from pathlib import Path
from dotenv import load_dotenv

# --- CONFIGURATION CHANGE ---
# Get the path to the root folder (One level up from 'dev_tools')
# __file__ is this script. parent is 'dev_tools'. parent.parent is 'AutoEmail' (root).
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / '.env'

# Load the specific .env file from root
print(f"📂 Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path)

# --- STANDARD CHECK LOGIC ---
email = os.getenv("TEST_VENDOR_EMAIL")
password = os.getenv("TEST_VENDOR_PASSWORD")

print(f"📧 Attempting login for: {email}")
# Mask password for display
masked_pass = "*" * len(password) if password else "None"
print(f"🔑 Password used: {masked_pass} (Length: {len(password) if password else 0})")

if not password or len(password) != 16:
    print("❌ ERROR: App Password must be exactly 16 characters.")
    print("   Make sure there are no spaces and it is not your normal login password.")
    exit()

try:
    print("⏳ Connecting to Gmail SMTP...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email, password)
    print("✅ SUCCESS! Login worked. Your credentials are correct.")
    server.quit()
except Exception as e:
    print("\n❌ LOGIN FAILED.")
    print(f"Error Message: {e}")