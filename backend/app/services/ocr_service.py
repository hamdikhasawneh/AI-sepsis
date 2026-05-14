"""
OCR Service — Extracts lab results from uploaded PDF and image documents.

Pipeline (in priority order):
1. PyMuPDF direct text extraction  — works instantly for text-based PDFs.
2. Gemini Vision API (gemini-2.0-flash) — handles scanned PDFs and images;
   send the rendered page image to Gemini and ask it to return structured
   lab values as JSON.  Requires GEMINI_API_KEY in environment / .env.
3. Regex fallback on whatever text was extracted in step 1.

The Gemini path never hangs: requests are synchronous with a 30-second
timeout enforced by the SDK's own connection settings.
"""

import os
import re
import json
import io
import base64
import logging
from typing import List, Dict, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# ── Gemini Vision setup ───────────────────────────────────────────────────────
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
_gemini_model = None

def _get_gemini_model():
    """Lazy-load a google.genai Client (only once)."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    if not GEMINI_API_KEY:
        logger.warning(
            "GEMINI_API_KEY not set — Gemini Vision OCR disabled. "
            "Add GEMINI_API_KEY=... to backend/.env and restart."
        )
        return None
    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=GEMINI_API_KEY)
        _gemini_model = client
        logger.info("Gemini client (google-genai SDK) initialised for OCR.")
        return _gemini_model
    except Exception as e:
        logger.error("Failed to initialise Gemini client: %s", e)
        return None


# ── Known lab tests (for regex fallback + status evaluation) ──────────────────
LAB_DEFINITIONS = {
    "wbc": {
        "names": [r"(?:white\s*blood\s*cell(?:\s*count)?|wbc(?:\s*count)?)"],
        "label": "White Blood Cell Count",
        "unit": "×10³/µL",
        "range": "4.5-11.0",
        "range_min": 4.5,
        "range_max": 11.0,
    },
    "lactate": {
        "names": [r"(?:serum\s*)?lactate", r"lactic\s*acid"],
        "label": "Serum Lactate",
        "unit": "mmol/L",
        "range": "0.5-2.0",
        "range_min": 0.5,
        "range_max": 2.0,
    },
    "procalcitonin": {
        "names": [r"procalcitonin|(?<!\w)pct(?!\w)"],
        "label": "Procalcitonin",
        "unit": "ng/mL",
        "range": "<0.1",
        "range_min": 0,
        "range_max": 0.1,
    },
    "crp": {
        "names": [r"c[\-\s]*reactive\s*protein|(?<!\w)crp(?!\w)"],
        "label": "C-Reactive Protein",
        "unit": "mg/L",
        "range": "<10",
        "range_min": 0,
        "range_max": 10,
    },
    "glucose": {
        "names": [r"(?:blood\s*)?glucose|blood\s*sugar|fasting\s*glucose"],
        "label": "Blood Glucose",
        "unit": "mg/dL",
        "range": "70-100",
        "range_min": 70,
        "range_max": 100,
    },
    "creatinine": {
        "names": [r"creatinine"],
        "label": "Creatinine",
        "unit": "mg/dL",
        "range": "0.6-1.2",
        "range_min": 0.6,
        "range_max": 1.2,
    },
    "hemoglobin": {
        "names": [r"h(?:a?e)?moglobin|hgb|(?<!\w)hb(?!\w)(?!\s*a1c)"],
        "label": "Hemoglobin",
        "unit": "g/dL",
        "range": "12.0-17.5",
        "range_min": 12.0,
        "range_max": 17.5,
    },
    "platelets": {
        "names": [r"platelet(?:\s*count)?|(?<!\w)plt(?!\w)"],
        "label": "Platelet Count",
        "unit": "×10³/µL",
        "range": "150-400",
        "range_min": 150,
        "range_max": 400,
    },
    "sodium": {
        "names": [r"sodium|(?<!\w)na\+(?!\w)"],
        "label": "Sodium",
        "unit": "mEq/L",
        "range": "136-145",
        "range_min": 136,
        "range_max": 145,
    },
    "potassium": {
        "names": [r"potassium|(?<!\w)k\+(?!\w)"],
        "label": "Potassium",
        "unit": "mEq/L",
        "range": "3.5-5.0",
        "range_min": 3.5,
        "range_max": 5.0,
    },
    "haematocrit": {
        "names": [r"h(?:a?e)?matocrit|(?<!\w)hct(?!\w)|(?<!\w)pcv(?!\w)"],
        "label": "Haematocrit",
        "unit": "%",
        "range": "36-50",
        "range_min": 36.0,
        "range_max": 50.0,
    },
    "erythrocytes": {
        "names": [r"erythrocytes?|red\s*blood\s*cells?|(?<!\w)rbc(?!\w)"],
        "label": "Red Blood Cell Count",
        "unit": "×10¹²/L",
        "range": "4.2-5.4",
        "range_min": 4.2,
        "range_max": 5.4,
    },
    "mcv": {
        "names": [r"mean\s*corp(?:uscular)?\s*vol(?:ume)?|(?<!\w)mcv(?!\w)"],
        "label": "MCV",
        "unit": "fL",
        "range": "80-100",
        "range_min": 80.0,
        "range_max": 100.0,
    },
    "neutrophils": {
        "names": [r"neutrophil(?:s)?"],
        "label": "Neutrophils",
        "unit": "×10³/µL",
        "range": "1.56-6.45",
        "range_min": 1.56,
        "range_max": 6.45,
    },
    "lymphocytes": {
        "names": [r"lymphocyte(?:s)?"],
        "label": "Lymphocytes",
        "unit": "×10³/µL",
        "range": "0.95-3.07",
        "range_min": 0.95,
        "range_max": 3.07,
    },
    "inr": {
        "names": [r"(?<!\w)inr(?!\w)|international\s*normalised?\s*ratio"],
        "label": "INR",
        "unit": "ratio",
        "range": "0.8-1.2",
        "range_min": 0.8,
        "range_max": 1.2,
    },
}


def _evaluate_status(value: float, range_min: float, range_max: float) -> str:
    if range_min <= value <= range_max:
        return "normal"
    if value > range_max * 1.5 or (range_min > 0 and value < range_min * 0.5):
        return "critical"
    return "high"


# ── Gemini Vision OCR ─────────────────────────────────────────────────────────

_GEMINI_PROMPT = """You are a medical lab report parser.
Examine this lab report image and extract ALL lab test results you can find.

