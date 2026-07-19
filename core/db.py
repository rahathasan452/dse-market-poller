import os
import sys
import logging
from supabase import create_client
from dotenv import load_dotenv
import pandas as pd

logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TABLE_NAME = "dse_market_snapshots"

def get_supabase_client():
    if not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def upsert_snapshots(client, df, chunk_name=""):
    """
    Upserts a pandas DataFrame of DSE data into Supabase.
    Expects columns: symbol, ltp (or close), high, low, open, volume, date
    """
    if df is None or df.empty:
        logger.info(f"No data returned for {chunk_name}")
        return

    payload = []
    for _, row in df.iterrows():
        ticker = str(row.get('symbol', '')).strip()
        date_str = str(row.get('date', '')).strip()
        
        if not ticker or not date_str or date_str.lower() == 'nan':
            continue

        try:
            open_price = float(str(row.get('open', '0')).replace(',', ''))
            high_price = float(str(row.get('high', '0')).replace(',', ''))
            low_price = float(str(row.get('low', '0')).replace(',', ''))
            
            # Use 'ltp' if 'close' is missing (for intraday vs EOD differences)
            close_val = row.get('close') if 'close' in row and pd.notnull(row['close']) else row.get('ltp', '0')
            close_price = float(str(close_val).replace(',', ''))
            
            volume_price = int(float(str(row.get('volume', '0')).replace(',', '')))
            
            payload.append({
                "ticker": ticker,
                "date": date_str,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume_price
            })
        except ValueError as e:
            logger.debug(f"Failed to parse row for {ticker} on {date_str}: {e}")
            continue

    if payload:
        batch_size = 1000
        for i in range(0, len(payload), batch_size):
            batch = payload[i:i+batch_size]
            try:
                client.table(TABLE_NAME).upsert(batch, on_conflict="ticker,date").execute()
                logger.info(f"Inserted batch {i//batch_size + 1} ({len(batch)} rows) for {chunk_name}")
            except Exception as e:
                logger.exception(f"Failed to insert batch {i//batch_size + 1} for {chunk_name}")
    else:
        logger.info(f"No valid rows to insert for {chunk_name}")
