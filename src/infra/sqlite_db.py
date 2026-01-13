import sqlite3
import datetime # <--- New import
from typing import List, Dict, Optional
from src.core.interfaces import IInvoiceRepository
from src.models import Invoice, InvoiceStatus

class SQLiteInvoiceRepository(IInvoiceRepository):
    def __init__(self, db_path: str = "invoices.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Added: last_reminder_sent_at, received_at
        c.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                vendor_email TEXT,
                amount REAL,
                status TEXT,
                gstin TEXT,
                hotel_name TEXT,
                workspace TEXT,
                thread_id TEXT,
                filename TEXT,
                last_reminder_sent_at TIMESTAMP,
                received_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def add_invoice(self, invoice: Invoice):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Initialize timestamps as None
        c.execute('''
            INSERT INTO invoices (invoice_number, vendor_email, amount, status, gstin, hotel_name, workspace, thread_id, filename, last_reminder_sent_at, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
        ''', (invoice.invoice_number, invoice.vendor_email, invoice.amount, invoice.status.value, 
              invoice.gstin, invoice.hotel_name, invoice.workspace, invoice.thread_id, invoice.filename))
        conn.commit()
        conn.close()

    def get_pending_invoices_by_sender(self, sender_email: str) -> List[Invoice]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT * FROM invoices 
            WHERE vendor_email LIKE ? AND status = ?
        ''', (f"%{sender_email}%", InvoiceStatus.PENDING.value))
        
        rows = c.fetchall()
        invoices = []
        for row in rows:
            invoices.append(self._map_row_to_invoice(row))
        conn.close()
        return invoices

    def mark_as_received(self, invoice_number: str, filename: str, thread_id: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.datetime.now()
        c.execute('''
            UPDATE invoices 
            SET status = ?, filename = ?, thread_id = ?, received_at = ?
            WHERE invoice_number = ?
        ''', (InvoiceStatus.RECEIVED.value, filename, thread_id, now, invoice_number))
        conn.commit()
        conn.close()

    def update_reminder_timestamp(self, vendor_email: str):
        """Updates the reminder timestamp for all pending invoices of a vendor."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.datetime.now()
        c.execute('''
            UPDATE invoices 
            SET last_reminder_sent_at = ?
            WHERE vendor_email = ? AND status = 'PENDING'
        ''', (now, vendor_email))
        conn.commit()
        conn.close()

    def get_vendors_needing_reminders(self, days_interval: int = 2) -> List[str]:
        """Finds vendor emails who have pending invoices AND haven't been emailed in X days."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Logic: Find Pending invoices where (Time Now - Last Reminder) > 2 days
        # OR where Last Reminder is NULL (never sent)
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_interval)
        
        c.execute('''
            SELECT DISTINCT vendor_email FROM invoices
            WHERE status = 'PENDING'
            AND (last_reminder_sent_at IS NULL OR last_reminder_sent_at < ?)
        ''', (cutoff_date,))
        
        rows = c.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_analytics_data(self):
        """Fetches raw data for the dashboard."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM invoices WHERE status = "RECEIVED"')
        rows = c.fetchall()
        conn.close()
        return [self._map_row_to_invoice(row) for row in rows]

    def get_all_invoices(self) -> List[Invoice]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM invoices')
        rows = c.fetchall()
        conn.close()
        return [self._map_row_to_invoice(row) for row in rows]

    def _map_row_to_invoice(self, row) -> Invoice:
        # Helper to map DB row to Object
        return Invoice(
            id=row['id'],
            invoice_number=row['invoice_number'],
            vendor_email=row['vendor_email'],
            amount=row['amount'],
            status=InvoiceStatus(row['status']),
            gstin=row['gstin'],
            hotel_name=row['hotel_name'],
            workspace=row['workspace'],
            thread_id=row['thread_id'],
            filename=row['filename']
        )