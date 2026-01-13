This document details the technical implementation of the AutoEmail System. It breaks down every file, the functions within them, and specifically how data flows between these functions to execute the business logic.

1. Data Models (src/models.py)

These classes are the "Envelopes" that carry data between functions. Understanding these is key to understanding the flow.

Invoice: Represents a row in the database.

Flow: DB 
→
→
 Agent 
→
→
 Logic 
→
→
 UI.

EmailMessage: Represents a raw email fetched from Gmail.

Flow: Gmail Adapter 
→
→
 Agent.

ExtractedInvoiceData: The raw data pulled from a PDF by the LLM.

Flow: LLM Adapter 
→
→
 Agent.

ReconciliationResult: The math result (Received vs. Missing).

Flow: Logic 
→
→
 Agent.

2. Infrastructure Layer (The Input/Output Adapters)
File: src/infra/gmail.py

Role: Translates between Google's complex JSON API and our clean EmailMessage objects.

fetch_unread_emails(limit: int) -> List[EmailMessage]

Technical Logic: Calls users().messages().list() with q='is:unread'. Iterates results. Fetches full payload. Decodes Base64 attachment data from MIME parts. Writes binary data to local download/ folder.

Data Out: Returns a list of EmailMessage objects (containing sender, body, and local file paths to attachments).

send_new_email(to, subject, body) -> str

Technical Logic: constructs a MIMEMultipart object. Embeds the body as MIMEText(..., 'html'). Base64 encodes it. Sends via API.

Data In: Target email, Subject string, HTML Body string.

Data Out: Thread ID string.

File: src/infra/attachments.py

Role: Handles local file manipulation.

convert_pdf_to_images(pdf_path: str) -> List[str]

Technical Logic: Uses pdf2image.convert_from_path (wraps Poppler binary). Renders PDF pages as JPEG images. Saves them to disk with suffix _page_X.jpg.

Data In: Path to a local PDF file.

Data Out: List of paths to the generated JPG images.

File: src/infra/gemini.py

Role: The Intelligence Pipeline.

_perform_ocr(image_paths) -> str (Private Helper)

Technical Logic: Iterates image paths. Loads image into Pillow (PIL). Calls pytesseract.image_to_string. Concatenates all text.

Data Out: One large raw text string.

extract_invoice_data(text_context, image_paths) -> ExtractedInvoiceData

Technical Logic: Calls _perform_ocr. Constructs a prompt combining the Email Body + OCR Text. Sends to Gemini Flash. Parses the returned JSON string (with ast.literal_eval fallback).

Data In: Email body text, List of image paths.

Data Out: ExtractedInvoiceData object (Invoice Numbers, Amounts, GSTINs).

draft_reply(sender, missing, received, context) -> str

Technical Logic: Standard LLM completion call. Prompt instructs LLM to be polite and reference the specific lists provided.

Data Out: A string containing the drafted email body.

File: src/infra/sqlite_db.py

Role: Persistent State Management.

get_pending_invoices_by_sender(email) -> List[Invoice]

Technical Logic: SELECT * FROM invoices WHERE vendor_email LIKE %email% AND status='PENDING'. Maps SQL rows to Invoice dataclasses.

Data Out: List of Invoice objects.

mark_as_received(invoice_number, ...)

Technical Logic: UPDATE invoices SET status='RECEIVED'... WHERE invoice_number=?.

3. Core Layer (The Logic & Orchestration)
File: src/core/logic.py

Role: Pure mathematical comparison.

reconcile(expected_invoices, extracted_ids) -> ReconciliationResult

Technical Logic:

Create Set 
𝐴
A
 = IDs from expected_invoices.

Create Set 
𝐵
B
 = extracted_ids.

Intersection (
𝐴
∩
𝐵
A∩B
) = Received.

Difference (
𝐴
−
𝐵
A−B
) = Missing.

Data In: List of Invoice objects, List of strings (extracted IDs).

Data Out: ReconciliationResult object.

File: src/core/agent.py

Role: The Controller. It moves data between the Infra adapters and the Logic layer.

_extract_email_address(sender_str) -> str

Technical Logic: String splitting. Converts "Name <email>" to "email".

start_reconciliation_flow(vendor_email)

Flow:

Calls db.get_pending_invoices_by_sender.

Loops through results to build an HTML string (<table>...</table>).

Calls email.send_new_email with that HTML.

run_reconciliation_cycle() (The Main Loop)

Flow:

Fetch: Calls email.fetch_unread_emails() 
→
→
 Gets [EmailMessage].

Loop: Iterates through each email.

Clean: Calls _extract_email_address.

Triage (Manual Flags): Checks email.body for "http" or email.attachments for ".zip". If found, returns a "Manual Review" status.

Triage (Empty): Checks if attachment list is empty. If so, calls llm.draft_reply complaining about missing files.

Processing:

Calls attachments.convert_pdf_to_images 
→
→
 Gets [image_paths].

Calls llm.extract_invoice_data 
→
→
 Gets ExtractedInvoiceData.

Logic:

Calls logic.reconcile(pending_invoices, extracted_data) 
→
→
 Gets ReconciliationResult.

Action:

Loops result.updated_invoices 
→
→
 Calls db.mark_as_received.

Calls llm.draft_reply(result.missing) 
→
→
 Gets draft string.

Report: Bundles everything into a Dict and returns it to the UI.

4. ETL Layer (Initialization)
File: seed_real_data.py

Role: One-time data ingestion.

seed_real_data()

Flow:

Reset: Deletes invoices.db.

Init: Creates new DB table.

Scan: os.listdir('s3_invoices') gets all PDF filenames.

Loop: For each PDF:

attachments.convert_pdf_to_images 
→
→
 Images.

llm.extract_invoice_data 
→
→
 JSON (GSTIN, Amount, ID).

Creates Invoice object with status=PENDING.

db.add_invoice(Invoice).

5. UI Layer (Presentation)
File: app.py

Role: User Interaction.

main()

State: Checks st.session_state. If Agent is missing, calls config.get_agent().

Sidebar: Calls db.get_all_invoices() to display the counts.

Tab 1 (Kickoff): Takes input string 
→
→
 calls agent.start_reconciliation_flow.

Tab 2 (Process): Button click 
→
→
 calls agent.run_reconciliation_cycle.

Approval Queue: Iterates the report list returned by the agent. Displays draft text area. Button click 
→
→
 calls agent.send_approved_reply.

6. Complete Data Lifecycle Example

Scenario: Vendor replies with a PDF.

Gmail API receives raw bytes 
→
→
 Saves temp.pdf to disk 
→
→
 Creates EmailMessage with path download/temp.pdf.

Agent passes download/temp.pdf to Attachment Adapter.

Attachment Adapter runs Poppler 
→
→
 saves temp_page_1.jpg 
→
→
 returns path.

Agent passes temp_page_1.jpg to Gemini Adapter.

Gemini Adapter runs Tesseract ("INV: 123") 
→
→
 Sends text to LLM 
→
→
 Returns ExtractedInvoiceData(ids=['123']).

Agent queries DB Adapter 
→
→
 Gets [Invoice(123), Invoice(456)].

Agent passes both lists to Logic 
→
→
 Returns ReconciliationResult(received=['123'], missing=['456']).

Agent calls DB Adapter 
→
→
 Updates Invoice 123 to RECEIVED.

Agent calls Gemini Adapter with list ['456'] 
→
→
 Returns draft "Please send #456".

UI displays draft. User clicks Send. Gmail Adapter sends email.