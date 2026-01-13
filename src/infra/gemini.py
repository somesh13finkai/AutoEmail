import os
import json
import ast
from typing import List
from PIL import Image
from google import genai 
from google.genai import types

from src.core.interfaces import ILLMProvider
from src.models import ExtractedInvoiceData

class GeminiLLMProvider(ILLMProvider):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.0-flash"

    def _clean_json_markdown(self, text: str) -> str:
        """Helper to strip markdown code blocks from LLM response."""
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return text.strip()

    def extract_invoice_data(self, text_context: str, image_paths: List[str]) -> ExtractedInvoiceData:
        images = []
        for path in image_paths:
            try:
                img = Image.open(path)
                images.append(img)
            except Exception as e:
                print(f"Error loading image {path}: {e}")

        # --- GENERIC, ROBUST PROMPT ---
        # No hard-coded ID fixes. We rely on general OCR principles.
        prompt = f"""
        Analyze the attached invoice images.
        
        CONTEXT: "{text_context}"
        
        Task: Extract the Invoice Number, Amount, GSTIN, Hotel Name, and Workspace.
        
        GUIDELINES FOR INVOICE NUMBERS:
        1. Look for labels like "Invoice No", "Bill No", "Folio No".
        2. Invoice numbers are usually alphanumeric.
        3. Common OCR corrections to apply contextually:
           - Distinguish '1' (one) from 'I' (India) based on surrounding letters/numbers.
           - Distinguish '0' (zero) from 'O' (Oscar).
           - Distinguish '5' from 'S'.
           - Distinguish '8' from 'B'.
        4. Return the exact characters you see, correcting only obvious OCR font artifacts.
        
        Return JSON format only:
        {{
            "invoice_numbers": ["cleaned_id"],
            "amounts": [1234.50],
            "gstins": ["number"],
            "hotel_names": ["name"],
            "workspaces": ["name"],
            "detected_poc_change": false,
            "new_poc_details": null
        }}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt] + images 
            )
            
            clean_json = self._clean_json_markdown(response.text)
            try:
                data = json.loads(clean_json)
            except json.JSONDecodeError:
                data = ast.literal_eval(clean_json)

            return ExtractedInvoiceData(
                invoice_numbers=data.get("invoice_numbers", []),
                detected_poc_change=data.get("detected_poc_change", False),
                new_poc_details=data.get("new_poc_details"),
                amounts=data.get("amounts", []),
                gstins=data.get("gstins", []),
                hotel_names=data.get("hotel_names", []),
                workspaces=data.get("workspaces", [])
            )

        except Exception as e:
            print(f"LLM Vision Extraction Error: {e}")
            return ExtractedInvoiceData([], False, None)

    def draft_reply(self, sender: str, missing_invoices: List[str], received_invoices: List[str], context: str) -> str:
        prompt = f"""
        You are a helpful accounts payable assistant. Draft a reply email to {sender}.
        
        Scenario:
        - We just received these invoices: {', '.join(received_invoices)}
        - We are STILL MISSING these: {', '.join(missing_invoices)}
        - Context: {context}
        
        Rules:
        1. Thank them for the specific invoices received.
        2. Politely ask for the missing ones.
        3. Do NOT ask for the ones we already received.
        4. Keep it professional.
        """
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text