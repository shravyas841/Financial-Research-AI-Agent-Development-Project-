import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from textblob import TextBlob
import requests
import sqlite3
from sqlite3 import Connection
from datetime import datetime, time as dtime
from dateutil.relativedelta import relativedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import os

# =========================
# BASIC CONFIG / CONSTANTS
# =========================

# 👉 Put your NewsAPI key here (or leave None and the app will disable news)
NEWS_API_KEY = ""  # e.g. "abcd1234..." from https://newsapi.org

INDIAN_MARKET_OPEN = dtime(9, 15)
INDIAN_MARKET_CLOSE = dtime(15, 30)

DB_PATH = "financial_agent.db"


# =========================
# UTILS
# =========================

def get_indian_time_now():
    """Return current time in IST (approx, without external libs)."""
    # Streamlit/host will generally run in local time; for your laptop (India) this is okay.
    # If you deploy somewhere else, you can adjust UTC + 5:30 here manually.
    return datetime.now()


def is_market_open(now: datetime = None):
    """Check if Indian market is open based on time and weekday."""
    if now is None:
        now = get_indian_time_now()
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False, "Market is closed (Weekend)."
    current_t = now.time()
    if current_t < INDIAN_MARKET_OPEN or current_t > INDIAN_MARKET_CLOSE:
        return False, "Market is currently closed (Outside trading hours 9:15–15:30 IST)."
    return True, "Market is open."


def validate_symbol(symbol: str):
    """Basic validation for stock symbol."""
    if not symbol:
        return False, "Stock symbol cannot be empty."
    if " " in symbol:
        return False, "Stock symbol should not contain spaces."
    return True, ""


def make_full_symbol(base_symbol: str, exchange: str):
    """Attach .NS / .BO suffix for NSE/BSE."""
    base_symbol = base_symbol.strip().upper()
    if exchange == "NSE (.NS)":
        return base_symbol + ".NS"
    elif exchange == "BSE (.BO)":
        return base_symbol + ".BO"
    return base_symbol


# =========================
# DATA ACCESS: YFINANCE
# =========================

@st.cache_data(show_spinner=False)
def get_stock_history(symbol: str, period: str = "6mo", interval: str = "1d"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        df = df.reset_index()
        df.rename(columns={"Date": "date"}, inplace=True)
        return df
    except Exception as e:
        st.error(f"Error fetching stock data: {e}")
        return None


@st.cache_data(show_spinner=False)
def get_stock_info(symbol: str):
    """Fetch basic info and fundamentals using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return info
    except Exception as e:
        st.error(f"Error fetching stock info: {e}")
        return None


# =========================
# TECHNICAL INDICATORS
# =========================

def compute_rsi(series: pd.Series, period: int = 14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    gain = pd.Series(gain).rolling(window=period).mean()
    loss = pd.Series(loss).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def add_indicators(df: pd.DataFrame):
    df = df.copy()
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA50"] = df["Close"].rolling(window=50).mean()

    # MACD
    exp1 = df["Close"].ewm(span=12, adjust=False).mean()
    exp2 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # RSI
    df["RSI"] = compute_rsi(df["Close"], period=14)

    return df


def plot_price_chart(df: pd.DataFrame, symbol: str):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    ))

    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["MA20"],
        mode="lines",
        name="MA20"
    ))
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["MA50"],
        mode="lines",
        name="MA50"
    ))

    fig.update_layout(
        title=f"{symbol} Price with Moving Averages",
        xaxis_title="Date",
        yaxis_title="Price (₹ approx)",
        xaxis_rangeslider_visible=False,
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # MACD and RSI
    macd_fig = go.Figure()
    macd_fig.add_trace(go.Scatter(x=df["date"], y=df["MACD"], mode="lines", name="MACD"))
    macd_fig.add_trace(go.Scatter(x=df["date"], y=df["Signal"], mode="lines", name="Signal"))
    macd_fig.update_layout(
        title="MACD Indicator",
        xaxis_title="Date",
        yaxis_title="MACD"
    )
    st.plotly_chart(macd_fig, use_container_width=True)

    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(x=df["date"], y=df["RSI"], mode="lines", name="RSI"))
    rsi_fig.update_layout(
        title="RSI (14-day)",
        xaxis_title="Date",
        yaxis_title="RSI"
    )
    st.plotly_chart(rsi_fig, use_container_width=True)


# =========================
# NEWS + SENTIMENT
# =========================

@st.cache_data(show_spinner=False)
def fetch_news(query: str, api_key: str, page_size: int = 10):
    if not api_key:
        return []
    url = (
        "https://newsapi.org/v2/everything?"
        f"q={query}&language=en&sortBy=publishedAt&pageSize={page_size}&apiKey={api_key}"
    )
    try:
        resp = requests.get(url)
        data = resp.json()
        if data.get("status") != "ok":
            return []
        return data.get("articles", [])
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []


def sentiment_label(polarity: float):
    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    else:
        return "Neutral"


def analyze_article_sentiment(article):
    title = article.get("title", "")
    desc = article.get("description", "") or ""
    text = title + " " + desc
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    label = sentiment_label(polarity)
    return polarity, label


# =========================
# DATABASE (WATCHLIST + PORTFOLIO)
# =========================

def get_connection() -> Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            symbol TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            symbol TEXT,
            shares REAL,
            avg_price REAL,
            PRIMARY KEY (symbol)
        )
    """)
    conn.commit()
    conn.close()


