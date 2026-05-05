"""
Generate a sample lab report PDF for testing the OCR pipeline.
"""
import fitz  # PyMuPDF

def create_sample_lab_pdf(output_path: str):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size
    
    # Title
    page.insert_text((50, 60), "LABORATORY REPORT", fontsize=18, fontname="helv")
    page.insert_text((50, 85), "Jordan University Hospital — Clinical Lab", fontsize=10, fontname="helv")
    page.insert_text((50, 100), "Date: 2026-05-05   Patient: Sarah Mitchell (P-1001)", fontsize=10, fontname="helv")
    page.insert_text((50, 115), "-" * 80, fontsize=8, fontname="helv")
    
    # Lab results
    results = [
        ("White Blood Cell Count (WBC)", "14.5", "×10³/µL", "4.5-11.0"),
        ("Serum Lactate", "3.8", "mmol/L", "0.5-2.0"),
        ("Procalcitonin (PCT)", "6.2", "ng/mL", "<0.1"),
        ("C-Reactive Protein (CRP)", "145", "mg/L", "<10"),
        ("Blood Glucose", "155", "mg/dL", "70-100"),
        ("Creatinine", "1.9", "mg/dL", "0.6-1.2"),
        ("Hemoglobin", "10.8", "g/dL", "12.0-17.5"),
        ("Platelet Count", "105", "×10³/µL", "150-400"),
        ("Sodium", "139", "mEq/L", "136-145"),
        ("Potassium", "4.3", "mEq/L", "3.5-5.0"),
    ]
    
    y = 145
    # Header row
    page.insert_text((50, y), "Test Name", fontsize=10, fontname="helv")
    page.insert_text((280, y), "Value", fontsize=10, fontname="helv")
    page.insert_text((350, y), "Unit", fontsize=10, fontname="helv")
    page.insert_text((440, y), "Ref Range", fontsize=10, fontname="helv")
    y += 5
    page.insert_text((50, y), "-" * 80, fontsize=8, fontname="helv")
    y += 18
    
    for test, value, unit, ref in results:
        page.insert_text((50, y), test, fontsize=9, fontname="helv")
        page.insert_text((280, y), value, fontsize=9, fontname="helv")
        page.insert_text((350, y), unit, fontsize=9, fontname="helv")
        page.insert_text((440, y), ref, fontsize=9, fontname="helv")
        y += 20
    
    y += 20
    page.insert_text((50, y), "Authorized by: Dr. A. Hassan, Clinical Pathologist", fontsize=9, fontname="helv")
    
    doc.save(output_path)
    doc.close()
    print(f"Sample lab PDF created: {output_path}")

if __name__ == "__main__":
    create_sample_lab_pdf("sample_lab_report.pdf")
