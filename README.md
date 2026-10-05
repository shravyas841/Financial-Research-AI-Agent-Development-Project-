# Financial Research AI Agent — Version 2

A local Windows Streamlit application for Indian equity research. It retrieves market data and fundamentals, calculates technical and risk metrics deterministically, analyzes NewsAPI article sentiment, tracks a transaction-based SQLite portfolio, builds a validated `ResearchSnapshot`, and optionally asks an LLM to interpret only that snapshot.

> Educational research only. This application does not execute trades, guarantee future performance, or provide personalized investment advice.

## Features

- Yahoo Finance prices and fundamentals
- Candlesticks, SMA 20/50, RSI, MACD, Bollinger Bands, returns, volatility, drawdown, Sharpe ratio, and beta
- NewsAPI metadata and TextBlob sentiment aggregation
- Relative-return stock comparison and SQLite watchlist
- BUY/SELL ledger with idempotency, average cost, realized/unrealized P&L, allocation, and return
- Pydantic-validated `ResearchSnapshot`
- One-shot grounded AI structured analysis—no chatbot
- PDF reports separating verified data from AI interpretation
- Deterministic and mocked tests

## Architecture

```text
Yahoo Finance / NewsAPI
        ↓
Provider clients + validation
        ↓
Deterministic analytics
        ↓
Validated ResearchSnapshot
        ↓
Grounded one-shot AI interpretation
        ↓
Streamlit UI + ReportLab PDF
```

The application owns the facts. The AI owns only the explanation. The LLM receives a serialized, validated `ResearchSnapshot`; it does not browse, fetch prices, calculate missing metrics, or access the database.

## Project structure

```text
app.py                  Streamlit entrypoint and routing
main.py                 Backward-compatible entrypoint
config/                 Local environment configuration
clients/                Yahoo Finance and NewsAPI adapters
analytics/              Deterministic financial calculations
ai/                     Schemas, grounding prompt, Cohere integration
data/                   SQLite schema, migration, repositories
services/               Application workflows and PDF generation
ui/                     Streamlit presentation components
utils/                  Validation, logging, formatting
tests/                  Unit and integration-style tests
```

## Local Windows setup

Open PowerShell in this project directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks activation, use `.venv\Scripts\python.exe` directly.

Edit `.env` locally:

```dotenv
NEWS_API_KEY=your_newsapi_key
COHERE_API_KEY=your_cohere_api_key
COHERE_MODEL=command-a-03-2025
DATABASE_URL=sqlite:///financial_agent.db
REQUEST_TIMEOUT=10
```

Both API keys are optional. Verified stock research, comparison, watchlist, portfolio, and data-only PDF reports work without them. News is unavailable without `NEWS_API_KEY`; grounded AI analysis is unavailable without `COHERE_API_KEY`.

Run:

```powershell
streamlit run app.py
```

Then open the URL printed by Streamlit, normally `http://localhost:8501`.

## Security

- Real keys belong only in `.env`, which Git ignores.
- `.env.example` contains placeholders only.
- Keys are not stored in SQLite, Streamlit state, logs, request URLs, or PDFs.
- NewsAPI authentication uses the `X-Api-Key` header.
- HTTP requests use HTTPS, timeouts, status validation, and safe errors.
- SQL is parameterized; symbols and financial inputs are validated.

If a key was committed or shared, revoke it and generate a new one. Removing it from the latest file does not remove it from Git history.

## Portfolio accounting

The database stores BUY and SELL transactions. Positions are derived in date order using weighted-average cost. BUY fees enter cost basis; SELL fees reduce proceeds. Overselling is rejected. A unique `idempotency_key` prevents duplicate inserts. Existing valid positive rows from the old `portfolio` table are imported once without deleting the old table.

## Grounded AI

The **Generate AI Research Analysis** button explicitly triggers one request. The model receives a strict grounding prompt, the validated snapshot JSON, and a Pydantic response schema. Output is parsed and checked for numeric claims about selected unavailable metrics. API failures are handled without exposing credentials.

**AI provider:** Cohere. The default model is `command-a-03-2025`, configurable with `COHERE_MODEL`. The Cohere Chat V2 request uses JSON Schema structured output; the returned JSON is parsed and validated again through the existing Pydantic `AIAnalysis` model. See the [official Cohere Structured Outputs documentation](https://docs.cohere.com/v2/docs/structured-outputs).

## Tests

```powershell
pytest -q
```

Tests do not require live Yahoo Finance, NewsAPI, or Cohere calls.

## Known limitations

- Yahoo Finance may be delayed or incomplete.
- NewsAPI's free plan has usage and freshness limits.
- TextBlob is general-purpose sentiment, not a price forecast.
- Sharpe ratio uses a documented 0% annual risk-free assumption.
- The market-hours banner does not check exchange holidays.
- This is a single-user local research application, not a production trading or accounting system.
