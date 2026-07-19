import io
import logging
import requests
import pandas as pd

logger = logging.getLogger(__name__)

AMARSTOCK_CSV_URL = "https://www.amarstock.com/data/download/CSV"
AMARSTOCK_INDICES = {'00DS30', '00DSES', '00DSEX', '00DSMEX'}

def fetch_amarstock_indices(target_date: str) -> pd.DataFrame:
    """
    Fetches the Amarstock CSV data for the given target_date (YYYY-MM-DD)
    and returns it as a Pandas DataFrame filtered ONLY for the 4 core indices.
    Standardizes columns to match bdshare: symbol, date, open, high, low, close, volume.
    Returns an empty DataFrame if no data is found or an error occurs.
    """
    payload = {
        'date': target_date,
        'type': 'adjusted'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://amarstock.com/'
    }
    
    try:
        response = requests.post(AMARSTOCK_CSV_URL, data=payload, headers=headers, timeout=10)
        
        if response.status_code == 200 and len(response.text) > 100:
            lines = response.text.splitlines()
            if not lines:
                return pd.DataFrame()
            
            # Fast string-level filtering
            filtered_lines = [lines[0]]
            for line in lines[1:]:
                parts = line.split(',')
                if len(parts) > 1 and parts[1].strip() in AMARSTOCK_INDICES:
                    filtered_lines.append(line)
            
            if len(filtered_lines) == 1:
                # Only header
                return pd.DataFrame()
                
            csv_data = io.StringIO('\n'.join(filtered_lines))
            df = pd.read_csv(csv_data)
            
            # Standardize columns to bdshare format
            # Amarstock returns: Date_YMD, Scrip, Open, High, Low, Close, Volume
            col_mapping = {
                'Date_YMD': 'date',
                'Scrip': 'symbol',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            }
            # Handle case variations
            actual_mapping = {}
            for col in df.columns:
                c_up = str(col).strip().upper()
                if c_up in ['DATE', 'DATE_YMD']: actual_mapping[col] = 'date'
                elif c_up in ['SCRIP', 'TRADING_CODE', 'TICKER']: actual_mapping[col] = 'symbol'
                elif c_up == 'OPEN': actual_mapping[col] = 'open'
                elif c_up == 'HIGH': actual_mapping[col] = 'high'
                elif c_up == 'LOW': actual_mapping[col] = 'low'
                elif c_up == 'CLOSE': actual_mapping[col] = 'close'
                elif c_up == 'VOLUME': actual_mapping[col] = 'volume'
            
            df.rename(columns=actual_mapping, inplace=True)
            
            # Ensure 'date' uses hyphens
            if 'date' in df.columns:
                def format_date(d):
                    d_str = str(d).strip()
                    if len(d_str) == 8 and d_str.isdigit():
                        return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                    return d_str
                df['date'] = df['date'].apply(format_date)
            else:
                # Add date if missing
                df['date'] = target_date

            required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 0
            
            # Reorder columns and return
            return df[required_cols]

        else:
            logger.warning(f"Failed to fetch Amarstock data for {target_date}. Status Code: {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        logger.exception(f"Error fetching Amarstock data for {target_date}: {e}")
        return pd.DataFrame()
