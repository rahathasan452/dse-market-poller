# DSE Market Poller

A lightweight stock scraper and database loader for the Dhaka Stock Exchange (DSE). This project fetches market snapshots (ticker, price, volume) on a schedule using the `bdshare` library and inserts them into a Supabase Postgres table.

## Features

- **Automated Scraping**: Periodically retrieves live market data using the `bdshare` API.
- **Supabase Integration**: Seamlessly saves snapshot data (ticker, price, and volume) into a Supabase database.
- **GitHub Actions Scheduled Runs**: Run the scraper automatically every 5 minutes or trigger it manually using GitHub Actions.
- **Resilient Fallback**: Falls back to a mock dataset when the API fails to ensure validation of the insertion logic.

---

## Repository Structure

- [scraper.py](file:///d:/Project/dse-market-poller/scraper.py) — The core Python script containing the fetch and insert logic.
- [requirements.txt](file:///d:/Project/dse-market-poller/requirements.txt) — Python dependencies (`supabase`, `pandas`, `bdshare`).
- [create_dse_market_snapshots.sql](file:///d:/Project/dse-market-poller/sql/create_dse_market_snapshots.sql) — SQL DDL script to create the Supabase database table and query index.
- [scraper.yml](file:///d:/Project/dse-market-poller/.github/workflows/scraper.yml) — GitHub Actions workflow for scheduled and manual scraper execution.
- [LICENSE](file:///d:/Project/dse-market-poller/LICENSE) — Apache License 2.0 terms.

---

## Getting Started

### 1. Database Setup (Supabase)

You will need a Supabase project or any PostgreSQL instance. To initialize the database table:

1. Open your Supabase project dashboard.
2. Navigate to the **SQL Editor** → **New query**.
3. Copy and paste the contents of [create_dse_market_snapshots.sql](file:///d:/Project/dse-market-poller/sql/create_dse_market_snapshots.sql).
4. Run the query.

Alternatively, you can run the SQL script using `psql`:

```bash
psql "postgresql://postgres:<PASSWORD>@<HOST>:5432/postgres" -f sql/create_dse_market_snapshots.sql
```

### 2. Configure Environment Variables

The scraper requires access to Supabase. Configure the following environment variables:

- `SUPABASE_URL`: Your Supabase project API URL (e.g., `https://<project-ref>.supabase.co`).
- `SUPABASE_SERVICE_ROLE_KEY`: The Supabase `service_role` API key (sensitive, bypasses RLS).

> [!WARNING]
> Keep the `SUPABASE_SERVICE_ROLE_KEY` secret. Never commit it to version control or expose it publicly.

### 3. Local Installation & Development

To run the scraper locally:

1. **Clone the repository:**

   ```bash
   git clone git@github.com:rochi88/bdshare.git
   cd bdshare
   ```
2. **Set up a virtual environment and install dependencies:**

   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate

   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **Set the environ ment variables:**

   - **Linux/macOS:**
     ```bash
     export SUPABASE_URL="https://<project-ref>.supabase.co"
     export SUPABASE_SERVICE_ROLE_KEY="<YOUR_SERVICE_ROLE_KEY>"
     ```
   - **Windows (PowerShell):**
     ```powershell
     $env:SUPABASE_URL="https://<project-ref>.supabase.co"
     $env:SUPABASE_SERVICE_ROLE_KEY="<YOUR_SERVICE_ROLE_KEY>"
     ```
4. **Run the scraper:**

   ```bash
   python scraper.py
   ```

   *Note: If the market API cannot be fetched, the script will log a warning and fall back to mock data to verify your database connection/insertion code.*

---

## Deployment & CI/CD with GitHub Actions

The repository includes a GitHub Actions workflow in [scraper.yml](file:///d:/Project/dse-market-poller/.github/workflows/scraper.yml) configured to:

- Run automatically every 5 minutes.
- Support manual triggers via `workflow_dispatch`.

To configure this in GitHub:

1. Go to your repository settings on GitHub.
2. Navigate to **Settings** → **Secrets and variables** → **Actions**.
3. Add the following repository secrets:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](file:///d:/Project/dse-market-poller/LICENSE) file for details.
