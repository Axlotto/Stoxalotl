"""
Ticker Utility Module for validating and normalizing stock ticker symbols.
Provides efficient client-side validation and checking against known tickers.
"""
import re
import os
import json
import time
import logging
import requests
from typing import Tuple, Dict, Optional, List, Set
from config import FINNHUB_API_KEY, FINNHUB_API_URL

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Common ticker misspellings and corrections
COMMON_MISSPELLINGS = {
    "APPL": "AAPL",   # Apple Inc.
    "AMZM": "AMZN",   # Amazon.com, Inc.
    "FB": "META",     # Meta Platforms (formerly Facebook)
    "GOGL": "GOOGL",  # Alphabet Inc.
    "GOOG": "GOOGL",  # Alphabet Inc. (another class)
    "NTFLX": "NFLX",  # Netflix, Inc.
    "TESL": "TSLA",   # Tesla, Inc.
    "TSLE": "TSLA",   # Tesla, Inc.
    "SOFT": "MSFT",   # Microsoft Corporation
    "MCRSFT": "MSFT", # Microsoft Corporation
    "AMZOM": "AMZN",  # Amazon.com, Inc.
    "NVIDA": "NVDA",  # NVIDIA Corporation
    "NVIDI": "NVDA",  # NVIDIA Corporation
    "COCA": "KO",     # The Coca-Cola Company
    "PEPSI": "PEP",   # PepsiCo, Inc.
    "BRK.A": "BRK-A", # Berkshire Hathaway Inc.
    "BRK.B": "BRK-B", # Berkshire Hathaway Inc.
    "JPM": "JPM",     # JPMorgan Chase & Co. (correct, for validation)
    # Add more common misspellings here
}

# Local cache files
VALID_TICKERS_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "valid_tickers.json")
INVALID_TICKERS_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "invalid_tickers.json")

# In-memory caches
_valid_tickers_cache: Set[str] = set()
_invalid_tickers_cache: Set[str] = set()
_last_cache_load_time = 0
_cache_ttl = 86400  # 24 hours in seconds

def _ensure_cache_dir():
    """Ensure the data directory exists for cache files"""
    cache_dir = os.path.dirname(VALID_TICKERS_CACHE_FILE)
    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir)
            return True
        except Exception as e:
            logging.error(f"Failed to create cache directory: {e}")
            return False
    return True

