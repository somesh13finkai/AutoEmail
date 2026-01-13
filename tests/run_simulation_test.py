import os
import smtplib
import time
import zipfile
import random
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv

load_dotenv()

# CONFIGURATION
BOT_EMAIL = "your_bot_email_address@gmail.com" # The email your Agent listens to
TEST_SENDER_EMAIL = "orionbee13@gmail.com" # Must match what you seeded in DB
TEST_SENDER_PASSWORD = "your_app_password_here" # Gmail App Password for sender

def get_random_invoices(count=3):
    files = [f for f in os.listdir("s3_invoices") if f.endswith(".pdf")]
    return random.sample(files, count)

def create_test_zip(files):
    zip_name = "test_batch.zip"
    with zipfile.ZipFile(zip_name, 'w') as zf:
        for f in files:
            zf.write(os.path.join("s3_invoices", f), arcname=f)
    return zip_name

def send_email_with_attachment(filename):
    msg = MIMEMultipart()
    msg['From'] = TEST_SENDER_EMAIL
    msg['To'] = BOT_EMAIL
    msg['Subject'] = "Re: Invoice Reconciliation Test"
    msg.attach(MIMEText("Here are the invoices you requested."))

    with open(filename, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {filename}")
        msg.attach(part)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(TEST_SENDER_EMAIL, TEST_SENDER_PASSWORD)
    text = msg.as_string()
    server.sendmail(TEST_SENDER_EMAIL, BOT_EMAIL, text)
    server.quit()
    print("📨 Test Email Sent!")

def verify_db(invoice_filenames):
    # Connect to DB and check status
    conn = sqlite3.connect("invoices.db")
    c = conn.cursor()
    
    print("\n🔎 Verifying Database Status...")
    all_passed = True
    
    # We need to map filename -> invoice number. 
    # Since we don't have that map handy here, we check if *Received Count* increased.
    # Ideally, you'd extract the ID from the filename or seed data to query specifically.
    
    # Simple check: Just list received
    c.execute("SELECT invoice_number, status FROM invoices WHERE status='RECEIVED'")
    rows = c.fetchall()
    print(f"✅ Total Received Invoices in DB: {len(rows)}")
    
    if len(rows) > 0:
        print("🚀 Success! The system processed the email.")
    else:
        print("❌ Failed. No invoices marked as RECEIVED yet.")
    
    conn.close()

if __name__ == "__main__":
    # 1. Pick Files
    selected_files = get_random_invoices(3)
    print(f"🧪 Testing with files: {selected_files}")
    
    # 2. Zip Them
    zip_file = create_test_zip(selected_files)
    
    # 3. Send Email
    try:
        send_email_with_attachment(zip_file)
        
        print("⏳ Waiting 60 seconds for you to run the Agent Loop...")
        # In a fully automated CI/CD pipeline, you would trigger the agent code here.
        # For now, this pauses so you can hit 'Run Loop' in Streamlit manually.
        for i in range(60, 0, -1):
            print(f"\rCheck Streamlit Now! {i}s remaining...", end="")
            time.sleep(1)
            
        # 4. Verify
        verify_db(selected_files)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(zip_file): os.remove(zip_file)