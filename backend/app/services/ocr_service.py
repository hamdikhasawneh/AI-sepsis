"""
OCR Service — Extracts lab results from uploaded PDF documents.

Supports two extraction modes:
1. Text-based PDFs: Uses PyMuPDF (fitz) to directly extract embedded text.
2. Scanned/image PDFs: Converts pages to images, then uses Tesseract OCR via pytesseract.

After text extraction, regex-based parsing identifies lab test names, numeric values,
units, and reference ranges. Results are auto-evaluated against known reference ranges.
"""

import re
import os
import logging
from typing import List, Dict, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Auto-detect Tesseract path on Windows
_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
for _tess_path in _TESSERACT_PATHS:
    if os.path.exists(_tess_path):
        os.environ["TESSERACT_CMD"] = _tess_path
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = _tess_path
            logger.info("Tesseract found at: %s", _tess_path)
        except ImportError:
            pass
        break

# ── Known lab tests with their expected units and reference ranges ──
LAB_DEFINITIONS = {
    "wbc": {
        "names": [
            r"(?:white\s*blood\s*cell(?:\s*count)?|wbc(?:\s*count)?)",
        ],
        "label": "White Blood Cell Count",
        "unit": "×10³/µL",
        "range": "4.5-11.0",
        "range_min": 4.5,
        "range_max": 11.0,
    },
    "lactate": {
        "names": [
            r"(?:serum\s*)?lactate",
            r"lactic\s*acid",
        ],
        "label": "Serum Lactate",
        "unit": "mmol/L",
        "range": "0.5-2.0",
        "range_min": 0.5,
        "range_max": 2.0,
    },
    "procalcitonin": {
        "names": [
            r"procalcitonin|pct",
        ],
        "label": "Procalcitonin",
        "unit": "ng/mL",
        "range": "<0.1",
        "range_min": 0,
        "range_max": 0.1,
    },
    "crp": {
        "names": [
            r"c[\-\s]*reactive\s*protein|crp",
        ],
        "label": "C-Reactive Protein",
        "unit": "mg/L",
        "range": "<10",
        "range_min": 0,
        "range_max": 10,
    },
    "glucose": {
        "names": [
            r"(?:blood\s*)?glucose|blood\s*sugar|fasting\s*glucose",
        ],
        "label": "Blood Glucose",
        "unit": "mg/dL",
        "range": "70-100",
        "range_min": 70,
        "range_max": 100,
    },
    "creatinine": {
        "names": [
            r"creatinine",
        ],
        "label": "Creatinine",
        "unit": "mg/dL",
        "range": "0.6-1.2",
        "range_min": 0.6,
        "range_max": 1.2,
    },
    "hemoglobin": {
        "names": [
            r"hemoglobin|haemoglobin|hgb|hb(?!\s*a1c)",
        ],
        "label": "Hemoglobin",
        "unit": "g/dL",
        "range": "12.0-17.5",
        "range_min": 12.0,
        "range_max": 17.5,
    },
    "platelets": {
        "names": [
            r"platelet(?:\s*count)?|plt",
        ],
        "label": "Platelet Count",
        "unit": "×10³/µL",
        "range": "150-400",
        "range_min": 150,
        "range_max": 400,
    },
    "sodium": {
        "names": [
            r"sodium|(?<!\w)na\+(?!\w)",
        ],
        "label": "Sodium",
        "unit": "mEq/L",
        "range": "136-145",
        "range_min": 136,
        "range_max": 145,
    },
    "potassium": {
        "names": [
            r"potassium|k\+",
        ],
        "label": "Potassium",
        "unit": "mEq/L",
        "range": "3.5-5.0",
        "range_min": 3.5,
        "range_max": 5.0,
    },
}

