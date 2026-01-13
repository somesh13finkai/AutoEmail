import os
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
ACCESS_KEY = os.getenv("S3_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
DOWNLOAD_FOLDER = "s3_invoices"
LIMIT = 200

def download_invoices():
    if not all([BUCKET_NAME, ACCESS_KEY, SECRET_KEY]):
        print("Error: S3 credentials missing in .env file.")
        return

    # Create directory
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)
        print(f"Created folder: {DOWNLOAD_FOLDER}")

    # Initialize S3 Client
    s3 = boto3.client(
        's3',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY
    )

    try:
        print(f"Connecting to bucket: {BUCKET_NAME}...")
        
        # List objects
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME)

        count = 0
        
        print("Starting download...")
        
        for page in pages:
            if "Contents" not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                
                # Filter: Only download PDFs, skip folders
                if key.endswith("/") or not key.lower().endswith(".pdf"):
                    continue
                
                # Create local filename (flattening folders if necessary)
                filename = os.path.basename(key)
                local_path = os.path.join(DOWNLOAD_FOLDER, filename)
                
                # Download
                print(f"[{count+1}/{LIMIT}] Downloading {filename}...")
                s3.download_file(BUCKET_NAME, key, local_path)
                
                count += 1
                if count >= LIMIT:
                    print("\n✅ Download limit reached!")
                    return

        if count == 0:
            print("Warning: No PDF files found in the bucket.")
        else:
            print(f"\n✅ Finished! Downloaded {count} files to '{DOWNLOAD_FOLDER}/'")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    download_invoices()