Return ONLY a valid JSON array — no markdown, no explanation, no code fences.
Each element must have exactly these keys:
  "test_name"       : full name of the test (e.g. "White Blood Cell Count")
  "value"           : numeric result as a number (not a string)
  "unit"            : unit string as shown (e.g. "g/dL", "mmol/L", "×10³/µL")
  "reference_range" : reference range as shown (e.g. "4.5-11.0", "<10")
  "status"          : one of "normal", "high", "low", or "critical"

If a test result is flagged as abnormal (e.g. shown in red, marked H/L/!),
use "high", "low", or "critical" for status.  Otherwise use "normal".

Example output:
[
  {"test_name": "Hemoglobin", "value": 16.9, "unit": "g/dL", "reference_range": "13.2-16.6", "status": "high"},
  {"test_name": "White Blood Cell Count", "value": 5.6, "unit": "×10³/µL", "reference_range": "4.5-11.0", "status": "normal"}
]

Return [] if no lab values are visible.
"""


def _image_bytes_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# Models tried in order — flash-lite is cheapest (free tier); 2.5-flash as fallback.
_GEMINI_MODELS = [
    "models/gemini-2.0-flash-lite",
    "models/gemini-2.0-flash",
    "models/gemini-2.5-flash",
]


def _ocr_page_with_gemini(image_bytes: bytes) -> List[Dict]:
    """Send one page image to Gemini and return parsed lab results.
    Tries each model in _GEMINI_MODELS until one succeeds.
    """
    client = _get_gemini_model()
    if client is None:
        return []

    from google.genai import types as genai_types

    image_part = genai_types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/png",
    )

    for model_name in _GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[_GEMINI_PROMPT, image_part],
                config=genai_types.GenerateContentConfig(temperature=0),
            )
            raw = response.text.strip()

            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            labs = json.loads(raw)
            if not isinstance(labs, list):
                return []

            results = []
            for lab in labs:
                try:
                    results.append({
                        "test_name":       str(lab["test_name"]),
                        "value":           float(lab["value"]),
                        "unit":            str(lab.get("unit", "")),
                        "reference_range": str(lab.get("reference_range", "")),
                        "status":          str(lab.get("status", "normal")).lower(),
                    })
                except (KeyError, ValueError, TypeError):
                    continue

            logger.info(
                "Gemini model %s returned %d lab results.", model_name, len(results)
            )
            return results

        except json.JSONDecodeError as e:
            logger.error("Gemini (%s) response was not valid JSON: %s", model_name, e)
            return []
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                logger.warning(
                    "Gemini model %s quota exceeded — trying next model.", model_name
                )
                continue  # Try next model
            logger.error("Gemini OCR call failed (%s): %s", model_name, e)
            return []

    logger.error("All Gemini models exceeded quota. OCR not available.")
    return []


# ── File → page images ────────────────────────────────────────────────────────


def _pdf_to_page_images(file_path: str) -> List[bytes]:
    """Render every PDF page as a 150-DPI PNG, return list of raw bytes."""
    doc = fitz.open(file_path)
    images = []
    mat = fitz.Matrix(150 / 72, 150 / 72)  # 150 DPI — enough for Gemini, smaller payload
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def _image_file_to_bytes(file_path: str) -> bytes:
    """Read an image file and return its bytes (PNG/JPG/JPEG etc.)."""
    with open(file_path, "rb") as f:
        return f.read()


# ── Regex fallback ────────────────────────────────────────────────────────────

def _parse_lab_results_regex(text: str) -> List[Dict]:
    """Regex-based parser — used as a fallback when Gemini is not available."""
    results: List[Dict] = []
    found_keys: set = set()
    num_pattern = re.compile(r"(\d+\.?\d*)")

    for key, defn in LAB_DEFINITIONS.items():
        if key in found_keys:
            continue
        for name_pattern in defn["names"]:
            name_match = re.search(name_pattern, text, re.IGNORECASE)
            if not name_match:
                continue
            window = text[name_match.end(): name_match.end() + 80]
            num_match = num_pattern.search(window)
            if num_match:
                try:
                    value = float(num_match.group(1))
                    if value > 10_000:
                        continue
                    status = _evaluate_status(value, defn["range_min"], defn["range_max"])
                    results.append({
                        "test_name":       defn["label"],
                        "value":           value,
                        "unit":            defn["unit"],
                        "reference_range": defn["range"],
                        "status":          status,
                    })
                    found_keys.add(key)
                    break
                except (ValueError, IndexError):
                    continue

    return results


# ── Public entry point ────────────────────────────────────────────────────────

def process_pdf(file_path: str) -> Dict:
    """
    Full pipeline for PDF and image files:

    1. For text-based PDFs: direct PyMuPDF extraction + regex parsing.
       (Fast, no API needed — covers most hospital e-reports.)

    2. For scanned PDFs and image files (PNG/JPG/etc.):
       render each page → send to Gemini Vision → structured JSON back.
       Falls back to regex on the extracted text if Gemini is unavailable.

    Returns:
        {
            "extracted_text": str,
            "lab_results": [{ test_name, value, unit, reference_range, status }, ...]
        }
    """
    ext = os.path.splitext(file_path)[1].lower()
    is_image = ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")

    # ── Step 1: Try direct text extraction (PDF only) ─────────────────────────
    extracted_text = ""
    if not is_image:
        try:
            doc = fitz.open(file_path)
            for page in doc:
                extracted_text += page.get_text("text") + "\n"
            doc.close()
            extracted_text = extracted_text.strip()
        except Exception as e:
            logger.warning("PyMuPDF text extraction failed: %s", e)

    # If we got good text, try regex first (fast + free)
    if len(extracted_text) > 50:
        logger.info("Text-based PDF — running regex parser on %d chars.", len(extracted_text))
        regex_results = _parse_lab_results_regex(extracted_text)
        if regex_results:
            logger.info("Regex parser found %d results.", len(regex_results))
            return {"extracted_text": extracted_text, "lab_results": regex_results}
        logger.info("Regex found 0 results — falling through to Gemini Vision.")

    # ── Step 2: Gemini Vision (scanned PDF or image) ──────────────────────────
    model = _get_gemini_model()
    if model:
        try:
            all_lab_results: List[Dict] = []

            if is_image:
                image_bytes = _image_file_to_bytes(file_path)
                all_lab_results = _ocr_page_with_gemini(image_bytes)
            else:
                # Render PDF pages to images and OCR each page
                page_images = _pdf_to_page_images(file_path)
                for page_bytes in page_images:
                    page_results = _ocr_page_with_gemini(page_bytes)
                    # Merge — keep first occurrence of each test name
                    existing_names = {r["test_name"].lower() for r in all_lab_results}
                    for r in page_results:
                        if r["test_name"].lower() not in existing_names:
                            all_lab_results.append(r)
                            existing_names.add(r["test_name"].lower())

            if all_lab_results:
                logger.info("Gemini Vision extracted %d lab results total.", len(all_lab_results))
                return {"extracted_text": extracted_text, "lab_results": all_lab_results}

        except Exception as e:
            logger.error("Gemini Vision pipeline failed: %s", e)

    # ── Step 3: Regex on whatever text we have ────────────────────────────────
    if extracted_text:
        regex_results = _parse_lab_results_regex(extracted_text)
        return {"extracted_text": extracted_text, "lab_results": regex_results}

    logger.warning(
        "No text extracted and Gemini not available. "
        "Add GEMINI_API_KEY=... to backend/.env to enable image OCR."
    )
    return {"extracted_text": "", "lab_results": []}
