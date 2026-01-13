import os
import sys
import time
import json
import smtplib
import zipfile
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_agent
from src.infra.sqlite_db import SQLiteInvoiceRepository
from src.models import Invoice, InvoiceStatus

load_dotenv()

SENDER_EMAIL = os.getenv("TEST_VENDOR_EMAIL")
SENDER_APP_PASSWORD = os.getenv("TEST_VENDOR_PASSWORD")
RECEIVER_EMAIL = os.getenv("SYSTEM_BOT_EMAIL")
TEST_FILES_DIR = "tests/golden_pdfs"
CONFIG_FILE = "tests/test_config.json" # <--- Load from here

if not all([SENDER_EMAIL, SENDER_APP_PASSWORD, RECEIVER_EMAIL]):
    print("❌ Error: Missing credentials in .env.")
    sys.exit(1)

# Load Test Data from JSON
if not os.path.exists(CONFIG_FILE):
    print("❌ Error: test_config.json not found. Run 'tests/prepare_large_test.py' first.")
    sys.exit(1)

with open(CONFIG_FILE, 'r') as f:
    TEST_DATA = json.load(f)

def setup_clean_db():
    print(f"1️⃣  Resetting Database with {len(TEST_DATA)} records...")
    if os.path.exists("invoices.db"):
        os.remove("invoices.db")
    
    repo = SQLiteInvoiceRepository()
    
    for filename, invoice_num in TEST_DATA.items():
        inv = Invoice(
            id=None,
            invoice_number=invoice_num,
            vendor_email=SENDER_EMAIL,
            amount=100.00,
            status=InvoiceStatus.PENDING,
            gstin="TEST_GSTIN",
            hotel_name="TEST_HOTEL",
            workspace="TEST_CLIENT"
        )
        repo.add_invoice(inv)
    print("   ✅ Database seeded.")

def create_zip_payload():
    zip_name = "e2e_large_test.zip"
    print("2️⃣  Creating Large ZIP Payload...")
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in TEST_DATA.keys():
            file_path = os.path.join(TEST_FILES_DIR, filename)
            if os.path.exists(file_path):
                zf.write(file_path, arcname=filename)
    
    size_mb = os.path.getsize(zip_name) / (1024 * 1024)
    print(f"   📦 ZIP Created: {size_mb:.2f} MB")
    
    if size_mb > 24:
        print("   ⚠️  WARNING: ZIP is larger than 25MB. Gmail might reject it.")
    
    return zip_name

def send_test_email(zip_filename):
    print("3️⃣  Sending Email...")
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"Stress Test: {len(TEST_DATA)} Invoices"
    msg.attach(MIMEText("Stress test payload attached."))

    with open(zip_filename, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={zip_filename}")
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("   ✅ Email sent!")
    except Exception as e:
        print(f"   ❌ Failed to send email: {e}")
        sys.exit(1)

def run_system_logic():
    print("4️⃣  Triggering Agent Logic...")
    # Wait longer for large file upload/download propagation
    print("   ⏳ Waiting 45 seconds for heavy payload delivery...")
    time.sleep(45) 
    
    try:
        agent = get_agent()
        report = agent.run_reconciliation_cycle()
        print(f"   ✅ Agent cycle finished. Threads: {len(report)}")
    except Exception as e:
        print(f"   ❌ Agent crashed: {e}")

def calculate_results():
    print("5️⃣  Verifying Results...")
    conn = sqlite3.connect("invoices.db")
    c = conn.cursor()
    c.execute("SELECT invoice_number, status FROM invoices")
    rows = c.fetchall()
    conn.close()

    total = len(rows)
    received = 0
    
    # Simple count
    for row in rows:
        if row[1] == "RECEIVED":
            received += 1

    accuracy = (received / total) * 100 if total > 0 else 0
    
    print("\n" + "="*30)
    print(f"🎯 STRESS TEST ACCURACY: {accuracy:.2f}%")
    print(f"   Matched: {received} / {total}")
    print("="*30)

if __name__ == "__main__":
    zip_file = "e2e_large_test.zip"
    try:
        setup_clean_db()
        zip_path = create_zip_payload()
        send_test_email(zip_path)
        run_system_logic()
        calculate_results()
    finally:
        if os.path.exists(zip_file):
            os.remove(zip_file)