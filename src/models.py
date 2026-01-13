from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

class InvoiceStatus(Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"

@dataclass
class Invoice:
    id: Optional[int]
    invoice_number: str
    vendor_email: str
    amount: float
    status: InvoiceStatus
    # New Fields for the Email Table
    gstin: str = ""
    hotel_name: str = ""
    workspace: str = ""  # This usually corresponds to "Bill To" name
    thread_id: Optional[str] = None
    filename: Optional[str] = None

@dataclass
class EmailMessage:
    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    attachments: List[str] = field(default_factory=list) # List of file paths

@dataclass
class ExtractedInvoiceData:
    invoice_numbers: List[str]
    detected_poc_change: bool
    new_poc_details: Optional[str] = None
    # Extra metadata for seeding
    amounts: List[float] = field(default_factory=list)
    gstins: List[str] = field(default_factory=list)
    hotel_names: List[str] = field(default_factory=list)
    workspaces: List[str] = field(default_factory=list)

@dataclass
class ReconciliationResult:
    received_invoices: List[str]
    missing_invoices: List[str]
    updated_invoices: List[Invoice]