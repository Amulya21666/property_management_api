import pytesseract
from PIL import Image
import re

# 🔹 Set path to Tesseract on your system
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_floorplan_details(image_path: str) -> dict:
    """
    Extracts and analyzes text from a floorplan image.
    Returns a dictionary with counts of rooms, kitchens, bathrooms, etc.
    """
    try:
        # Open the uploaded floorplan image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img).lower()

        # Count keywords
        details = {
            "rooms": len(re.findall(r"\broom\b", text)),
            "kitchens": len(re.findall(r"\bkitchen\b", text)),
            "bathrooms": len(re.findall(r"\bbathroom\b|\btoilet\b|\bwashroom\b", text)),
            "halls": len(re.findall(r"\bhall\b|\bliving\b", text)),
        }

        details["raw_text"] = text.strip()
        return details
    except Exception as e:
        return {"error": str(e)}
