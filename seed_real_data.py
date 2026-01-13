import os
import time
from dotenv import load_dotenv
from src.infra.sqlite_db import SQLiteInvoiceRepository
from src.infra.gemini import GeminiLLMProvider
from src.infra.attachments import PdfAttachmentProcessor
from src.models import Invoice, InvoiceStatus

load_dotenv()

def seed_real_data():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not found.")
        return

    # 1. Clean Slate: Delete old DB to remove "poisoned" OCR typos
    if os.path.exists("invoices.db"):
        try:
            os.remove("invoices.db")
            print("🗑️  Deleted old database to update schema and fix typos.")
        except PermissionError:
            print("❌ Error: Could not delete 'invoices.db'. Is the app running? Close it first.")
            return

    # 2. Initialize
    repo = SQLiteInvoiceRepository() # Creates new table
    llm = GeminiLLMProvider(api_key)
    processor = PdfAttachmentProcessor()
    
    s3_folder = "s3_invoices"
    
    if not os.path.exists(s3_folder):
        print("❌ s3_invoices folder not found.")
        return

    files = [f for f in os.listdir(s3_folder) if f.lower().endswith('.pdf')]
    print(f"📂 Found {len(files)} PDFs. Starting Vision Extraction...")
    
    # 3. User Input
    sim_email = input("Enter your Test Sender Email Address (e.g., orionbee13@gmail.com): ").strip()
    if not sim_email:
        print("❌ Email required.")
        return

    # 4. Processing Loop
    for idx, filename in enumerate(files):
        pdf_path = os.path.join(s3_folder, filename)
        image_paths = []
        
        try:
            print(f"[{idx+1}/{len(files)}] Reading {filename}...", end=" ")
            
            # Convert PDF to Images
            image_paths = processor.convert_pdf_to_images(pdf_path)
            
            # Extract Data using Gemini Vision
            # We add a specific instruction to watch out for the I/1 confusion
            context_prompt = (
                "Extract metadata for database seeding. "
                "CRITICAL: Be extremely careful with Invoice Numbers. "
                "Distinguish clearly between the letter 'I' (India) and the number '1'. "
                "Example: 'H33HL25I...' is likely correct, 'H33HL251...' might be an OCR error if the font is confusing."
            )
            
            data = llm.extract_invoice_data(
                text_context=context_prompt, 
                image_paths=image_paths
            )
            
            if not data.invoice_numbers:
                print("⚠️  Skipped (No Invoice # found)")
                continue

            # Safe Getters
            inv_num = data.invoice_numbers[0]
            amt = data.amounts[0] if data.amounts else 0.0
            gst = data.gstins[0] if data.gstins else "Unknown GSTIN"
            hotel = data.hotel_names[0] if data.hotel_names else "Unknown Hotel"
            work = data.workspaces[0] if data.workspaces else "Unknown Client"

            new_invoice = Invoice(
                id=None,
                invoice_number=inv_num,
                vendor_email=sim_email,
                amount=amt,
                status=InvoiceStatus.PENDING,
                gstin=gst,              
                hotel_name=hotel,       
                workspace=work          
            )
            
            repo.add_invoice(new_invoice)
            print(f"✅ Added {inv_num} (₹{amt})")
            
            # Rate limit protection
            time.sleep(1.0) 

        except Exception as e:
            print(f"❌ Error: {e}")
        
        finally:
            # Cleanup images
            for img in image_paths:
                if os.path.exists(img): os.remove(img)

    print(f"\n🎉 Finished! Seeded invoices linked to: {sim_email}")

if __name__ == "__main__":
    seed_real_data()