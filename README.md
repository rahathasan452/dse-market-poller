# DSE Market Poller & Telegram Price Alert System 🚀

A robust, fully automated stock scraper, historical database loader, and real-time Telegram price alert system for the Dhaka Stock Exchange (DSE). 

This project fetches live intraday market snapshots and historical End-of-Day (EOD) data using `bdshare` and `Amarstock`, safely stores everything into a Supabase PostgreSQL database, and allows you to manage live stock price alerts directly from Telegram on your phone with zero GitHub Actions compute cost!

---

## ✨ Features

- 📈 **Dual-Source Architecture**: Fetches live and historical stocks directly from DSE via `bdshare`, while intelligently sourcing the 4 core market indices (`00DSEX`, `00DS30`, `00DSES`, `00DSMEX`) from Amarstock.
- ⚡ **Intelligent Historical Backfill**: Automatically detects missing dates in Supabase and fills historical gaps sequentially to ensure 100% data integrity.
- 🤖 **Interactive Telegram Bot Manager**: Add, list, delete, and check stock prices directly from Telegram on your phone!
- 🎯 **Dual Bracket Alerts (Take Profit & Stop Loss in 1 Command)**: Set both a target high price (Take Profit) and target low price (Stop Loss) simultaneously in a single command (`/add GP 280 240`).
- 🔍 **Smart Ticker Autofill & Suggestions**: If you misspell or type a partial ticker (e.g. `/price SQU`), the bot presents clickable inline buttons with suggested tickers (`SQURPHARMA`, `SQUARETEXT`).
- ⚡ **Zero GitHub Actions Compute Minutes for Alerts**: Notifications are evaluated and dispatched 100% inside Supabase using Postgres `pg_net` triggers and Edge Functions.
- 🔄 **Automated GitHub Actions Workflows**: Intraday scraping runs automatically during Bangladesh market hours (Sun–Thu).

---

## 📁 Repository Structure

```text
dse-market-poller/
├── core/
│   ├── db.py               # Supabase database client and bulk upsert helpers
│   ├── dse.py              # DSE patch utilities (disabling invalid SSL certs)
│   └── amarstock.py        # Amarstock index API fetcher & parser
├── sql/
│   ├── create_dse_market_snapshots.sql # Main OHLCV snapshots table schema
│   ├── create_ticker_max_dates_view.sql# View tracking max scraped date per ticker
│   └── create_price_alerts.sql         # Price alerts table schema & pg_net trigger
├── supabase/
│   └── functions/
│       └── telegram-bot/
│           └── index.ts    # Deno Edge Function handling Telegram bot commands, dual alerts & autocomplete
├── .github/workflows/
│   ├── scraper.yml         # 15-minute intraday market scraper workflow
│   └── intelligent_backfill.yml # Daily historical EOD backfill workflow
├── intraday_scraper.py     # Main 15-min live market scraper script
├── backfill_gaps.py        # Historical gap detector & backfill script
├── import_historical.py    # Seed CSV import script
└── requirements.txt        # Python dependencies
```

---

## 📲 Telegram Bot Commands

You can control your stock alerts directly from your phone:

| Command | Usage Example | Description |
| :--- | :--- | :--- |
| `/add` | `/add GP 280 240` | **Dual Bracket Alert:** Sets Take Profit (ABOVE 280) AND Stop Loss (BELOW 240) in 1 command! |
| `/add` | `/add GP 280 ABOVE` | Create a single target price alert |
| `/add` | `/add SQURPHARMA 220 BELOW` | Create a single stop loss price alert |
| `/list` | `/list` | View all active price alerts with IDs |
| `/del` | `/del 3` | Delete an active price alert by ID |
| `/price` | `/price BATBC` | Check current stock quote, high/low, and volume |
| `/help` | `/help` | Display command help menu |

> 💡 **Autofill / Suggestions**: If you type `/price SQU`, the bot automatically suggests `SQURPHARMA` and `SQUARETEXT` via interactive inline buttons!

---

## 🚀 Quick Setup Guide

### 1. Database Setup (Supabase)

1. Open your **Supabase Project Dashboard → SQL Editor**.
2. Run `sql/create_dse_market_snapshots.sql` to create the market snapshots table.
3. Run `sql/create_ticker_max_dates_view.sql` to create the max date tracking view.
4. Run `sql/create_price_alerts.sql` to create the alerts table and Postgres notification trigger.

---

### 2. Set Up the Telegram Bot (3 Minutes)

1. **Create Bot**: Message `@BotFather` on Telegram, send `/newbot`, and copy your **Bot Token**.
2. **Deploy Edge Function**:
   - Go to **Supabase Dashboard → Edge Functions** → Create function `telegram-bot`.
   - Paste code from `supabase/functions/telegram-bot/index.ts`.
   - Add Secret: `TELEGRAM_BOT_TOKEN = <your_bot_token>`.
   - Copy the deployed function URL (e.g. `https://xyz.supabase.co/functions/v1/telegram-bot`).
3. **Set Telegram Webhook**:
   Open this URL in your browser:
   `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<YOUR_PROJECT_REF>.supabase.co/functions/v1/telegram-bot`

---

### 3. Local Development

1. **Clone & Install Dependencies:**
   ```bash
   git clone https://github.com/your-username/dse-market-poller.git
   cd dse-market-poller
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables (`.env`):**
   ```env
   SUPABASE_URL=https://<your-project-ref>.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   ```

3. **Run Scrapers Locally:**
   - **Intraday Scraper**: `python intraday_scraper.py`
   - **Historical Backfill**: `python backfill_gaps.py`

---

## 🤖 GitHub Actions Automation

The project runs completely automated using 2 GitHub Actions workflows:

1. **`scraper.yml`**: Runs `intraday_scraper.py` every 15 minutes during BD Market Hours (4:00 AM – 8:30 AM UTC, Sun–Thu).
2. **`intelligent_backfill.yml`**: Runs `backfill_gaps.py` daily at 3:30 PM BD Time to automatically fill missing historical market data.

To enable, add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to your **GitHub Repo Secrets**.

---

## 📜 License

This project is open source and available under the [MIT License](LICENSE).
