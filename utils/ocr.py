from pathlib import Path


def extract_text(image_path: Path) -> str:
    """Return OCR text from an image if pytesseract is available."""
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""

    try:
        with Image.open(image_path) as img:
            text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception:
        return ""