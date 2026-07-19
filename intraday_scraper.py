import logging
import argparse
import pandas as pd
from datetime import datetime

from bdshare import get_current_trade_data
from core.db import get_supabase_client, upsert_snapshots
from core.dse import patch_dse_ssl

# Patch SSL to bypass DSE certificate issues
patch_dse_ssl()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def get_today_date_str() -> str:
    return datetime.today().strftime('%Y-%m-%d')

def fetch_intraday_ohlcv() -> pd.DataFrame:
    """
    Fetch current market trade data and return as DataFrame.
    """
    try:
        df = get_current_trade_data()
        if df is None or df.empty:
            raise ValueError("bdshare returned an empty DataFrame.")

        date_str = get_today_date_str()
        df['date'] = date_str
        
        # 'open' is not provided in intraday, so we use 'ycp'
        df['open'] = df['ycp']
        
        return df

    except Exception as e:
        logger.exception("Failed to fetch intraday data: %s", e)
        return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description="DSE Market Poller (Intraday)")
    args = parser.parse_args()

    logger.info("Running in Intraday mode...")
    df = fetch_intraday_ohlcv()
        
    if df.empty:
        logger.warning("No data parsed. Exiting.")
        return

    logger.info("Fetched %d snapshots from DSE", len(df))
    
    client = get_supabase_client()
    upsert_snapshots(client, df, chunk_name="Intraday Snapshots")

if __name__ == "__main__":
    main()