def _load_ticker_caches():
    """Load ticker caches from disk if they exist and aren't expired"""
    global _valid_tickers_cache, _invalid_tickers_cache, _last_cache_load_time
    
    current_time = time.time()
    
    # If cache is still fresh, don't reload
    if current_time - _last_cache_load_time < _cache_ttl and _valid_tickers_cache:
        return
        
    _ensure_cache_dir()
    
    # Load valid tickers
    try:
        if os.path.exists(VALID_TICKERS_CACHE_FILE):
            with open(VALID_TICKERS_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                # Convert to set for O(1) lookups
                _valid_tickers_cache = set(cache_data.get('tickers', []))
                cache_time = cache_data.get('timestamp', 0)
                
                # Only use cache if it's not expired
                if current_time - cache_time > _cache_ttl:
                    logging.info("Valid tickers cache expired, will be refreshed on next API check")
    except Exception as e:
        logging.error(f"Error loading valid tickers cache: {e}")
        _valid_tickers_cache = set()
    
    # Load invalid tickers
    try:
        if os.path.exists(INVALID_TICKERS_CACHE_FILE):
            with open(INVALID_TICKERS_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                # Convert to set for O(1) lookups
                _invalid_tickers_cache = set(cache_data.get('tickers', []))
                # Expiration handled same as valid tickers
    except Exception as e:
        logging.error(f"Error loading invalid tickers cache: {e}")
        _invalid_tickers_cache = set()
    
    _last_cache_load_time = current_time
    logging.info(f"Loaded {len(_valid_tickers_cache)} valid and {len(_invalid_tickers_cache)} invalid tickers from cache")

def _save_ticker_cache(valid_ticker=None, invalid_ticker=None):
    """Save a ticker to the appropriate cache file"""
    global _valid_tickers_cache, _invalid_tickers_cache
    
    if not _ensure_cache_dir():
        return
        
    # Add to valid tickers cache
    if valid_ticker:
        _valid_tickers_cache.add(valid_ticker)
        try:
            valid_cache_data = {
                'tickers': list(_valid_tickers_cache),
                'timestamp': time.time()
            }
            with open(VALID_TICKERS_CACHE_FILE, 'w') as f:
                json.dump(valid_cache_data, f)
        except Exception as e:
            logging.error(f"Error saving valid ticker cache: {e}")
    
    # Add to invalid tickers cache
    if invalid_ticker:
        _invalid_tickers_cache.add(invalid_ticker)
        try:
            invalid_cache_data = {
                'tickers': list(_invalid_tickers_cache),
                'timestamp': time.time()
            }
            with open(INVALID_TICKERS_CACHE_FILE, 'w') as f:
                json.dump(invalid_cache_data, f)
        except Exception as e:
            logging.error(f"Error saving invalid ticker cache: {e}")

def _check_ticker_pattern(ticker: str) -> bool:
    """
    Check if a ticker matches valid ticker patterns (client-side validation only)
    
    Args:
        ticker: Ticker symbol to check
        
    Returns:
        bool: True if the ticker matches valid patterns, False otherwise
    """
    # Most common U.S. ticker pattern: 1-5 uppercase letters
    if re.match(r'^[A-Z]{1,5}$', ticker):
        return True
        
    # Special cases with dashes (e.g., BRK-A, BRK-B)
    if re.match(r'^[A-Z]{1,4}-[A-Z]$', ticker):
        return True
        
    # Special cases with dots (e.g., BF.A, BF.B) that might be normalized
    if re.match(r'^[A-Z]{1,4}\.[A-Z]$', ticker):
        return True
        
    return False

def _verify_ticker_with_finnhub(ticker: str) -> bool:
    """
    Verify if a ticker exists using Finnhub API
    
    Args:
        ticker: Ticker symbol to verify
        
    Returns:
        bool: True if the ticker exists, False otherwise
    """
    try:
        # First check rate limiting: Query up to 10 tickers per day from Finnhub
        daily_check_key = f"ticker_checks_{time.strftime('%Y%m%d')}"
        checks_today = _get_api_check_count()
        
        if checks_today >= 10:
            logging.warning("Daily Finnhub ticker check limit reached, using pattern matching only")
            return _check_ticker_pattern(ticker)
        
        # Make the API request
        url = f"{FINNHUB_API_URL}/stock/profile2"
        params = {
            'symbol': ticker,
            'token': FINNHUB_API_KEY
        }
        
        response = requests.get(url, params=params)
        
        # Increment the counter
        _increment_api_check_count()
        
        if response.status_code != 200:
            logging.warning(f"Finnhub API returned status code {response.status_code}")
            return False
            
        data = response.json()
        
        # If we get an empty object back, the ticker doesn't exist
        if not data:
            return False
            
        # Check if required fields are present
        return 'ticker' in data and data['ticker'] == ticker
    except Exception as e:
        logging.error(f"Error verifying ticker with Finnhub: {e}")
        # Fall back to pattern checking if API is unavailable
        return _check_ticker_pattern(ticker)

def _get_api_check_count() -> int:
    """Get the number of Finnhub API ticker checks today"""
    daily_check_key = f"ticker_checks_{time.strftime('%Y%m%d')}"
    
    try:
        check_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "api_checks.json")
        
        if not os.path.exists(check_file):
            return 0
            
        with open(check_file, 'r') as f:
            data = json.load(f)
            return data.get(daily_check_key, 0)
    except Exception:
        return 0

def _increment_api_check_count():
    """Increment the Finnhub API ticker check counter"""
    daily_check_key = f"ticker_checks_{time.strftime('%Y%m%d')}"
    
    try:
        check_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "api_checks.json")
        check_dir = os.path.dirname(check_file)
        
        if not os.path.exists(check_dir):
            os.makedirs(check_dir)
        
        data = {}
        if os.path.exists(check_file):
            with open(check_file, 'r') as f:
                data = json.load(f)
        
        count = data.get(daily_check_key, 0) + 1
        data[daily_check_key] = count
        
        with open(check_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"Error updating API check count: {e}")

