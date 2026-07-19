import logging
import argparse
import pandas as pd

from core.db import get_supabase_client, upsert_snapshots

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def import_historical_data(csv_path: str, chunk_size: int = 5000, start_chunk: int = 0):
    client = get_supabase_client()
    
    logger.info(f"Reading CSV from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.exception("Failed to read CSV")
        return

    required_columns = {'ticker', 'date', 'open', 'high', 'low', 'close', 'volume'}
    missing = required_columns - set(df.columns)
    if missing:
        logger.error(f"CSV is missing required columns: {missing}")
        return

    # Ensure date is string format yyyy-mm-dd
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    
    # We rename 'ticker' to 'symbol' because core.db expects 'symbol' (from bdshare)
    df.rename(columns={'ticker': 'symbol'}, inplace=True)

    total_rows = len(df)
    logger.info(f"Found {total_rows} rows to import.")

    chunks = [df[i:i+chunk_size] for i in range(0, total_rows, chunk_size)]
    total_chunks = len(chunks)

    for idx in range(start_chunk, total_chunks):
        chunk_df = chunks[idx]
        logger.info(f"Processing chunk {idx + 1}/{total_chunks}...")
        upsert_snapshots(client, chunk_df, chunk_name=f"CSV Chunk {idx + 1}")

    logger.info("Import completed successfully.")

def main():
    parser = argparse.ArgumentParser(description="Import Historical DSE Data to Supabase")
    parser.add_argument("--file", type=str, required=True, help="Path to the merged_data.csv file")
    parser.add_argument("--chunk-size", type=int, default=5000, help="Number of rows per insert batch")
    parser.add_argument("--start-chunk", type=int, default=0, help="Chunk index to start/resume from")
    
    args = parser.parse_args()
    import_historical_data(args.file, chunk_size=args.chunk_size, start_chunk=args.start_chunk)

if __name__ == "__main__":
    main()
