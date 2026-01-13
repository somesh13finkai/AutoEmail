import os
from dotenv import load_dotenv

from src.infra.gmail import GmailProvider
from src.infra.gemini import GeminiLLMProvider
from src.infra.sqlite_db import SQLiteInvoiceRepository
from src.infra.faiss_db import FAISSVectorStore
from src.infra.attachments import PdfAttachmentProcessor
from src.core.agent import InvoiceAgent

load_dotenv()

def get_agent() -> InvoiceAgent:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in .env")

    return InvoiceAgent(
        email_provider=GmailProvider(),
        llm_provider=GeminiLLMProvider(api_key=api_key),
        db=SQLiteInvoiceRepository(),
        vector_store=FAISSVectorStore(),
        attachment_processor=PdfAttachmentProcessor()
    )