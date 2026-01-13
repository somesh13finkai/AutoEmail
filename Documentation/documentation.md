Here is the comprehensive technical documentation for the Intelligent Email Automation & Invoice Reconciliation System.

System Documentation: AutoEmail Reconciliation Agent

Version: 1.0 (Prototype)
Date: January 9, 2026
Architectural Style: Hexagonal Architecture (Ports & Adapters)

1. Executive Summary

The AutoEmail Agent is an autonomous system designed to streamline Accounts Payable (AP) workflows. It manages the "Closed Loop" process of collecting missing invoices from vendors.
Unlike standard scripts, it maintains state (Database), understands context (Thread IDs), and possesses cognitive capabilities (reading unstructured PDF data) to reconcile what was expected versus what was received.

2. System Architecture

The system follows SOLID Principles, specifically Dependency Inversion. The core business logic depends only on Abstractions (Interfaces), not concrete implementations (APIs).

Layers

Domain Layer (src/core/): Contains business rules, logic, and orchestrators. It knows nothing about Google, OpenAI, or SQLite.

Infrastructure Layer (src/infra/): Contains the specific adapters that talk to the outside world (Gmail API, Gemini API, File System, SQLite).

Application Layer (app.py): The entry point (Streamlit UI) that injects dependencies and triggers the agent.

3. Technology Stack
Component	Technology	Purpose
Language	Python 3.11+	Core runtime environment.
UI	Streamlit	Dashboard for monitoring and manual triggers.
LLM Provider	Google Gemini 2.0 Flash	"The Brains": JSON Extraction & Email Drafting.
OCR Engine	Tesseract (via pytesseract)	"The Eyes": Converts PDF pixels to raw text.
Email Service	Gmail API (OAuth2)	Sending/Receiving emails & Thread management.
Database	SQLite3	Local persistence for Invoice Status (Pending/Received).
Image Proc	pdf2image / Pillow	Converting PDF pages to images for OCR.
Cloud Storage	AWS S3 (boto3)	Source of historical invoices for seeding.
4. Directory Structure
code
Text
download
content_copy
expand_less
AutoEmail/
├── .env                        # API Keys (Google, AWS)
├── credentials.json            # Google OAuth Client Secrets
├── token.json                  # User Auth Token (Generated after login)
├── requirements.txt            # Python Dependencies
├── app.py                      # Main UI Entry Point
├── seed_real_data.py           # Script to ingest S3 data into DB
├── download_s3.py              # Helper to fetch files from AWS
├── invoices.db                 # SQLite Database file
├── s3_invoices/                # Local cache of downloaded S3 PDFs
├── download/                   # Temp folder for email attachment processing
└── src/
    ├── config.py               # Dependency Injection Factory
    ├── models.py               # Data Classes (Invoice, EmailMessage)
    ├── core/
    │   ├── interfaces.py       # Abstract Base Classes (Contracts)
    │   ├── logic.py            # Pure Math Logic (Set Difference)
    │   └── agent.py            # The Main Orchestrator (Business Flow)
    └── infra/
        ├── gmail.py            # Gmail Adapter (HTML support, Threading)
        ├── gemini.py           # LLM Adapter (Tesseract -> Text -> JSON)
        ├── sqlite_db.py        # Database Adapter (CRUD operations)
        ├── attachments.py      # PDF Processing Adapter
        └── faiss_db.py         # Vector Store (Placeholder for RAG)
5. Module Details & Data Flow
A. Data Models (src/models.py)

Defines the structure of data moving through the system.

Invoice: Stores invoice_number, amount, gstin, hotel_name, status (PENDING/RECEIVED).

ReconciliationResult: A carrier object containing lists of missing_invoices and received_invoices.

B. The Database (src/infra/sqlite_db.py)

A single table schema invoices:

invoice_number (Text): Unique Identifier.

vendor_email (Text): The key used to link invoices to a specific sender.

status (Text): Controls the logic flow.

gstin, hotel_name, workspace, amount: Metadata for generating professional emails.

C. The Intelligence Pipeline (src/infra/gemini.py)

This is a hybrid OCR + LLM pipeline designed for speed and low cost:

Input: List of image paths (converted from PDF).

Step 1 (OCR): Tesseract scans images 
→
→
 Raw Text string.

Step 2 (LLM Analysis): Gemini 2.0 Flash analyzes Raw Text.

Prompt: "Extract Invoice #, GSTIN, Amount into JSON."

Output: Structured ExtractedInvoiceData object.

D. The Agent Orchestrator (src/core/agent.py)

The "Manager" that ties everything together.

start_reconciliation_flow(vendor_email):

Queries DB for all PENDING invoices for the vendor.

Generates an HTML Table email summarizing the missing items.

Sends the email via Gmail.

run_reconciliation_cycle():

Fetches emails via Gmail.

Cleans sender strings (e.g., extracts email@domain.com from Name <...>).

Branch A (No Attachments): Drafts a reply asking for missing files.

Branch B (Attachments): Runs Intelligence Pipeline on files.

Calls logic.py to compare Extracted IDs vs Expected IDs.

Updates DB status to RECEIVED.

Drafts reply asking only for the remaining missing items.

6. Workflow Life Cycles
Phase 1: Ingestion (Seeding)

Goal: Teach the database what invoices to expect.

Download: download_s3.py fetches PDFs from AWS S3 to local folder.

Extraction: seed_real_data.py loops through local PDFs.

OCR/LLM: Extracts Invoice #, GSTIN, Hotel Name, Amount.

Storage: Inserts into invoices.db with status PENDING and linked to the Simulated Vendor Email (orionbee13@gmail.com).

Phase 2: Initiation (Kickoff)

Goal: Proactively contact the vendor.

User enters vendor email in Streamlit UI.

System retrieves pending list.

System constructs HTML email with a data table.

System sends email: "Action Required: We are missing 200 invoices."

Phase 3: Reconciliation (The Loop)

Goal: Process replies until all invoices are collected.

Vendor Reply: Vendor replies to the thread with 5 PDFs attached.

Detection: System detects email.

Processing:

System reads the 5 PDFs.

System finds IDs: [A, B, C, D, E].

Logic:

DB Update: Mark A, B, C, D, E as RECEIVED.

Calculation: Missing = Total - {A,B,C,D,E}.

Response:

Drafts email: "Thanks for A, B, C, D, E. Please send the remaining 195."

User approves draft in UI.

Repeat: Process continues until Missing list is empty.

7. Operational Costs (Estimated)

Based on a volume of 30 threads/day:

Compute (Server): ~$20/month.

Gmail API: Free (Workspace quota).

Tesseract OCR: Free (Open Source).

Gemini Flash API: ~$0.36/month (approx $0.00055 per thread).

Total: ~$20.50 / Month.

8. Current Limitations & Roadmap
Current Limitations

Concurrency: Uses SQLite, which handles one user at a time.

Trigger: Manual button press ("Run Loop") required to process emails.

Input: Requires S3/Local files for seeding (no direct ERP connection yet).

Roadmap to Production

Database Upgrade: Migrate invoices.db to PostgreSQL for multi-user support.

Background Workers: Implement Celery/Redis to process emails automatically in the background (no button press).

ERP Connector: Build an adapter to fetch "Pending Invoices" directly from SAP/Oracle API.

Dockerization: Containerize the application for easy cloud deployment.

9. Setup Guide (Summary)

Install: pip install -r requirements.txt.

Install Binaries: Tesseract and Poppler must be installed on the OS.

Config: Set GOOGLE_API_KEY in .env. Place credentials.json in root.

Seed: Run python seed_real_data.py.

Run: streamlit run app.py.