import os
from pdf2image import convert_from_path
from src.core.interfaces import IAttachmentProcessor

class PdfAttachmentProcessor(IAttachmentProcessor):
    def convert_pdf_to_images(self, pdf_path: str) -> list[str]:
        try:
            # Convert PDF to list of PIL Images
            images = convert_from_path(pdf_path)
            image_paths = []
            base_name = os.path.splitext(pdf_path)[0]
            
            for i, image in enumerate(images):
                image_path = f"{base_name}_page_{i}.jpg"
                image.save(image_path, "JPEG")
                image_paths.append(image_path)
                
            return image_paths
        except Exception as e:
            print(f"Error converting PDF {pdf_path}: {e}")
            return []