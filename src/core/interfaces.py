from abc import ABC, abstractmethod
from typing import List, Any, Optional
from src.models import EmailMessage, Invoice, ExtractedInvoiceData

class IEmailProvider(ABC):
    @abstractmethod
    def fetch_unread_emails(self, limit: int = 5) -> List[EmailMessage]:
        """Fetches unread emails that have attachments."""
        pass

    @abstractmethod
    def send_reply(self, thread_id: str, to_email: str, body: str):
        """Replies to an existing conversation thread."""
        pass

    @abstractmethod
    def send_new_email(self, to_email: str, subject: str, body: str) -> str:
        """
        Sends a fresh email to start a conversation.
        Returns the thread_id of the new email.
        """
        pass

class ILLMProvider(ABC):
    @abstractmethod
    def extract_invoice_data(self, text_context: str, image_paths: List[str]) -> ExtractedInvoiceData:
        """
        Uses OCR/Vision to extract invoice numbers and POC details.
        """
        pass

    @abstractmethod
    def draft_reply(self, sender: str, missing_invoices: List[str], received_invoices: List[str], context: str) -> str:
        """
        Generates a polite email reply based on the reconciliation status.
        """
        pass

class IInvoiceRepository(ABC):
    @abstractmethod
    def get_pending_invoices_by_sender(self, sender_email: str) -> List[Invoice]:
        """Returns all invoices marked PENDING for a specific vendor email."""
        pass

    @abstractmethod
    def mark_as_received(self, invoice_number: str, filename: str, thread_id: str):
        """Updates status to RECEIVED and links the file/thread."""
        pass

    @abstractmethod
    def add_invoice(self, invoice: Invoice):
        """Adds a new expected invoice to the database."""
        pass

    @abstractmethod
    def get_all_invoices(self) -> List[Invoice]:
        """Returns all invoices (used for UI display)."""
        pass

class IVectorStore(ABC):
    @abstractmethod
    def add_documents(self, texts: List[str], metadata: List[dict]):
        pass

    @abstractmethod
    def search(self, query: str, k: int = 3) -> List[str]:
        pass

class IAttachmentProcessor(ABC):
    @abstractmethod
    def convert_pdf_to_images(self, pdf_path: str) -> List[str]:
        """Converts a PDF file into a list of image file paths (for OCR/Vision)."""
        pass