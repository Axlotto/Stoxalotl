"""
Utility script to validate Finnhub API key
Run this script to quickly check if your API key works
"""
import requests
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_finnhub_api_key(api_key):
    """Test if the provided Finnhub API key is valid"""
    url = "https://finnhub.io/api/v1/stock/symbol"
    params = {
        "exchange": "US",
        "token": api_key
    }
    
    try:
        # Make a simple request to verify the API key
        logging.info(f"Testing API key: {api_key[:4]}...{api_key[-4:]} (first/last 4 chars)")
        response = requests.get(url, params=params)
        
        # Log response details
        logging.info(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                logging.info(f"SUCCESS! API key is valid. Retrieved {len(data)} symbols.")
                return True
            else:
                logging.error("API key may be valid, but returned unexpected data format.")
                return False
        
        elif response.status_code == 401:
            logging.error("API key is INVALID. Authentication failed.")
            return False
            
        elif response.status_code == 403:
            logging.error("API key is valid but FORBIDDEN. Your subscription may not allow this endpoint.")
            return False
            
        elif response.status_code == 429:
            logging.error("Rate limit exceeded. Your API key is valid, but you've hit the rate limit.")
            return True
            
        else:
            logging.error(f"Unexpected status code: {response.status_code}")
            logging.error(f"Response text: {response.text}")
            return False
            
    except Exception as e:
        logging.error(f"Error testing API key: {e}")
        return False

def main():
    # First try to import the key from config
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config import FINNHUB_API_KEY
        
        logging.info("Found API key in config.py")
        api_key = FINNHUB_API_KEY
        
    except ImportError:
        logging.warning("Could not import FINNHUB_API_KEY from config.py")
        api_key = input("Enter your Finnhub API key to test: ")
    
    if check_finnhub_api_key(api_key):
        print("\n✅ API Key is VALID!")
        
        # If the key wasn't in the config file, suggest adding it
        if api_key != FINNHUB_API_KEY:
            print(f"\nAdd this to your config.py file:")
            print(f"FINNHUB_API_KEY = \"{api_key}\"")
    else:
        print("\n❌ API Key appears to be INVALID!")
        print("\nGet a valid API key by signing up at https://finnhub.io/register")
        print("After signing up, find your API key at https://finnhub.io/dashboard")

if __name__ == "__main__":
    main()
