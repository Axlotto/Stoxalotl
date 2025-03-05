import os
from dotenv import load_dotenv
import logging

# Load environment variables from API.env
env_file = "API.env"

# Check if the file exists before trying to load it
if os.path.exists(env_file):
    load_dotenv(env_file)
    # Print the API keys for debugging (with minimal exposure)
    news_key = os.getenv("NEWSAPI_KEY", "")
    finnhub_key = os.getenv("FINNHUB_KEY", "")
    
    # Log success status with key validation
    if news_key:
        logging.info(f"Loaded NEWSAPI_KEY: {news_key[:4]}...{news_key[-4:]}")
    else:
        logging.warning("NEWSAPI_KEY not found in environment")
        
    if finnhub_key:
        logging.info(f"Loaded FINNHUB_KEY: {finnhub_key[:4]}...{finnhub_key[-4:]}")
    else:
        logging.warning("FINNHUB_KEY not found in environment")
else:
    logging.warning(f"Environment file {env_file} not found")