def get_levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein (edit) distance between two strings
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        int: Edit distance (smaller means more similar)
    """
    if len(s1) < len(s2):
        return get_levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def find_similar_ticker(ticker: str) -> Optional[str]:
    """
    Find a similar ticker to the given (possibly invalid) ticker
    
    Args:
        ticker: Ticker symbol to find similar alternatives for
        
    Returns:
        Optional[str]: Similar ticker symbol, or None if no good match found
    """
    # First check common misspellings
    if ticker in COMMON_MISSPELLINGS:
        return COMMON_MISSPELLINGS[ticker]
    
    # Load cache to check against known valid tickers
    _load_ticker_caches()
    
    # Check edit distance against known valid tickers
    closest = None
    min_distance = float('inf')
    
    # Get all valid tickers we know about
    known_valid = list(_valid_tickers_cache) + list(COMMON_MISSPELLINGS.values())
    
    for valid in known_valid:
        distance = get_levenshtein_distance(ticker, valid)
        # Only consider close matches (edit distance <= 2)
        if distance <= 2 and distance < min_distance:
            min_distance = distance
            closest = valid
    
    return closest

def normalize_ticker(ticker: str) -> str:
    """
    Normalize a ticker symbol (strip, uppercase, handle special cases)
    
    Args:
        ticker: Raw ticker input
        
    Returns:
        str: Normalized ticker symbol
    """
    if not ticker:
        return ""
    
    # Strip whitespace and convert to uppercase
    norm = ticker.strip().upper()
    
    # Handle special cases like BRK.A -> BRK-A
    norm = re.sub(r'([A-Z]{1,4})\.([A-Z])', r'\1-\2', norm)
    
    return norm

def validate_ticker(ticker: str) -> Tuple[str, bool, Optional[str]]:
    """
    Validate and normalize a ticker symbol with comprehensive checks
    
    Args:
        ticker: Raw ticker input
        
    Returns:
        Tuple[str, bool, Optional[str]]: 
            - Normalized ticker
            - Whether it's valid
            - Suggested correction (if available)
    """
    # Handle empty input first
    if not ticker or not ticker.strip():
        return "", False, None
    
    # Normalize the ticker
    normalized = normalize_ticker(ticker)
    
    # Load caches for faster validation
    _load_ticker_caches()
    
    # Check against known valid tickers first (fastest)
    if normalized in _valid_tickers_cache or normalized in COMMON_MISSPELLINGS.values():
        # If the ticker is already known to be valid or is a valid correction, 
        # consider it valid immediately
        return normalized, True, None
    
    # Check if this is a common misspelling
    if normalized in COMMON_MISSPELLINGS:
        correction = COMMON_MISSPELLINGS[normalized]
        return correction, False, correction
    
    # Check if we already know this ticker is invalid
    if normalized in _invalid_tickers_cache:
        # Try to find a similar ticker
        suggestion = find_similar_ticker(normalized)
        # Don't suggest the original ticker as a correction
        if suggestion and suggestion != normalized:
            return normalized, False, suggestion
        else:
            return normalized, False, None
    
    # If we get here, we don't have this ticker in our cache yet
    # Check basic pattern first (much faster than API call)
    if not _check_ticker_pattern(normalized):
        # Invalid pattern - check for similar tickers
        suggestion = find_similar_ticker(normalized)
        # Don't suggest the original ticker as a correction
        if suggestion and suggestion != normalized:
            # Cache this invalid ticker
            _save_ticker_cache(invalid_ticker=normalized)
            return normalized, False, suggestion
        else:
            _save_ticker_cache(invalid_ticker=normalized)
            return normalized, False, None
    
    # Consider all standard-format tickers as potentially valid without API verification
    # This avoids unnecessary API calls and prevents this issue
    # Add it to our valid cache for future checks
    _save_ticker_cache(valid_ticker=normalized)
    return normalized, True, None
