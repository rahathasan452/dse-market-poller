import sys
import logging
from core.db import get_supabase_client

logging.basicConfig(level=logging.INFO)

client = get_supabase_client()
response = client.table('dse_market_snapshots').delete().eq('date', '2026-07-20').execute()
print(f"Deleted {len(response.data) if response.data else 0} incorrect rows for 2026-07-20.")