# Regex to capture a numeric value (e.g. 14.5, 185, 0.08) near a test name.
# Handles values on the same line (separated by whitespace/colon/tabs) or the next line.
# The [^a-z]{0,30} limits the gap to prevent over-matching across distant text.
_VALUE_PATTERN = r"(?:[^a-z\d]{0,30})(\d+\.?\d*)"


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file. Tries direct text extraction first (text-based PDFs).
    If little/no text is found, falls back to OCR via Tesseract (scanned/image PDFs).
    """
    doc = fitz.open(file_path)
    full_text = ""

    # Pass 1: Try direct text extraction (fast, works for text-based PDFs)
    for page in doc:
        page_text = page.get_text("text")
        if page_text:
            full_text += page_text + "\n"

    # If we got meaningful text (more than just whitespace/headers), return it
    stripped = full_text.strip()
    if len(stripped) > 50:
        doc.close()
        logger.info("PDF text extraction succeeded (text-based PDF), length=%d", len(stripped))
        return stripped

    # Pass 2: Fall back to OCR for scanned/image PDFs
    logger.info("Minimal text found in PDF, attempting OCR via Tesseract...")
    try:
        import pytesseract
        from PIL import Image
        import io

        ocr_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render page at 300 DPI for better OCR accuracy
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            page_ocr = pytesseract.image_to_string(img)
            ocr_text += page_ocr + "\n"

        doc.close()
        ocr_stripped = ocr_text.strip()
        logger.info("OCR extraction completed, length=%d", len(ocr_stripped))
        return ocr_stripped if ocr_stripped else stripped  # Fall back to whatever we had

    except ImportError:
        doc.close()
        logger.warning("pytesseract or Pillow not available — OCR skipped for scanned PDF")
        return stripped
    except Exception as e:
        doc.close()
        logger.warning("OCR failed: %s — returning text extraction result", str(e))
        return stripped


def _evaluate_status(value: float, range_min: float, range_max: float) -> str:
    """Evaluate whether a lab value is normal, high, or critical."""
    if range_min <= value <= range_max:
        return "normal"
    # Critical: value exceeds 1.5x the max or below 0.5x the min
    if value > range_max * 1.5 or (range_min > 0 and value < range_min * 0.5):
        return "critical"
    return "high"


def parse_lab_results(text: str) -> List[Dict]:
    """
    Parse extracted text to identify lab test results.

    Uses a two-step approach:
    1. Find the test name in the text.
    2. From that position, scan the next ~80 characters for the first numeric value.

    Returns a list of dicts, each with:
        - test_name: str
        - value: float
        - unit: str
        - reference_range: str
        - status: str (normal/high/critical)
    """
    results = []
    found_keys = set()
    num_pattern = re.compile(r"(\d+\.?\d*)")

    for key, defn in LAB_DEFINITIONS.items():
        if key in found_keys:
            continue

        for name_pattern in defn["names"]:
            # Step 1: Find the test name
            name_match = re.search(name_pattern, text, re.IGNORECASE)
            if not name_match:
                continue

            # Step 2: Look for the first number after the test name
            # Scan up to 80 chars ahead (handles "(WBC)\n14.5" style layouts)
            search_start = name_match.end()
            search_window = text[search_start:search_start + 80]
            num_match = num_pattern.search(search_window)

            if num_match:
                try:
                    value = float(num_match.group(1))
                    # Skip values that look like dates/IDs (very large numbers)
                    if value > 10000:
                        continue
                    status = _evaluate_status(value, defn["range_min"], defn["range_max"])
                    results.append({
                        "test_name": defn["label"],
                        "value": value,
                        "unit": defn["unit"],
                        "reference_range": defn["range"],
                        "status": status,
                    })
                    found_keys.add(key)
                    logger.info("Parsed %s = %s %s (%s)", defn["label"], value, defn["unit"], status)
                    break
                except (ValueError, IndexError):
                    continue

    logger.info("Total lab results parsed from PDF: %d", len(results))
    return results


def process_pdf(file_path: str) -> Dict:
    """
    Full pipeline: extract text from PDF → parse lab results.

    Returns:
        {
            "extracted_text": str,
            "lab_results": [{ test_name, value, unit, reference_range, status }, ...]
        }
    """
    text = extract_text_from_pdf(file_path)
    lab_results = parse_lab_results(text)
    return {
        "extracted_text": text,
        "lab_results": lab_results,
    }