def add_to_watchlist(symbol: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO watchlist(symbol) VALUES (?)", (symbol,))
    conn.commit()
    conn.close()


def remove_from_watchlist(symbol: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()


def get_watchlist():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def upsert_portfolio(symbol: str, shares: float, avg_price: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO portfolio(symbol, shares, avg_price)
        VALUES (?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            shares = excluded.shares,
            avg_price = excluded.avg_price
    """, (symbol, shares, avg_price))
    conn.commit()
    conn.close()


def get_portfolio():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol, shares, avg_price FROM portfolio")
    rows = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(rows, columns=["Symbol", "Shares", "Avg Buy Price"])
    return df


def delete_portfolio_symbol(symbol: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio WHERE symbol = ?", (symbol,))
    conn.commit()
    conn.close()


def compute_portfolio_valuation(df_portfolio: pd.DataFrame):
    records = []
    total_value = 0.0
    total_invested = 0.0

    for _, row in df_portfolio.iterrows():
        symbol = row["Symbol"]
        shares = row["Shares"]
        avg_price = row["Avg Buy Price"]

        hist = get_stock_history(symbol, period="5d")
        if hist is None or hist.empty:
            current_price = np.nan
        else:
            current_price = hist["Close"].iloc[-1]

        invested = shares * avg_price
        value = shares * (current_price if not np.isnan(current_price) else 0.0)
        pnl = value - invested

        total_value += value
        total_invested += invested

        records.append({
            "Symbol": symbol,
            "Shares": shares,
            "Avg Buy Price": avg_price,
            "Current Price": current_price,
            "Invested (₹)": invested,
            "Current Value (₹)": value,
            "PnL (₹)": pnl
        })

    if records:
        df = pd.DataFrame(records)
    else:
        df = pd.DataFrame(columns=[
            "Symbol", "Shares", "Avg Buy Price", "Current Price",
            "Invested (₹)", "Current Value (₹)", "PnL (₹)"
        ])

    return df, total_invested, total_value


# =========================
# EXPORT REPORT (PDF)
# =========================

def generate_pdf_report(symbol: str, df_price: pd.DataFrame, info: dict, df_portfolio_summary: pd.DataFrame = None):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"Financial Research Report - {symbol}")

    c.setFont("Helvetica", 10)
    y = height - 80

    # Basic info
    if info:
        lines = [
            f"Company: {info.get('shortName', 'N/A')}",
            f"Sector: {info.get('sector', 'N/A')}",
            f"Industry: {info.get('industry', 'N/A')}",
            f"Market Cap: {info.get('marketCap', 'N/A')}",
            f"PE Ratio (TTM): {info.get('trailingPE', 'N/A')}",
            f"52 Week High: {info.get('fiftyTwoWeekHigh', 'N/A')}",
            f"52 Week Low: {info.get('fiftyTwoWeekLow', 'N/A')}",
        ]
        for line in lines:
            c.drawString(50, y, line)
            y -= 15

    # Price summary
    if df_price is not None and not df_price.empty:
        last_close = df_price["Close"].iloc[-1]
        first_close = df_price["Close"].iloc[0]
        ret = ((last_close - first_close) / first_close) * 100

        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Price Performance (selected period):")
        y -= 15
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"First Close: {first_close:.2f}")
        y -= 15
        c.drawString(50, y, f"Last Close: {last_close:.2f}")
        y -= 15
        c.drawString(50, y, f"Return: {ret:.2f}%")
        y -= 20

    # Portfolio summary (optional)
    if df_portfolio_summary is not None and not df_portfolio_summary.empty:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Portfolio Snapshot:")
        y -= 15
        c.setFont("Helvetica", 10)
        for _, row in df_portfolio_summary.iterrows():
            line = (
                f"{row['Symbol']}: Shares={row['Shares']}, "
                f"Avg={row['Avg Buy Price']}, Curr={row['Current Price']:.2f}, "
                f"PnL={row['PnL (₹)']:.2f}"
            )
            c.drawString(50, y, line)
            y -= 15
            if y < 100:
                c.showPage()
                y = height - 50

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# =========================
# SIMPLE "AI-LIKE" COMMENT
# =========================

def simple_text_insight(symbol: str, df: pd.DataFrame, info: dict):
    """Lightweight heuristic explanation (no external LLM, safe for college)."""
    if df is None or df.empty:
        return "Not enough price data to generate insights."

    last_close = df["Close"].iloc[-1]
    first_close = df["Close"].iloc[0]
    ret = ((last_close - first_close) / first_close) * 100
    sector = info.get("sector", "N/A") if info else "N/A"

    comment = f"""
For stock **{symbol}**, over the selected period the price moved from approximately ₹{first_close:.2f} to ₹{last_close:.2f},
which is a return of about **{ret:.2f}%**.

Sector: **{sector}**

This assistant is for **educational analysis only** and not a SEBI-registered advisory tool. 
Please do your own research and consult a qualified financial advisor before investing.
"""
    return comment


# =========================
# STREAMLIT UI
# =========================

def main():
    st.set_page_config(
        page_title="Indian Stock Research Assistant",
        layout="wide"
    )

    init_db()

    st.title("📊 AI-Assisted Indian Stock Research (Track A Project)")
    st.caption("Educational financial research assistant – not investment advice.")

    # Sidebar controls
    st.sidebar.header("Stock Settings")

    base_symbol = st.sidebar.text_input("Base Symbol (e.g. RELIANCE, TCS)", value="RELIANCE")
    exchange = st.sidebar.selectbox("Exchange", ["NSE (.NS)", "BSE (.BO)"])

    full_symbol = make_full_symbol(base_symbol, exchange)

    period = st.sidebar.selectbox(
        "History Period",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
        index=2
    )
    interval = st.sidebar.selectbox(
        "Candle Interval",
        ["1d", "1wk", "1mo"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Stock Overview", "News & Sentiment", "Compare Stocks", "Watchlist & Portfolio", "Export Report", "About / Disclaimer"]
    )

    # Main routing
    if page == "Stock Overview":
        render_stock_overview(full_symbol, period, interval)
    elif page == "News & Sentiment":
        render_news_sentiment(full_symbol)
    elif page == "Compare Stocks":
        render_compare_stocks(exchange)
    elif page == "Watchlist & Portfolio":
        render_watchlist_portfolio(exchange)
    elif page == "Export Report":
        render_export_report(full_symbol, period, interval)
    else:
        render_about()


def render_stock_overview(symbol: str, period: str, interval: str):
    st.subheader(f"Stock Overview – {symbol}")

    is_open, msg = is_market_open()
    st.info(msg)

    valid, err = validate_symbol(symbol)
    if not valid:
        st.error(err)
        return

    df = get_stock_history(symbol, period=period, interval=interval)
    if df is None or df.empty:
        st.error("No price data found. Check the symbol or try a different period.")
        return

    df = add_indicators(df)
    info = get_stock_info(symbol)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Price & Technical Indicators")
        plot_price_chart(df, symbol)

    with col2:
        st.markdown("### Basic Fundamentals")

        if info:
            st.write(f"**Company:** {info.get('shortName', 'N/A')}")
            st.write(f"**Sector:** {info.get('sector', 'N/A')}")
            st.write(f"**Industry:** {info.get('industry', 'N/A')}")
            st.write(f"**Market Cap:** {info.get('marketCap', 'N/A')}")
            st.write(f"**PE (TTM):** {info.get('trailingPE', 'N/A')}")
            st.write(f"**52W High:** {info.get('fiftyTwoWeekHigh', 'N/A')}")
            st.write(f"**52W Low:** {info.get('fiftyTwoWeekLow', 'N/A')}")
        else:
            st.write("Fundamental data not available.")

        if st.button("➕ Add to Watchlist", key="add_watchlist_overview"):
            add_to_watchlist(symbol)
            st.success(f"{symbol} added to watchlist.")

    st.markdown("### AI-style Summary (Rule-based)")
    st.info(simple_text_insight(symbol, df, info))


def render_news_sentiment(symbol: str):
    st.subheader(f"News & Sentiment – {symbol}")

    if not NEWS_API_KEY:
        st.warning("NewsAPI key not configured. Set NEWS_API_KEY in the code to enable this section.")
        return

    base = symbol.split(".")[0]
    query = f"{base} stock India"
    articles = fetch_news(query=query, api_key=NEWS_API_KEY, page_size=10)

    if not articles:
        st.info("No news articles found or API limit reached.")
        return

    sentiments = []
    for art in articles:
        polarity, label = analyze_article_sentiment(art)
        sentiments.append({"title": art["title"], "polarity": polarity, "label": label})

    df_sent = pd.DataFrame(sentiments)
    avg_pol = df_sent["polarity"].mean()
    overall_label = sentiment_label(avg_pol)

    st.markdown(f"**Overall Sentiment (News):** {overall_label} (avg polarity {avg_pol:.2f})")
    st.dataframe(df_sent[["title", "label", "polarity"]])

    st.markdown("#### Articles")
    for art, row in zip(articles, sentiments):
        st.markdown(f"**{art['title']}**")
        st.write(art.get("description", ""))
        st.write(f"Sentiment: **{row['label']}** (polarity {row['polarity']:.2f})")
        st.write(f"[Read more]({art.get('url', '#')})")
        st.markdown("---")


def render_compare_stocks(default_exchange: str):
    st.subheader("Compare Two Indian Stocks")

    col1, col2 = st.columns(2)
    with col1:
        base1 = st.text_input("Stock 1 Symbol (e.g. RELIANCE)", value="RELIANCE")
        exch1 = st.selectbox("Exchange 1", ["NSE (.NS)", "BSE (.BO)"], index=0)
        sym1 = make_full_symbol(base1, exch1)

    with col2:
        base2 = st.text_input("Stock 2 Symbol (e.g. TCS)", value="TCS")
        exch2 = st.selectbox("Exchange 2", ["NSE (.NS)", "BSE (.BO)"], index=0)
        sym2 = make_full_symbol(base2, exch2)

    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=2)

    if st.button("Compare"):
        df1 = get_stock_history(sym1, period=period, interval="1d")
        df2 = get_stock_history(sym2, period=period, interval="1d")

        if df1 is None or df1.empty or df2 is None or df2.empty:
            st.error("Could not fetch data for one or both symbols.")
            return

        df1["Return"] = df1["Close"] / df1["Close"].iloc[0] - 1
        df2["Return"] = df2["Close"] / df2["Close"].iloc[0] - 1

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df1["date"], y=df1["Return"] * 100, mode="lines", name=sym1))
        fig.add_trace(go.Scatter(x=df2["date"], y=df2["Return"] * 100, mode="lines", name=sym2))
        fig.update_layout(
            title=f"Relative Returns Comparison ({period})",
            xaxis_title="Date",
            yaxis_title="Return (%)"
        )
        st.plotly_chart(fig, use_container_width=True)


def render_watchlist_portfolio(default_exchange: str):
    st.subheader("Watchlist & Portfolio (SQLite-backed)")

    # Watchlist
    st.markdown("### Watchlist")
    watchlist = get_watchlist()
    if watchlist:
        st.write("Your watchlist:")
        st.write(watchlist)
    else:
        st.info("No symbols in your watchlist yet.")

    col_add, col_rem = st.columns(2)
    with col_add:
        base = st.text_input("Add to Watchlist (Base Symbol)", value="INFY", key="wl_add")
        exch = st.selectbox("Exchange", ["NSE (.NS)", "BSE (.BO)"], key="wl_exch")
        sym = make_full_symbol(base, exch)
        if st.button("Add Symbol", key="wl_add_btn"):
            add_to_watchlist(sym)
            st.success(f"Added {sym} to watchlist.")

    with col_rem:
        rem = st.selectbox("Remove Symbol", watchlist + ["(None)"]) if watchlist else "(None)"
        if st.button("Remove from Watchlist", key="wl_rem_btn") and rem != "(None)":
            remove_from_watchlist(rem)
            st.success(f"Removed {rem} from watchlist.")

    st.markdown("---")
    st.markdown("### Portfolio")

    df_port = get_portfolio()
    if df_port.empty:
        st.info("Portfolio is currently empty.")
    else:
        df_val, total_inv, total_val = compute_portfolio_valuation(df_port)
        st.dataframe(df_val)
        st.metric("Total Invested (₹)", f"{total_inv:,.2f}")
        st.metric("Current Value (₹)", f"{total_val:,.2f}")
        st.metric("PnL (₹)", f"{(total_val - total_inv):,.2f}")

    with st.expander("Add / Update Portfolio Entry"):
        base = st.text_input("Symbol (Base, e.g. RELIANCE)", value="RELIANCE", key="pf_add")
        exch = st.selectbox("Exchange", ["NSE (.NS)", "BSE (.BO)"], key="pf_exch")
        sym = make_full_symbol(base, exch)
        shares = st.number_input("Shares", min_value=0.0, step=1.0, value=10.0)
        avg_price = st.number_input("Average Buy Price (₹)", min_value=0.0, step=1.0, value=2500.0)
        if st.button("Save Position"):
            upsert_portfolio(sym, shares, avg_price)
            st.success(f"Saved {sym} in portfolio.")

    with st.expander("Delete Symbol from Portfolio"):
        if not df_port.empty:
            sym_del = st.selectbox("Symbol", df_port["Symbol"].tolist())
            if st.button("Delete Position"):
                delete_portfolio_symbol(sym_del)
                st.success(f"Deleted {sym_del} from portfolio.")


def render_export_report(symbol: str, period: str, interval: str):
    st.subheader("Export PDF Report")

    df = get_stock_history(symbol, period=period, interval=interval)
    info = get_stock_info(symbol)
    df_port = get_portfolio()
    if df_port.empty:
        df_port_summary = None
    else:
        df_port_summary, _, _ = compute_portfolio_valuation(df_port)

    if st.button("Generate PDF Report"):
        if df is None or df.empty:
            st.error("No price data available for report.")
            return
        pdf_buffer = generate_pdf_report(symbol, df, info, df_port_summary)
        st.success("PDF generated.")
        st.download_button(
            label="Download Report PDF",
            data=pdf_buffer,
            file_name=f"{symbol}_financial_report.pdf",
            mime="application/pdf"
        )


def render_about():
    st.subheader("About / Disclaimer")

    st.markdown("""
### Project Overview

This application is a **Track A – Essential Financial Research Assistant** implementation.

Key Features:
- Indian stock price analysis using Yahoo Finance (`yfinance`)
- Technical indicators: Moving Averages (MA20, MA50), MACD, RSI
- News + sentiment analysis for selected stock (using TextBlob, NewsAPI)
- Stock comparison (relative return charts)
- SQLite-backed watchlist and simple portfolio tracker
- Exportable PDF summary report
- Basic awareness of Indian market hours and INR formatting

### Disclaimer

- This tool is for **educational and academic purposes only**.
- It does **not** provide SEBI-registered investment advice.
- Always consult a qualified financial advisor before making investment decisions.

You can explain in viva:
- APIs used (Yahoo Finance + NewsAPI if enabled)
- Data pipeline: Fetch → Process (Indicators, Sentiment) → Visualize → Store (SQLite)
- Risk and limitations: data delays, free API rate limits, no guarantee of accuracy.
""")


if __name__ == "__main__":
    main()
