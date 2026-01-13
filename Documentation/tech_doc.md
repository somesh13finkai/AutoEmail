Here is the comprehensive technical documentation for the system in its current state. This documentation reflects the exact code structure, logic, and features we have built, including the recent fixes for email extraction, HTML tables, and empty attachment handling.

Technical Documentation: AutoEmail Reconciliation System

Version: 1.1 (Stable Prototype)
Date: January 9, 2026
Architectural Pattern: Hexagonal Architecture (Ports & Adapters)

1. Project Overview

The AutoEmail System is an intelligent, agentic workflow automation tool designed for Accounts Payable (AP) Invoice Reconciliation.

It automates the "Closed Loop" communication process with vendors:

Ingestion: Reads historical invoices (PDFs) to build an "Expected" ledger.

Kickoff: Proactively emails vendors with a detailed HTML table of missing invoices.

Reconciliation: Listens for replies, reads attached PDFs using OCR/LLM, matches them against the ledger, and updates the status.

Follow-up: Automatically drafts polite replies asking only for the remaining missing invoices, or alerting the vendor if they forgot attachments.

2. System Architecture

The system adheres to SOLID principles, specifically Dependency Inversion.

Core (Inner Layer): Contains business logic (Agent, ReconciliationService). It has no external dependencies.

Infra (Outer Layer): Contains adapters for Gmail, Gemini, SQLite, and File Systems.

Interfaces: The Core communicates with Infra via abstract interfaces defined in interfaces.py.

3. Directory Structure & File Manifest
code
Text
download
content_copy
expand_less
AutoEmail/
├── .env                        # Config: GOOGLE_API_KEY, S3 Credentials
├── credentials.json            # OAuth2 Client Secrets (GCP)
├── token.json                  # OAuth2 User Session Token
├── requirements.txt            # Python dependencies (boto3, pytesseract, streamlit, etc.)
├── app.py                      # UI Layer: Streamlit Dashboard
├── seed_real_data.py           # ETL Script: S3 -> OCR -> DB
├── download_s3.py              # Utility: Fetch files from AWS
├── invoices.db                 # Persistence: SQLite Database
├── s3_invoices/                # Local storage for S3 downloads
├── download/                   # Temp storage for incoming email attachments
└── src/
    ├── __init__.py
    ├── config.py               # Dependency Injection Container
    ├── models.py               # Domain Data Transfer Objects (DTOs)
    ├── core/
    │   ├── __init__.py
    │   ├── interfaces.py       # Abstract Base Classes
    │   ├── logic.py            # Pure Business Logic (Set Theory)
    │   └── agent.py            # Main Orchestrator (The "Brain")
    └── infra/
        ├── __init__.py
        ├── gmail.py            # Adapter: Gmail API (Send/Receive)
        ├── gemini.py           # Adapter: Tesseract + Gemini Flash
        ├── sqlite_db.py        # Adapter: Database CRUD
        ├── faiss_db.py         # Adapter: Vector Store (Placeholder)
        └── attachments.py      # Adapter: PDF to Image conversion
4. Component Detail Reference
A. Data Models (src/models.py)

Defines the schema for data passing through the system.

Invoice:

invoice_number (str): Primary matching key.

vendor_email (str): Foreign key to link to sender.

status (Enum): PENDING or RECEIVED.

gstin, hotel_name, workspace, amount: Metadata for email generation.

ExtractedInvoiceData: Output from the LLM containing lists of IDs, amounts, GSTINs, etc.

ReconciliationResult: Output from Logic layer containing received_invoices (list) and missing_invoices (list).

B. Core Layer (src/core/)

1. agent.py (InvoiceAgent)
The central controller.

_extract_email_address(sender_str):

Logic: regex-style split to turn "Name <email@domain.com>" into "email@domain.com". Fixes DB query mismatches.

start_reconciliation_flow(vendor_email):

Logic: Queries DB for PENDING items. Constructs a professional HTML Table (using <table>, <tr>, <td> tags) with CSS styling. Sends via email_provider.

