import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logic import ReconciliationService
from src.core.agent import InvoiceAgent
from src.models import Invoice, InvoiceStatus

# 1. Test the Math (Reconciliation)
def test_reconciliation_math():
    # Setup: We expect A, B, C
    pending = [
        Invoice(id=1, invoice_number="INV-A", vendor_email="v@t.com", amount=100, status=InvoiceStatus.PENDING),
        Invoice(id=2, invoice_number="INV-B", vendor_email="v@t.com", amount=100, status=InvoiceStatus.PENDING),
        Invoice(id=3, invoice_number="INV-C", vendor_email="v@t.com", amount=100, status=InvoiceStatus.PENDING),
    ]
    # Input: We extracted A and C
    extracted_ids = ["INV-A", "INV-C"]

    # Action
    result = ReconciliationService.reconcile(pending, extracted_ids)

    # Assertions
    assert "INV-A" in result.received_invoices
    assert "INV-C" in result.received_invoices
    assert "INV-B" in result.missing_invoices
    assert len(result.updated_invoices) == 2

# 2. Test Email Cleaning Logic
def test_email_extraction():
    # We can instantiate Agent with None for dependencies since we only test the helper method
    agent = InvoiceAgent(None, None, None, None, None)
    
    raw_1 = "Somesh Shukla <orionbee13@gmail.com>"
    raw_2 = "orionbee13@gmail.com"
    raw_3 = "Accounts <billing@hotel.com>"

    assert agent._extract_email_address(raw_1) == "orionbee13@gmail.com"
    assert agent._extract_email_address(raw_2) == "orionbee13@gmail.com"
    assert agent._extract_email_address(raw_3) == "billing@hotel.com"