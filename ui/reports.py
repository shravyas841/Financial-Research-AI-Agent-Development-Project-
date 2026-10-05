from __future__ import annotations

import streamlit as st

from ai.schemas import AIAnalysis, ResearchSnapshot
from services.report_service import generate_pdf_report


def render_report_download(snapshot: ResearchSnapshot, analysis: AIAnalysis | None) -> None:
    pdf = generate_pdf_report(snapshot, analysis)
    st.download_button(
        "Download PDF report",
        data=pdf,
        file_name=f"{snapshot.company.symbol}_financial_research_report.pdf",
        mime="application/pdf",
    )