run_reconciliation_cycle():

Logic: Fetches unread emails.

Edge Case Handling: If an email has no attachments, it triggers a specific workflow to draft a reply saying "You forgot the PDF."

Normal Flow: Sends PDFs to Gemini -> Matches IDs -> Updates DB -> Drafts Reply.

2. logic.py (ReconciliationService)

Logic: Missing_List = Pending_Set - Extracted_Set. Ensures we never ask for an invoice twice.

C. Infrastructure Layer (src/infra/)

1. gmail.py (GmailProvider)

Query: q='is:unread' (Modified to find all unread emails, even without attachments).

MIME Handling: Uses MIMEMultipart and MIMEText(..., 'html') to support bold text and tables in emails.

2. gemini.py (GeminiLLMProvider)

Hybrid Pipeline:

OCR: Uses pytesseract to scrape raw text from images (Cost/Speed optimization).

LLM: Sends raw text to Gemini 2.0 Flash.

Prompting: Instructed to return strictly formatted JSON containing invoice_numbers, gstins, hotel_names, etc.

Resiliency: Uses ast.literal_eval as a fallback if json.loads fails due to markdown formatting.

3. sqlite_db.py (SQLiteInvoiceRepository)

Schema: Table invoices with columns: id, invoice_number, vendor_email, amount, status, gstin, hotel_name, workspace, thread_id, filename.

4. attachments.py (PdfAttachmentProcessor)

Uses pdf2image (Poppler) to convert PDF pages into a list of JPEG paths for the OCR engine.

5. Logic Workflows
Workflow A: Database Seeding (seed_real_data.py)

Used to initialize the system with historical data.

Deletes old invoices.db to ensure schema freshness.

Iterates through s3_invoices/ folder.

Extraction: Converts PDF -> Images -> Tesseract Text -> Gemini JSON.

Metadata Capture: Captures GSTIN, Hotel Name, Amount.

Persist: Saves to DB linked to the orionbee13@gmail.com (Simulated Vendor).

Workflow B: The Kickoff

User inputs target email in Streamlit.

Agent fetches all PENDING invoices for that target.

Agent builds an HTML string with a table displaying: Workspace | Hotel | GSTIN | Invoice # | Amount.

Sends email with subject "Action Required: ...".

Workflow C: The Response Loop

Detection: Agent fetches unread emails.

Sanitization: Extracts the pure email address from the sender header.

Check:

If Attachments exist:

Extract Invoice IDs.

Update DB (PENDING -> RECEIVED).

Draft reply: "Thanks for [Found]. Please send [Missing]."

If No Attachments:

Draft reply: "Thanks for the email, but you forgot the attachments. Please send [Missing]."

Approval: User reviews the draft in Streamlit and clicks "Approve & Send".

6. API Configuration
Google Cloud (GCP)

API: Gmail API enabled.

Auth: OAuth 2.0 Client ID (Desktop App).

Scopes: https://www.googleapis.com/auth/gmail.modify (Read, Send, Modify labels).

Google AI Studio

Model: gemini-2.0-flash.

Key: Stored in .env as GOOGLE_API_KEY.

7. Known Behaviors & Features

Strict Email Matching: The database query strictly matches the email address. The code now automatically strips "Name <...>" to ensure matches work.

Duplicate Prevention: The logic layer mathematically ensures that once an invoice is marked RECEIVED, it is never requested again.

Empty Email Handling: The system proactively catches replies with missing files and prompts the vendor to correct the mistake.

Threading: All replies use the In-Reply-To and References headers to keep the conversation in a single Gmail thread.

8. Deployment Requirements

To run this system, the host machine needs:

Python 3.11+

Tesseract OCR Engine (Binary installed on OS).

Poppler Utils (Binary installed for PDF conversion).

Internet Access (For Gmail and Gemini APIs).

Write Access to local disk (For SQLite DB and Temp Downloads).

This documentation covers the entire codebase functionality as of the latest successful test run.