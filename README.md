# DSE Market Poller

A robust, fully automated stock scraper and historical database loader for the Dhaka Stock Exchange (DSE). This project fetches live intraday market snapshots and historical End-of-Day (EOD) data using the `bdshare` library, safely storing everything into a Supabase PostgreSQL database.

## Features

- **Dual-Source Architecture**: Fetches live and historical stocks directly from DSE via `bdshare`, while intelligently sourcing the 4 core market indices (`00DSEX`, `00DS30`, `00DSES`, `00DSMEX`) from Amarstock for maximum reliability.
- **Intelligent Historical Backfill**: Automatically detects gaps in your Supabase database and fetches missing EOD data sequentially (day-by-day for Amarstock, ticker-by-ticker for DSE) to ensure 100% data integrity without overwhelming servers.
- **Supabase Integration**: Seamlessly saves snapshot data (ticker, price, volume, and date) into Supabase using optimized bulk upserts.
- **GitHub Actions Scheduled Runs**: Fully automated entirely within GitHub Actions. Designed to run only during market hours to dramatically save Action runner minutes.
- **CSV Seed Importer**: A utility script to instantly import massive legacy CSV datasets directly into the database.

---

## Repository Structure

The project has been heavily modularized to prevent code duplication:

- **`core/`** — Shared library package.
  - `db.py`: Handles Supabase connection and optimized batch upserting.
  - `dse.py`: Contains DSE-specific monkey patches (like disabling invalid SSL certificates).
  - `amarstock.py`: Specialized API fetcher and parser for Amarstock index data.
- **`intraday_scraper.py`** — The 5-minute poller that runs during market hours to fetch live prices from both DSE (stocks) and Amarstock (indices).
- **`backfill_gaps.py`** — The intelligent historical scraper. It isolates missing dates for Amarstock indices and DSE stocks independently, sequentially pulling gaps to mimic robust desktop software architectures.
- **`import_historical.py`** — A script to upload your `merged_data.csv` seed files.
- **`sql/`** — Contains the SQL DDL scripts to create the required tables and views in Supabase.
- **`.github/workflows/`** — GitHub Actions configurations for both the intraday and backfill scrapers.

---

## Getting Started

### 1. Database Setup (Supabase)

You will need a Supabase project or any PostgreSQL instance.

1. Open your Supabase project dashboard.
2. Navigate to the **SQL Editor** → **New query**.
3. Create the main snapshots table by running the SQL in `sql/create_dse_market_snapshots.sql`.
4. Create the tracker view (required by the backfill script) by running the SQL in `sql/create_ticker_max_dates_view.sql`.

### 2. Configure Environment Variables

The scraper requires access to Supabase. Configure the following environment variables (locally in a `.env` file or via shell export):

- `SUPABASE_URL`: Your Supabase project API URL (e.g., `https://<project-ref>.supabase.co`).
- `SUPABASE_SERVICE_ROLE_KEY`: The Supabase `service_role` API key (sensitive, bypasses RLS).

> [!WARNING]
> Keep the `SUPABASE_SERVICE_ROLE_KEY` secret. Never commit it to version control or expose it publicly.

### 3. Local Installation & Development

To run the scrapers locally:

1. **Clone the repository:**
   ```bash
   git clone git@github.com:your-username/dse-market-poller.git
   cd dse-market-poller
   ```
2. **Set up a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   # On Windows:
   .\.venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate

   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **Run the scrapers:**
   - For Intraday: `python intraday_scraper.py`
   - For Historical Gaps: `python backfill_gaps.py`
   - For CSV Seed Import: `python import_historical.py --file merged_data.csv`

---

## Deployment & CI/CD with GitHub Actions

The repository includes two GitHub Actions workflows designed to run entirely on autopilot:

1. **`scraper.yml`**: Runs `intraday_scraper.py` every 5 minutes strictly during BD Market Hours (4:00 AM - 8:30 AM UTC, Sun-Thu).
2. **`intelligent_backfill.yml`**: Runs `backfill_gaps.py` once a day at 3:30 PM BD Time (9:30 AM UTC, Sun-Thu), one hour after the market closes.

To enable these in your own GitHub repository:

1. Go to your repository settings on GitHub.
2. Navigate to **Settings** → **Secrets and variables** → **Actions**.
3. Add the following repository secrets:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

Once the secrets are added, the actions will seamlessly trigger on their schedule and keep your database perfectly in sync.

---

---

## How to Access and Use the Scraped Data

Once the data is saved in Supabase, you can easily use it as a data source in other tools. Here are the two most common setup methods:

### Method 1: Connecting via PostgreSQL ODBC Driver (For AmiBroker / Excel)
An ODBC connection allows desktop applications to connect directly to your database.

1. **Download & Install**: Visit [psqlODBC Downloads](https://www.postgresql.org/ftp/odbc/versions/msi/) and download the MSI installer matching your Windows architecture (64-bit or 32-bit).
2. **Add a System DSN**:
   * Open **ODBC Data Sources** in Windows.
   * Go to **System DSN** -> **Add...** -> **PostgreSQL Unicode**.
   * Fill in your Supabase connection parameters (found in Supabase under *Settings* -> *Database*):
     * **Data Source**: `Supabase_DSE`
     * **Server**: `db.eepwcezwzzlnzqowniyd.supabase.co`
     * **Port**: `5432`
     * **Database**: `postgres`
     * **User Name**: `postgres`
     * **Password**: `[Your Database Password]`
3. **Connect**:
   * **Excel**: Go to *Data* -> *Get Data* -> *From Other Sources* -> *From ODBC*. Select `Supabase_DSE`.
   * **AmiBroker**: Use an ODBC SQL plugin with connection string: `DSN=Supabase_DSE;Uid=postgres;Pwd=[Your Password];`

### Method 2: Accessing via Auto-Generated REST API
Supabase generates a REST API for you out of the box.

* **Base URL**: `https://<your-project-id>.supabase.co/rest/v1/dse_market_snapshots`
* **Query Format**: Send a `GET` request with your `apikey` and `Authorization` headers:
  ```bash
  curl -X GET "https://<your-project-id>.supabase.co/rest/v1/dse_market_snapshots?ticker=eq.00DSEX&order=date.desc&limit=10" \
       -H "apikey: <YOUR_ANON_KEY>" \
       -H "Authorization: Bearer <YOUR_ANON_KEY>"
  ```
* **Python Integration**:
  ```python
  import requests
  url = "https://eepwcezwzzlnzqowniyd.supabase.co/rest/v1/dse_market_snapshots"
  headers = { "apikey": "YOUR_ANON_KEY", "Authorization": "Bearer YOUR_ANON_KEY" }
  params = { "ticker": "eq.00DSEX", "order": "date.desc", "limit": 10 }
  response = requests.get(url, headers=headers, params=params).json()
  ```

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
