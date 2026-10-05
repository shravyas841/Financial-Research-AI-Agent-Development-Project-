from pathlib import Path

from pypdf import PdfReader

from services.report_service import generate_pdf_report
from test_snapshot_ai import snapshot, valid_analysis


def test_pdf_contains_verified_and_ai_sections_without_secrets(tmp_path: Path):
    pdf = generate_pdf_report(snapshot(), valid_analysis())
    output = tmp_path / "report.pdf"
    output.write_bytes(pdf.getvalue())
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    assert "Verified Financial Data" in text
    assert "AI Research Interpretation" in text
    assert "Educational research" in text or "educational research" in text
    assert "secret" not in text.lower()
