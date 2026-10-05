from __future__ import annotations

import io
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ai.schemas import AIAnalysis, ResearchSnapshot
from utils.formatting import format_number


def _rows(values: dict[str, object]) -> list[list[str]]:
    return [[label, "Unavailable" if value is None else str(value)] for label, value in values.items()]


def generate_pdf_report(snapshot: ResearchSnapshot, analysis: AIAnalysis | None = None) -> io.BytesIO:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Financial Research Report - {snapshot.company.symbol}",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER, spaceAfter=14))
    story = [Paragraph(f"Financial Research Report — {escape(snapshot.company.symbol)}", styles["ReportTitle"])]

    def section(title: str, values: dict[str, object]) -> None:
        story.extend([Paragraph(title, styles["Heading2"]), Table(_rows(values), colWidths=[60 * mm, 95 * mm], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF7")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ])), Spacer(1, 8)])

    story.append(Paragraph("Verified Financial Data", styles["Heading1"]))
    section("Company Overview", {
        "Name": snapshot.company.name,
        "Symbol": snapshot.company.symbol,
        "Sector": snapshot.company.sector,
        "Industry": snapshot.company.industry,
    })
    section("Market Data", {
        "Current price": format_number(snapshot.market.current_price),
        "Daily change": format_number(snapshot.market.daily_change_pct, suffix="%"),
        "Period return": format_number(snapshot.market.period_return_pct, suffix="%"),
    })
    section("Technical Analysis", {
        "RSI (14)": format_number(snapshot.technical.rsi_14),
        "SMA (20)": format_number(snapshot.technical.sma_20),
        "SMA (50)": format_number(snapshot.technical.sma_50),
        "MACD": format_number(snapshot.technical.macd),
        "MACD signal": format_number(snapshot.technical.macd_signal),
        "Bollinger upper": format_number(snapshot.technical.bollinger_upper),
        "Bollinger lower": format_number(snapshot.technical.bollinger_lower),
    })
    section("Fundamental Analysis", {
        "P/E": format_number(snapshot.fundamentals.pe_ratio),
        "P/B": format_number(snapshot.fundamentals.pb_ratio),
        "Debt/equity": format_number(snapshot.fundamentals.debt_to_equity),
        "Market cap": format_number(snapshot.fundamentals.market_cap, 0),
        "Revenue growth": format_number(snapshot.fundamentals.revenue_growth, suffix=" (decimal)"),
        "Profit margin": format_number(snapshot.fundamentals.profit_margin, suffix=" (decimal)"),
    })
    section("Risk Analysis", {
        "Annualized volatility": format_number(snapshot.risk.volatility_pct, suffix="%"),
        "Maximum drawdown": format_number(snapshot.risk.max_drawdown_pct, suffix="%"),
        "Sharpe ratio (0% risk-free assumption)": format_number(snapshot.risk.sharpe_ratio),
        "Beta vs NIFTY 50": format_number(snapshot.risk.beta),
    })
    section("News Sentiment", {
        "Articles": snapshot.sentiment.article_count,
        "Average TextBlob polarity": format_number(snapshot.sentiment.average_score),
        "Positive / neutral / negative": f"{snapshot.sentiment.positive} / {snapshot.sentiment.neutral} / {snapshot.sentiment.negative}",
    })

    if analysis:
        story.extend([PageBreak(), Paragraph("AI Research Interpretation", styles["Heading1"])])
        for title, text in [
            ("Summary", analysis.summary),
            ("Technical interpretation", analysis.technical_analysis),
            ("Fundamental interpretation", analysis.fundamental_analysis),
            ("Sentiment interpretation", analysis.sentiment_analysis),
            ("Risk interpretation", analysis.risk_analysis),
        ]:
            story.extend([Paragraph(title, styles["Heading2"]), Paragraph(escape(text), styles["BodyText"]), Spacer(1, 6)])
        story.append(Paragraph("Key observations", styles["Heading2"]))
        for item in analysis.key_observations:
            story.append(Paragraph(f"• {escape(item)}", styles["BodyText"]))
        story.append(Paragraph("Limitations", styles["Heading2"]))
        for item in analysis.limitations:
            story.append(Paragraph(f"• {escape(item)}", styles["BodyText"]))

    story.extend([
        Spacer(1, 12),
        Paragraph("Sources, Freshness and Methodology", styles["Heading1"]),
        Paragraph(escape(snapshot.metadata.methodology), styles["BodyText"]),
        Paragraph(f"Market source: {escape(snapshot.metadata.market_data_source)}", styles["BodyText"]),
        Paragraph(f"News source: {escape(snapshot.metadata.news_source or 'Unavailable')}", styles["BodyText"]),
        Paragraph(f"Retrieved: {snapshot.metadata.generated_at.isoformat()}", styles["BodyText"]),
        Paragraph(f"Analysis period: {escape(snapshot.metadata.analysis_period)}", styles["BodyText"]),
        Paragraph("Limitations and Disclaimer", styles["Heading1"]),
        Paragraph(
            "Data may be delayed, incomplete, or unavailable. Sentiment is descriptive and does not predict price movement. "
            "AI text interprets only the supplied snapshot. This report is for educational research and is not personalized investment advice.",
            styles["BodyText"],
        ),
    ])
    document.build(story)
    buffer.seek(0)
    return buffer
