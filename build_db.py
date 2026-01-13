import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from src.infra.sqlite_db import SQLiteInvoiceRepository
from src.models import Invoice, InvoiceStatus

def seed_db():
    print("Seeding Database...")
    repo = SQLiteInvoiceRepository()
    
    # Dummy Expected Invoices
    # Note: Ensure the 'vendor_email' matches what your Gmail API will see (e.g., your own secondary email for testing)
    dummies = [
        Invoice(None, "INV-101", "vendor@example.com", 500.0, InvoiceStatus.PENDING),
        Invoice(None, "INV-102", "vendor@example.com", 1200.0, InvoiceStatus.PENDING),
        Invoice(None, "INV-103", "vendor@example.com", 300.0, InvoiceStatus.PENDING),
    ]
    
    for inv in dummies:
        repo.add_invoice(inv)
        
    print(f"Seeded {len(dummies)} invoices.")

if __name__ == "__main__":
    seed_db()