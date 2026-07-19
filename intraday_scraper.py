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

def get_true_market_date() -> str:
    """
    Scrapes the DSE homepage to find the exact date the current market data belongs to.
    This prevents assigning today's date if the script is run manually before the market opens.
    """
    try:
        from bdshare import get_market_info
        market_info = get_market_info()
        if not market_info.empty:
            raw_date = market_info.iloc[0]['Date']
            dt = datetime.strptime(raw_date, '%d-%m-%Y')
            return dt.strftime('%Y-%m-%d')
    except Exception as e:
        logger.warning(f"Could not fetch true market date, falling back to system date: {e}")
    
    return datetime.today().strftime('%Y-%m-%d')

def fetch_intraday_ohlcv() -> pd.DataFrame:
    """
    Fetch current market trade data and return as DataFrame.
    """
    try:
        df = get_current_trade_data()
        if df is None or df.empty:
            raise ValueError("bdshare returned an empty DataFrame.")

        date_str = get_true_market_date()
        df['date'] = date_str
        
        # 'open' is not provided in intraday, so we use 'ycp'
        df['open'] = df['ycp']
        
        return df

    except Exception as e:
        logger.exception("Failed to fetch intraday data: %s", e)
        return pd.DataFrame()

from core.amarstock import fetch_amarstock_indices

def main():
    parser = argparse.ArgumentParser(description="DSE Market Poller (Intraday)")
    args = parser.parse_args()

    logger.info("Running in Intraday mode...")
    
    # 1. Fetch DSE stocks from bdshare
    df_stocks = fetch_intraday_ohlcv()
    
    # 2. Fetch DSE indices from Amarstock
    today_str = get_true_market_date()
    logger.info("Fetching intraday indices from Amarstock...")
    df_indices = fetch_amarstock_indices(today_str)
    
    # 3. Combine them
    dataframes = []
    if not df_stocks.empty:
        dataframes.append(df_stocks)
    if not df_indices.empty:
        dataframes.append(df_indices)
        
    if not dataframes:
        logger.warning("No data parsed from either bdshare or Amarstock. Exiting.")
        return
        
    df = pd.concat(dataframes, ignore_index=True)

    logger.info("Fetched %d total snapshots", len(df))
    
    client = get_supabase_client()
    upsert_snapshots(client, df, chunk_name="Intraday Snapshots")

if __name__ == "__main__":
    main()