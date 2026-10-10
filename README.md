# Forex Signal Desk

**A news-driven Forex assistant where AI analyses, a human approves, and code enforces risk before any trade.**

🇦🇿 [Azərbaycan dilində](README.az.md)

The project combines three pieces:

- **n8n** for automation: news ingestion, LLM analysis, Telegram approval.
- **FastAPI** for decisions: signal validation, risk limits, position sizing, execution.
- **A live trading-terminal dashboard.**

It runs in **PAPER (simulation) mode by default**.

## How it works

```
Fed RSS ──► n8n ──► Groq LLM (strict JSON) ──► draft ──► Telegram: /paylas <id> or /rədd <id>
                                                              │ human decision
                                                              ▼
                                         FastAPI: DRAFT → PUBLISHED  ──►  /news page

RSI(14) engine (every 15 min) ─┐
TradingView / n8n webhook ─────┼──► risk chain ──► sizing ──► PAPER / MT5-demo execution
"Generate signal now" button ──┘                                   │
                                                                   ▼
                                               WebSocket live dashboard
```

### Safety by design

- **Nothing publishes itself:** AI news analysis is always saved as a **draft**, and an admin approves
  or rejects it from Telegram with a short ID.
- **Hard risk rules** (`app/risk.py`):
  - only allowed pairs
  - a maximum volume ceiling
  - mandatory stop-loss and take-profit on the correct side of entry
  - a per-pair open-position limit
- **Balance-aware position sizing** (`app/sizing.py`), shared by every signal source. `MAX_VOLUME`
  remains an absolute ceiling, so a sizing bug can't open a huge position.
- **Live orders go only to an explicitly confirmed MT5 demo server**
  (`app/core.py → can_send_mt5_demo_orders`).
- **Grounded AI chat assistant:** it answers questions about the bot and your own paper trades from a
  live database snapshot, and is told never to invent numbers.

## Features

- **Self-running signal engine:** Wilder RSI(14) on daily FX closes from the free Frankfurter/ECB API,
  checked every 15 minutes, with preview and "run now" endpoints.
- **Paper trading:** stop-loss/take-profit tracking, automatic closing, an equity curve.
- **Dashboard:**
  - live FX ticker and candlestick and price charts
  - market analysis and a risk calculator
  - WebSocket live updates (`/ws/live`)
  - a one-click demo run
- **News pipeline:** DRAFT → PUBLISHED / REJECTED workflow, with a generated image per post. Rejected
  drafts are kept for audit.
- **Pages:** `/` dashboard · `/news` · `/about` architecture · `/pricing` · `/docs` Swagger.

## API

| Endpoint | Caller | Purpose |
|---|---|---|
| `POST /webhook/signal` | n8n / TradingView / RSI engine | Validate a signal through the risk chain, execute in PAPER/DEMO |
| `GET /signals/preview` | dashboard | Current RSI(14) per allowed pair, no orders |
| `POST /signals/run-now` | dashboard / n8n / cron | Run the RSI engine once |
| `POST /paper/quote` | simulator | Update prices and close positions on SL/TP |
| `POST /news/draft` | n8n analysis workflow | Store AI analysis + image URL as a DRAFT |
| `POST /news/{id}/approve` · `/reject` | n8n approval workflow | Human decision on a draft |
| `GET /news/posts` | integrations | Published posts as JSON |
| `GET /equity/history` · `/market/history/{symbol}` · `/market/analysis` | dashboard | Charts and analysis |
| `POST /chat` | dashboard | Grounded AI assistant |
| `GET /health` | monitoring | Bot status |

## n8n workflows

1. **News analysis:**
   - Schedule → Federal Reserve RSS → Groq (`llama-3.1-8b-instant`) returns strict JSON: summary,
     affected pairs, impact, direction, confidence.
   - An image link is built, then `POST /news/draft`.
   - Telegram gets the preview plus `/paylas <id>`.
2. **Approval:** Telegram trigger → `/paylas <id>` or `/rədd <id>` → approve or reject endpoint → the
   result is posted back.
3. **RSI trigger (optional):** Schedule → `POST /signals/run-now`.

The workflow JSON exports are not committed because they carry credential references.

## Run it

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
uvicorn main:app --reload --port 9999
```

Then open http://localhost:9999. Configuration is in `.env` (see `.env.example`). SQLite is the
default; any SQLAlchemy URL works.

## Stack

Python · FastAPI · SQLAlchemy · Jinja2 · WebSockets · n8n · Groq · Telegram Bot API · MetaTrader 5 (demo)

## Limitations

- **Daily data only:** the RSI uses daily closes because that is what the free ECB feed provides.
  Intraday signals need a broker's real-time feed.
- **Fixed SL/TP:** stop-loss and take-profit are fixed pip values. ATR-based levels are the natural
  next step.
- **Not investment advice:** this is an engineering project.

## License

MIT
