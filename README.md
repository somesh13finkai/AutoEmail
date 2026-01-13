
Hotel Invoice Email Assistant

A modular, AI-powered Accounts Payable automation system.
This application acts as an intelligent agent that manages vendor communication. It tracks missing invoices, emails vendors to request them, reads incoming replies (including attachments and zip files), extracts data using Computer Vision (Gemini 2.0), and reconciles them against a local ledger.
🌟 Key Features
📧 Automated Communication: Sends formatted HTML tables of missing invoices to vendors via Gmail.
👁️ AI Computer Vision: Uses Google Gemini 2.0 Flash to read PDF invoices. It is prompt-engineered to correct OCR errors (e.g., distinguishing 'I' from '1').
🧠 Intelligent Matching: Uses fuzzy logic and suffix heuristics to match extracted invoice numbers against the database, handling file naming inconsistencies.
📂 Multi-Format Support: Automatically handles simple PDF attachments and unzips .zip archives containing multiple files.
human-in-the-Loop: A Streamlit dashboard allows users to review AI findings and edit/approve draft email replies before they are sent.


🛠️ Architecture
The system follows a Modular Monolith architecture with Dependency Injection:
Interface Layer (Streamlit): User interaction for kicking off workflows and approving actions.
Core Agent: Orchestrates the logic between email, database, and AI.
Infrastructure:
Gmail API: For sending/receiving emails.
Gemini API: For Vision/OCR and text generation.
SQLite: Stores invoice state (PENDING vs RECEIVED).
PDF2Image: Converts PDFs to images for the Vision model.
⚙️ Prerequisites
Python 3.9+
Poppler: Required for PDF processing.
MacOS: brew install poppler
Windows: Download Binary and add to PATH.
Linux: sudo apt-get install poppler-utils
Google Cloud Project:
Enabled Gmail API.
Enabled Gemini (Generative AI) API.
🚀 Installation
Clone the Repository
code
Bash
git clone https://github.com/yourusername/invoice-reconciler.git
cd invoice-reconciler
Create a Virtual Environment
code
Bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies
code
Bash
pip install streamlit pandas google-genai google-auth-oauthlib google-api-python-client pdf2image pillow python-dotenv schedule boto3
🔐 Configuration
1. Environment Variables
Create a .env file in the root directory:
code
Ini
# Required for AI Vision
GOOGLE_API_KEY="your_gemini_api_key_here"

# Optional (Only if using S3 features)
S3_BUCKET_NAME="your_bucket"
S3_ACCESS_KEY_ID="your_key"
S3_SECRET_ACCESS_KEY="your_secret"
2. Gmail Credentials
Go to the Google Cloud Console.
Create credentials for an OAuth 2.0 Client ID (Desktop App).
Download the JSON file.
Rename it to credentials.json and place it in the project root.
Note: On the first run, a browser window will open to authorize access. This creates a token.json file automatically.
🏃 Usage Guide
Step 1: Seed the Database
The system needs a list of "Expected" invoices to work.
For Testing: Run the build script to create dummy data.
code
Bash
python build_db.py
(Tip: Edit build_db.py to change the vendor email to your own secondary email address for testing).
For Real Data: To seed from existing PDFs (simulating a booking platform export):
code
Bash
python seed_real_data.py
Step 2: Run the Dashboard
Launch the user interface:
code
Bash
streamlit run app.py
Step 3: The Workflow
Tab 1: 🚀 Kickoff & Reminders
Enter the Vendor's Email.
Click "Send Initial Request".
The agent sends an email listing all PENDING invoices for that vendor.
Vendor Action (Simulation)
Reply to that email from your other account.
Attach a PDF (or a Zip file) containing the invoice.
Tab 2: 🔄 Process Replies
Click "Run Reconciliation Loop".
The agent will:
Fetch the unread reply.
Read the attachment using Gemini Vision.
Match the invoice number to the database.
Mark it as RECEIVED.
Approval Queue:
Scroll down to see the draft reply.
The AI will draft a text: "Received INV-001. Still waiting for INV-002."
Click "Approve & Send Reply".

Tab 3: 📊 Analytics
View charts of Total Liability vs. Paid.
See breakdowns by Hotel or Client.
📂 Project Structure
code
Text
.
├── app.py                  # Main Streamlit Dashboard
├── build_db.py             # Script to create dummy database data
├── download_s3.py          # Script to fetch invoices from AWS S3
├── run_scheduler.py        # Headless script for cron/scheduled jobs
├── seed_real_data.py       # Script to seed DB from local/S3 PDFs
├── requirements.txt        # Python dependencies
├── .env                    # API Keys
├── credentials.json        # Gmail OAuth Client Secret
├── token.json              # Gmail OAuth Token (Generated on first run)
└── src/
    ├── config.py           # Dependency Injection wiring
    ├── models.py           # Data Classes (Invoice, EmailMessage)
    ├── core/
    │   ├── agent.py        # Main Agent Logic (The "Brain")
    │   ├── logic.py        # Fuzzy matching & reconciliation algorithms
    │   └── interfaces.py   # Abstract Base Classes
    └── infra/
        ├── attachments.py  # PDF to Image conversion
        ├── gemini.py       # Google Gemini LLM Provider
        ├── gmail.py        # Gmail API Provider
        └── sqlite_db.py    # SQL Database Repository
❓ Troubleshooting
1. pdf2image.exceptions.PDFInfoNotInstalledError
Cause: Poppler is not installed or not in PATH.
Fix: Follow the prerequisites section to install Poppler for your OS.
2. Gmail Authentication Fails
Cause: Token expired or scopes changed.
Fix: Delete the token.json file and restart the app. It will prompt you to log in again.
3. "Agent failed to initialize"
Cause: Missing API Key.
Fix: Ensure GOOGLE_API_KEY is set in your .env file.
4. Invoices not matching
Cause: OCR misreading fonts or file naming issues.
Fix: Check the logs in the terminal. The logic.py file uses fuzzy matching (70% threshold), but extremely blurry images may fail.
