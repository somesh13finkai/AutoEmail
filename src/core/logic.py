from typing import List
from difflib import SequenceMatcher
from src.models import Invoice, ReconciliationResult, InvoiceStatus

class ReconciliationService:
    """
    Business Logic with Fuzzy Matching & Suffix Heuristics.
    """
    
    @staticmethod
    def _is_match(expected_id: str, extracted_id: str) -> bool:
        """
        Determines if two ID strings match using strict, fuzzy, or partial logic.
        """
        # 1. Strict Match (Fastest)
        if expected_id == extracted_id:
            return True
            
        # 2. Normalization
        # Remove common separators and normalize 1/I, 0/O
        def normalize(s):
            return s.upper().replace("1", "I").replace("0", "O").replace(" ", "").replace("-", "").replace("_", "")
            
        s1 = normalize(expected_id)
        s2 = normalize(extracted_id)
        
        if s1 == s2:
            return True

        # 3. Suffix Match (The "Anti-Noise" Fix)
        # If the invoice number is long (>8 chars) and the last 6 chars are identical,
        # it's extremely likely to be the same invoice, just with OCR noise at the start.
        # Example: 'FI18HL...' vs 'H18HL...' -> Both end in '000150'
        if len(s1) > 8 and len(s2) > 8:
            if s1[-6:] == s2[-6:]:
                # Optional: Ensure the rest isn't totally different (length check)
                if abs(len(s1) - len(s2)) < 4: 
                    return True

        # 4. Fuzzy Similarity (Levenshtein Ratio)
        # We lowered the threshold to 0.70 (70%) to catch cases like missing 1 char ('H29' vs 'H2')
        similarity = SequenceMatcher(None, s1, s2).ratio()
        
        if len(s1) > 8 and similarity > 0.70:
            return True
            
        return False

    @staticmethod
    def reconcile(expected_invoices: List[Invoice], extracted_numbers: List[str]) -> ReconciliationResult:
        expected_map = {inv.invoice_number: inv for inv in expected_invoices}
        
        received_numbers = []
        updated_invoices = []
        
        for extracted_id in extracted_numbers:
            # Check against every EXPECTED invoice
            for expected_id, inv in expected_map.items():
                if ReconciliationService._is_match(expected_id, extracted_id):
                    # Check if we already matched this one (avoid duplicates)
                    if expected_id not in received_numbers:
                        received_numbers.append(expected_id)
                        inv.status = InvoiceStatus.RECEIVED
                        updated_invoices.append(inv)
                    break 

        received_set = set(received_numbers)
        missing_numbers = [
            inv.invoice_number 
            for inv in expected_invoices 
            if inv.invoice_number not in received_set
        ]

        return ReconciliationResult(
            received_invoices=received_numbers,
            missing_invoices=missing_numbers,
            updated_invoices=updated_invoices
        )