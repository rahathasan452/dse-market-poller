import sys
import time
import logging
import datetime
import bdshare
import pandas as pd

from core.db import get_supabase_client, upsert_snapshots
from core.dse import patch_dse_ssl
from core.amarstock import fetch_amarstock_indices, AMARSTOCK_INDICES

# Patch SSL to bypass DSE certificate issues
patch_dse_ssl()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MAX_HISTORY_DAYS = 730  # bdshare limit is roughly 2 years

def run_backfill():
    client = get_supabase_client()
    
    logger.info("Fetching active tickers from DSE...")
    try:
        active_tickers_df = bdshare.get_current_trade_data()
        if active_tickers_df is None or active_tickers_df.empty:
            logger.error("Failed to fetch active tickers from DSE.")
            sys.exit(1)
        active_tickers = [str(x).strip() for x in active_tickers_df['symbol'].dropna().tolist() if str(x).strip()]
        
        # Inject Amarstock Indices
        for idx in AMARSTOCK_INDICES:
            if idx not in active_tickers:
                active_tickers.append(idx)
                
        logger.info(f"Found {len(active_tickers)} active tickers (including Amarstock indices).")
    except Exception as e:
        logger.exception("Error fetching active tickers")
        sys.exit(1)

    logger.info("Fetching max dates from Supabase view 'ticker_max_dates'...")
    try:
        response = client.table("ticker_max_dates").select("*").execute()
        db_dates = {row['ticker']: row['max_date'] for row in response.data if row.get('max_date')}
    except Exception as e:
        logger.exception("Failed to query 'ticker_max_dates'. Did you create the SQL View?")
        sys.exit(1)

    today = datetime.date.today()
    two_years_ago = today - datetime.timedelta(days=MAX_HISTORY_DAYS)
    
    existing_dates = []
    for ticker in active_tickers:
        if ticker in db_dates:
            dt = datetime.datetime.strptime(db_dates[ticker], "%Y-%m-%d").date()
            existing_dates.append(dt)

    if not existing_dates:
        logger.info("No existing data found. Global start date is 2 years ago.")
        global_start_date = two_years_ago
    else:
        global_start_date = min(existing_dates)
        global_start_date = global_start_date + datetime.timedelta(days=1)
        
    if global_start_date < two_years_ago:
        logger.warning(f"Global start date {global_start_date} is older than 2 years. Capping to {two_years_ago}.")
        global_start_date = two_years_ago
    
    # Split tickers into DSE vs Amarstock
    dse_tickers_to_fetch = []
    amarstock_missing_dates = set()
    
    for ticker in active_tickers:
        start_date = two_years_ago
        if ticker in db_dates:
            dt = datetime.datetime.strptime(db_dates[ticker], "%Y-%m-%d").date()
            if dt < today:
                start_date = dt + datetime.timedelta(days=1)
                if start_date < two_years_ago:
                    start_date = two_years_ago
            else:
                continue # Up to date
                
        if ticker in AMARSTOCK_INDICES:
            # We add all days from start_date to today for this index
            cur_date = start_date
            while cur_date <= today:
                amarstock_missing_dates.add(cur_date)
                cur_date += datetime.timedelta(days=1)
        else:
            dse_tickers_to_fetch.append((ticker, start_date))

    # --- Phase 1: Amarstock Backfill ---
    if amarstock_missing_dates:
        sorted_amarstock_dates = sorted(list(amarstock_missing_dates))
        logger.info(f"Need to backfill {len(sorted_amarstock_dates)} days of Amarstock index data.")
        
        success_count = 0
        for idx, date_obj in enumerate(sorted_amarstock_dates, 1):
            date_str = date_obj.strftime("%Y-%m-%d")
            logger.info(f"[Amarstock {idx}/{len(sorted_amarstock_dates)}] Fetching indices for {date_str}...")
            try:
                df = fetch_amarstock_indices(date_str)
                if df is not None and not df.empty:
                    upsert_snapshots(client, df, chunk_name=f"Amarstock Indices ({date_str})")
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to fetch Amarstock data for {date_str}: {e}")
            
            # Gentle rate-limiting
            time.sleep(0.5)
        logger.info(f"Amarstock backfill completed. Processed {success_count} days.")

    # --- Phase 2: DSE Backfill ---
    if not dse_tickers_to_fetch:
        logger.info("No DSE gaps to fill. DSE tickers are up to date.")
    else:
        logger.info(f"Need to backfill data for {len(dse_tickers_to_fetch)} DSE tickers.")
        logger.info("Starting sequential bulk sync per ticker (DSEBD web)...")
        
        success_count = 0
        for idx, (ticker, start_date) in enumerate(dse_tickers_to_fetch, 1):
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = today.strftime("%Y-%m-%d")
            
            logger.info(f"[DSE {idx}/{len(dse_tickers_to_fetch)}] Processing {ticker} from {start_str} to {end_str}...")
            try:
                df = bdshare.get_historical_data(start=start_str, end=end_str, code=ticker)
                if df is not None and not df.empty:
                    df = df.reset_index()  # Move 'date' from index to a standard column
                    upsert_snapshots(client, df, chunk_name=f"{ticker} ({start_str} to {end_str})")
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed or no data for {ticker}: {e}")
            
            # Sleep briefly between symbols to avoid hammering DSE servers too aggressively
            time.sleep(0.1)
    
        logger.info(f"DSE Intelligent Backfill completed! Successfully processed {success_count} out of {len(dse_tickers_to_fetch)} tickers.")

if __name__ == "__main__":
    run_backfill()
