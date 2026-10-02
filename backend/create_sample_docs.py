import os
import csv
from pathlib import Path
import docx
from pypdf import PdfWriter
import io

SAMPLE_DIR = Path(__file__).resolve().parent / "sample_data"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def create_samples():
    print("[Sample Generator] Creating synthetic sample documents...")

    # 1. TXT Document
    txt_path = SAMPLE_DIR / "project_meeting_notes.txt"
    txt_content = """Project Alpha - Sprint 14 Meeting Notes
Date: September 4, 2026
Attendees: Sarah Connor (PM), Alex Mercer (Lead Engineer), Maria Garcia (QA)

Key Discussion Points:
1. API Gateway latency has increased to 450ms due to unindexed database queries.
2. The payment service integration is delayed by 3 business days due to missing API credentials from vendor.
3. Sprint velocity fell from 42 points to 28 points.
4. Action Item: Alex will optimize PostgreSQL query indices by Thursday.
5. Action Item: Sarah will escalate third-party vendor credential issue to management.
"""
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
    print(f"Created TXT sample: {txt_path}")

    # 2. CSV Document
    csv_path = SAMPLE_DIR / "sprint_velocity_metrics.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Sprint", "Planned_Points", "Completed_Points", "Blockers_Count", "Primary_Risk"])
        writer.writerow(["Sprint 11", "40", "38", "1", "Minor scope creep"])
        writer.writerow(["Sprint 12", "45", "42", "2", "Frontend deployment pipeline failure"])
        writer.writerow(["Sprint 13", "40", "35", "3", "Database migration timeout"])
        writer.writerow(["Sprint 14", "35", "28", "5", "Unassigned payment vendor dependency & database query latency"])
    print(f"Created CSV sample: {csv_path}")

    # 3. DOCX Document
    docx_path = SAMPLE_DIR / "architecture_requirements.docx"
    doc = docx.Document()
    doc.add_heading("AI Risk Advisor Architecture Requirements", level=1)
    doc.add_paragraph(
        "The AI Risk Advisor system must process heterogeneous project documents including PDF status reports, "
        "DOCX requirements, CSV sprint metrics, and TXT meeting notes."
    )
    doc.add_heading("Security and Compliance Specs", level=2)
    doc.add_paragraph(
        "All data must be processed using local vector storage (ChromaDB) with 384-dimensional embeddings generated "
        "by SentenceTransformers. No proprietary project data shall be transmitted to external unverified endpoints."
    )
    table = doc.add_table(rows=1, cols=3)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Module'
    hdr_cells[1].text = 'SLA Target'
    hdr_cells[2].text = 'Status'
    
    row_cells = table.add_row().cells
    row_cells[0].text = 'Document Ingestion'
    row_cells[1].text = '< 500ms per file'
    row_cells[2].text = 'Operational'
    
    doc.save(str(docx_path))
    print(f"Created DOCX sample: {docx_path}")

    # 4. PDF Document using pypdf / raw stream
    pdf_path = SAMPLE_DIR / "project_status_report.pdf"
    # Create a clean simple PDF text page using reportlab or minimal PDF syntax
    # Since reportlab is not installed, we can generate a valid PDF using pypdf or minimal raw pdf
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.drawString(100, 750, "Quarterly Project Risk & Status Report")
        c.drawString(100, 720, "Executive Summary:")
        c.drawString(100, 700, "The core cloud migration project is currently facing a 2-week schedule delay.")
        c.drawString(100, 680, "Resource constraints in the DevOps team have impacted Kubernetes deployment.")
        c.drawString(100, 660, "Budget allocation has reached 82% with 30% of work remaining.")
        c.drawString(100, 640, "Mitigation Plan: Reallocate 2 senior engineers from team Bravo.")
        c.save()
        print(f"Created PDF sample with reportlab: {pdf_path}")
    except ImportError:
        # Fallback using python script or reportlab install
        pass

if __name__ == "__main__":
    create_samples()
