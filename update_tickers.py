"""
Utility script to update the ticker database by fetching the latest symbols
from major exchanges. Run this periodically to keep ticker validation current.
"""

import os
import json
import time
import logging
import requests
from config import FINNHUB_API_KEY, FINNHUB_API_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# File paths
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
VALID_TICKERS_FILE = os.path.join(DATA_DIR, "valid_tickers.json")

def ensure_data_dir():
    """Ensure the data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logging.info(f"Created data directory at {DATA_DIR}")

def fetch_exchange_symbols(exchange):
    """
    Fetch all stock symbols for a specific exchange from Finnhub
    
    Args:
        exchange (str): Exchange code (e.g., 'US')
        
    Returns:
        list: List of valid tickers from the exchange
    """
    try:
        url = f"{FINNHUB_API_URL}/stock/symbol"
        params = {
            'exchange': exchange,
            'token': FINNHUB_API_KEY
        }
        
        logging.info(f"Fetching symbols for exchange: {exchange}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not isinstance(data, list):
            logging.error(f"Unexpected response format for {exchange}: {data}")
            return []
            
        # Extract just the ticker symbols
        tickers = [item['symbol'] for item in data if 'symbol' in item]
        logging.info(f"Retrieved {len(tickers)} symbols from {exchange}")
        return tickers
        
    except Exception as e:
        logging.error(f"Error fetching symbols for {exchange}: {e}")
        return []

def update_ticker_database():
    """Update the ticker database with symbols from major exchanges"""
    ensure_data_dir()
    
    exchanges = ['US', 'NYSE', 'NASDAQ', 'AMEX']
    all_tickers = set()
    
    for exchange in exchanges:
        tickers = fetch_exchange_symbols(exchange)
        # Add to master list
        all_tickers.update(tickers)
        # Respect API rate limits
        time.sleep(1)
    
    # Save to file
    if all_tickers:
        try:
            data = {
                'tickers': list(all_tickers),
                'timestamp': time.time(),
                'count': len(all_tickers),
                'update_date': time.strftime('%Y-%m-%d')
            }
            
            with open(VALID_TICKERS_FILE, 'w') as f:
                json.dump(data, f)
                
            logging.info(f"Successfully updated ticker database with {len(all_tickers)} symbols")
        except Exception as e:
            logging.error(f"Error saving ticker database: {e}")
    else:
        logging.warning("No tickers retrieved, database not updated")

if __name__ == "__main__":
    logging.info("Starting ticker database update")
    update_ticker_database()
    logging.info("Ticker database update completed")
