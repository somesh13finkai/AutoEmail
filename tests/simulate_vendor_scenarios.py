import os
import time
import smtplib
import imaplib
import email
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION FROM ENV ---
VENDOR_EMAIL = os.getenv("TEST_VENDOR_EMAIL")
VENDOR_APP_PASSWORD = os.getenv("TEST_VENDOR_PASSWORD")
SYSTEM_EMAIL = os.getenv("SYSTEM_BOT_EMAIL")

# Directory containing PDFs to use for simulation
SOURCE_DIR = "tests/golden_pdfs"

if not all([VENDOR_EMAIL, VENDOR_APP_PASSWORD, SYSTEM_EMAIL]):
    print("❌ Error: Missing credentials in .env file.")
    exit(1)

class VendorBot:
    def __init__(self):
        try:
            self.imap = imaplib.IMAP4_SSL("imap.gmail.com")
            self.imap.login(VENDOR_EMAIL, VENDOR_APP_PASSWORD)
            print(f"🤖 VendorBot initialized as {VENDOR_EMAIL}")
        except Exception as e:
            print(f"❌ Login Failed: {e}")
            exit(1)

    def wait_for_system_email(self, timeout_sec=120):
        print("   👂 Listening for email from System...")
        for _ in range(timeout_sec // 5):
            self.imap.select("INBOX")
            # Search for UNREAD emails from your System Address
            status, messages = self.imap.search(None, f'(UNSEEN FROM "{SYSTEM_EMAIL}")')
            
            if status == 'OK' and messages[0]:
                print("   📨 Email received from System!")
                return True
            time.sleep(5)
        
        print("   ❌ Timed out waiting for System email.")
        return False

    def send_email(self, subject, body, attachment_files=None, is_zip=False):
        print(f"   📤 Sending Reply: '{subject}'...")
        msg = MIMEMultipart()
        msg['From'] = VENDOR_EMAIL
        msg['To'] = SYSTEM_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if attachment_files:
            if is_zip:
                zip_name = "remaining_invoices.zip"
                with zipfile.ZipFile(zip_name, 'w') as zf:
                    for f in attachment_files:
                        path = os.path.join(SOURCE_DIR, f)
                        if os.path.exists(path):
                            zf.write(path, arcname=f)
                files_to_send = [zip_name]
            else:
                files_to_send = [os.path.join(SOURCE_DIR, f) for f in attachment_files]

            for filepath in files_to_send:
                if not os.path.exists(filepath): continue
                
                filename = os.path.basename(filepath)
                with open(filepath, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f"attachment; filename= {filename}")
                    msg.attach(part)
                
                if is_zip and filename == "remaining_invoices.zip":
                    os.remove(filepath)

        # SMTP Send
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(VENDOR_EMAIL, VENDOR_APP_PASSWORD)
        server.sendmail(VENDOR_EMAIL, SYSTEM_EMAIL, msg.as_string())
        server.quit()
        print("   ✅ Sent.")

def run_simulation():
    bot = VendorBot()
    
    # Get available files
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ Error: {SOURCE_DIR} not found.")
        return

    all_pdfs = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".pdf")]
    if len(all_pdfs) < 5:
        print("❌ Need at least 5 PDFs in tests/golden_pdfs to run this simulation.")
        return

    print("\n--- SIMULATION STARTED ---")
    print("1. Please go to Streamlit and send 'Kickoff Email' to the vendor now.")
    
    # --- SCENARIO 1: PARTIAL SEND ---
    if bot.wait_for_system_email():
        # Pick 2 random files
        batch_1 = all_pdfs[:2] 
        print(f"   🎭 Acting: Sending only 2 invoices ({batch_1})...")
        bot.send_email(
            subject="Re: Action Required",
            body="Here are some of the invoices. I will check for the others.",
            attachment_files=batch_1,
            is_zip=False
        )
    else:
        return

    print("\n👉 ACTION: Go to Streamlit -> 'Run Loop' -> 'Approve Draft'.")
    print("   (Wait for the bot to ask for the missing ones...)")

    # --- SCENARIO 2: POC CHANGE (No Attachments) ---
    if bot.wait_for_system_email():
        print("   🎭 Acting: Claiming POC Change (No files)...")
        bot.send_email(
            subject="Re: Action Required",
            body="I actually don't handle the older bookings. Please contact manager@hotel.com for the rest.",
            attachment_files=[] 
        )
    else:
        return

    print("\n👉 ACTION: Go to Streamlit -> 'Run Loop' -> 'Approve Draft'.")
    print("   (The System should have drafted a reply acknowledging the POC change but asking for files).")

    # --- SCENARIO 3: ZIP CLEANUP ---
    if bot.wait_for_system_email():
        remaining_files = all_pdfs[2:] # The rest
        print(f"   🎭 Acting: Sending remaining {len(remaining_files)} invoices in a ZIP...")
        bot.send_email(
            subject="Re: Action Required",
            body="Okay, I found the rest. Sending them in a zip file.",
            attachment_files=remaining_files,
            is_zip=True
        )

    print("\n🏁 Simulation Complete. Run the Agent Loop one last time to verify completion.")

if __name__ == "__main__":
    run_simulation()