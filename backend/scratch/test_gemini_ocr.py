import os, json
os.environ['GEMINI_API_KEY'] = 'AIzaSyAcwVLVt4ub-GV1APXbZQ_1YQiSDMjRvsI'

from app.services.ocr_service import _pdf_to_page_images, _ocr_page_with_gemini, process_pdf, _get_gemini_model

client = _get_gemini_model()
print("Gemini client:", client is not None)

# Force Gemini Vision path by rendering a page and calling Gemini directly
pages = _pdf_to_page_images('sample_lab_report.pdf')
print("PDF pages rendered:", len(pages))

labs = _ocr_page_with_gemini(pages[0])
print("Labs from Gemini Vision:", len(labs))
print(json.dumps(labs, indent=2, ensure_ascii=False))
