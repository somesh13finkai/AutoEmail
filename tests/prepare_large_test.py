import os
import sys
import json
import shutil
import random
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infra.gemini import GeminiLLMProvider
from src.infra.attachments import PdfAttachmentProcessor

load_dotenv()

# CONFIGURATION
SOURCE_DIR = "s3_invoices"          # Where your 200 downloads are
TARGET_DIR = "tests/golden_pdfs"    # Where the test files go
CONFIG_FILE = "tests/test_config.json" # Where we save the ID mapping
SAMPLE_SIZE = 100                   # How many files to test

def prepare_test_data():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY missing.")
        return

    # 1. Initialize Tools
    llm = GeminiLLMProvider(api_key)
    processor = PdfAttachmentProcessor()

    # 2. Clear and Setup Target Directory
    if os.path.exists(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)
    os.makedirs(TARGET_DIR)
    
    # 3. Pick Random Files
    all_files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith('.pdf')]
    
    if len(all_files) < SAMPLE_SIZE:
        print(f"⚠️  Only found {len(all_files)} files. Using all of them.")
        selected_files = all_files
    else:
        selected_files = random.sample(all_files, SAMPLE_SIZE)

    print(f"🚀 Preparing {len(selected_files)} files for Stress Testing...")
    print("   This involves reading each file once to establish Ground Truth.")
    
    ground_truth_map = {}
    
    for idx, filename in enumerate(selected_files):
        src_path = os.path.join(SOURCE_DIR, filename)
        dst_path = os.path.join(TARGET_DIR, filename)
        
        # Copy file
        shutil.copy2(src_path, dst_path)
        
        # Extract ID for Ground Truth
        try:
            images = processor.convert_pdf_to_images(dst_path)
            # Use a fast prompt just to get the ID
            context = "Extract the Invoice Number strictly for testing validation."
            data = llm.extract_invoice_data(context, images)
            
            # Cleanup images
            for img in images:
                if os.path.exists(img): os.remove(img)

            if data.invoice_numbers:
                invoice_id = data.invoice_numbers[0]
                ground_truth_map[filename] = invoice_id
                print(f"   [{idx+1}/{len(selected_files)}] ✅ {filename} -> {invoice_id}")
            else:
                print(f"   [{idx+1}/{len(selected_files)}] ⚠️  Skipping (No ID found): {filename}")
                os.remove(dst_path) # Remove bad file from test set

        except Exception as e:
            print(f"   ❌ Error processing {filename}: {e}")

    # 4. Save Configuration
    with open(CONFIG_FILE, 'w') as f:
        json.dump(ground_truth_map, f, indent=4)

    print(f"\n✨ Preparation Complete!")
    print(f"   - {len(ground_truth_map)} files staged in {TARGET_DIR}")
    print(f"   - Configuration saved to {CONFIG_FILE}")
    print("   👉 Now run 'python tests/test_whole_system.py'")

if __name__ == "__main__":
    prepare_test_data()