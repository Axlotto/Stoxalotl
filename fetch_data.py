"""
Financial Data Fetching Module
Standardizes all financial data retrieval through Finnhub API
"""

import requests
import pandas as pd
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any

from config import FINNHUB_API_KEY, FINNHUB_API_URL
from rate_limiter import execute_finnhub_request

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FinnhubError(Exception):
    """Custom exception for Finnhub API errors"""
    pass

def make_finnhub_request(endpoint: str, params: Dict, use_header_auth: bool = False) -> Dict:
    """
    Make a request to Finnhub API with error handling and logging
    
    Args:
        endpoint: API endpoint to access
        params: Query parameters (without the API key)
        use_header_auth: Whether to use header-based authentication instead of query parameter
        
    Returns:
        Dict: JSON response from the API
        
    Raises:
        FinnhubError: If the request fails
    """
    # Add API key to parameters
    params['token'] = FINNHUB_API_KEY
    
    # Construct full URL
    url = f"https://finnhub.io/api/v1/{endpoint}"
    
    logging.info(f"Making Finnhub request to: {url}")
    logging.debug(f"Request params: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        # Log response details for debugging
        logging.debug(f"Response status code: {response.status_code}")
        
        # Check for error status codes
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Check for API error messages in the response body
        if isinstance(data, dict):
            if data.get('error'):
                raise FinnhubError(f"API error: {data['error']}")
            # Handle 'no_data' response for candle data
            if endpoint == 'stock/candle' and data.get('s') == 'no_data':
                raise FinnhubError(f"No data available for the specified symbol and time range")
            # Empty object might mean invalid ticker for profile endpoints
            if endpoint in ['stock/profile', 'stock/profile2'] and not any(data.values()):
                raise FinnhubError(f"No company profile found for the specified symbol")
            
        return data
        
    except requests.exceptions.Timeout:
        raise FinnhubError("Request timed out")
    except requests.exceptions.ConnectionError:
        raise FinnhubError("Connection failed")
    except requests.exceptions.HTTPError as e:
        # Handle specific HTTP errors
        status_code = e.response.status_code if hasattr(e, 'response') else None
        
        if status_code == 401:
            raise FinnhubError("API key invalid or missing")
        elif status_code == 403:
            raise FinnhubError("Access forbidden. Check API subscription level.")
        elif status_code == 429:
            # Extract retry-after header if available
            retry_after = e.response.headers.get('Retry-After', '60')
            try:
                retry_seconds = int(retry_after)
            except ValueError:
                retry_seconds = 60
                
            raise FinnhubError(f"Rate limit exceeded. Try again after {retry_seconds} seconds.")
        else:
            raise FinnhubError(f"HTTP error: {str(e)}")
    except ValueError as e:
        raise FinnhubError(f"Invalid response format: {str(e)}")
    except Exception as e:
        raise FinnhubError(f"Unexpected error: {str(e)}")

def get_stock_quote(ticker: str) -> Dict:
    """
    Get current stock quote data
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Dict: Quote data with keys: c (current price), pc (prev close), h (high), 
              l (low), o (open), t (timestamp)
    """
    params = {'symbol': ticker}
    return execute_finnhub_request(make_finnhub_request, 'quote', params)

def get_company_profile(ticker: str) -> Dict:
    """
    Get company profile information
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Dict: Company profile data with fields like country, currency, exchange,
              ipo date, marketCapitalization, name, ticker, weburl, etc.
    """
    params = {'symbol': ticker}
    return execute_finnhub_request(make_finnhub_request, 'stock/profile2', params)

def search_symbol(query: str) -> List[Dict]:
    """
    Search for symbols by name or ticker
    
    Args:
        query: Search query (company name or ticker)
        
    Returns:
        List[Dict]: List of matching symbols with description, displaySymbol, symbol and type
    """
    params = {'q': query}
    return execute_finnhub_request(make_finnhub_request, 'search', params)

def get_market_status() -> Dict[str, Any]:
    """
    Get current market status (whether market is open or closed)
    
    Returns:
        Dict: Contains market status information including whether market is open
    """
    return execute_finnhub_request(make_finnhub_request, 'stock/market-status', {})

def get_market_holidays() -> Dict[str, Any]:
    """
    Get list of market holidays
    
    Returns:
        Dict: Contains list of market holidays
    """
    params = {'exchange': 'US'}  # Default to US exchange
    return execute_finnhub_request(make_finnhub_request, 'stock/market-holiday', params)

def get_historical_data(ticker: str, resolution: str, from_timestamp: int, to_timestamp: int) -> Dict:
    """
    Get historical price candles
    
    Args:
        ticker: Stock symbol
        resolution: Candle resolution (1, 5, 15, 30, 60, D, W, M)
        from_timestamp: Unix timestamp for start date
        to_timestamp: Unix timestamp for end date
        
    Returns:
        Dict: Historical candle data with keys: c, h, l, o, t, v (close, high, low, open, time, volume)
    """
    params = {
        'symbol': ticker,
        'resolution': resolution,
        'from': from_timestamp,
        'to': to_timestamp
    }
    return execute_finnhub_request(make_finnhub_request, 'stock/candle', params)

def get_stock_metrics(ticker: str) -> Dict:
    """
    Get financial metrics for a stock
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Dict: Financial metrics including P/E ratio, 52-week high/low, etc.
    """
    params = {
        'symbol': ticker,
        'metric': 'all'
    }
    return execute_finnhub_request(make_finnhub_request, 'stock/metric', params)

def get_price_target(ticker: str) -> Dict:
    """
    Get price target information
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Dict: Price target data including targetHigh, targetLow, targetMean, targetMedian
    """
    params = {'symbol': ticker}
    return execute_finnhub_request(make_finnhub_request, 'stock/price-target', params)

def get_recommendation_trends(ticker: str) -> List[Dict]:
    """
    Get recommendation trends
    
    Args:
        ticker: Stock symbol
        
    Returns:
        List[Dict]: Recommendation trend data with buy, hold, sell, strongBuy, strongSell counts
    """
    params = {'symbol': ticker}
    return execute_finnhub_request(make_finnhub_request, 'stock/recommendation', params)

def get_earnings(ticker: str) -> List[Dict]:
    """
    Get earnings data
    
    Args:
        ticker: Stock symbol
        
    Returns:
        List[Dict]: Earnings data including actual, estimate, surprise, and period values
    """
    params = {'symbol': ticker}
    return execute_finnhub_request(make_finnhub_request, 'stock/earnings', params)

def get_earnings_calendar(from_date: str = None, to_date: str = None, symbols: str = None) -> Dict:
    """
    Get earnings calendar
    
    Args:
        from_date: From date in YYYY-MM-DD format
        to_date: To date in YYYY-MM-DD format
        symbols: Comma-separated list of symbols (optional)
        
    Returns:
        Dict: Earnings calendar data
    """
    params = {}
    if from_date:
        params['from'] = from_date
    if to_date:
        params['to'] = to_date
    if symbols:
        params['symbol'] = symbols
    
    return execute_finnhub_request(make_finnhub_request, 'calendar/earnings', params)

def get_ticker_news(ticker: str, from_date: str, to_date: str = None, limit: int = 10) -> List[Dict]:
    """
    Get news for a specific ticker
    
    Args:
        ticker: Stock symbol
        from_date: From date (YYYY-MM-DD)
        to_date: To date (YYYY-MM-DD), defaults to today if None
        limit: Number of articles to return
        
    Returns:
        List[Dict]: News articles
    """
    if to_date is None:
        to_date = datetime.now().strftime('%Y-%m-%d')
        
    params = {
        'symbol': ticker,
        'from': from_date,
        'to': to_date,
        'limit': limit
    }
    return execute_finnhub_request(make_finnhub_request, 'company-news', params)

def get_market_news(category: str = 'general', limit: int = 10) -> List[Dict]:
    """
    Get general market news
    
    Args:
        category: News category (general, forex, crypto, merger)
        limit: Number of articles to return
        
    Returns:
        List[Dict]: News articles
    """
    params = {'category': category, 'limit': limit}
    return execute_finnhub_request(make_finnhub_request, 'news', params)

def get_news_sentiment(ticker: str) -> Dict:
    """
    Get news sentiment for a ticker
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Dict: News sentiment data
    """
    params = {'symbol': ticker}
    return execute_finnhub_request(make_finnhub_request, 'news-sentiment', params)

def get_peers(ticker: str) -> List[str]:
    """
    Get company peers
    
    Args:
        ticker: Stock symbol
        
    Returns:
        List[str]: List of peer company symbols
    """
    params = {'symbol': ticker}
    return execute_finnhub_request(make_finnhub_request, 'stock/peers', params)

def get_insider_transactions(ticker: str, from_date: str = None, to_date: str = None) -> Dict:
    """
    Get insider transactions
    
    Args:
        ticker: Stock symbol
        from_date: From date (YYYY-MM-DD), defaults to 3 months ago if None
        to_date: To date (YYYY-MM-DD), defaults to today if None
        
    Returns:
        Dict: Insider transactions data
    """
    if from_date is None:
        from_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
    if to_date is None:
        to_date = datetime.now().strftime('%Y-%m-%d')
        
    params = {
        'symbol': ticker,
        'from': from_date,
        'to': to_date
    }
    return execute_finnhub_request(make_finnhub_request, 'stock/insider-transactions', params)

def get_insider_sentiment(ticker: str, from_date: str = None, to_date: str = None) -> Dict:
    """
    Get insider sentiment
    
    Args:
        ticker: Stock symbol
        from_date: From date (YYYY-MM-DD)
        to_date: To date (YYYY-MM-DD)
        
    Returns:
        Dict: Insider sentiment data with MSPR scores
    """
    if from_date is None:
        from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
    if to_date is None:
        to_date = datetime.now().strftime('%Y-%m-%d')
        
    params = {
        'symbol': ticker,
        'from': from_date,
        'to': to_date
    }
    return execute_finnhub_request(make_finnhub_request, 'stock/insider-sentiment', params)

def get_stock_symbols(exchange: str) -> List[Dict]:
    """
    Get list of symbols in an exchange
    
    Args:
        exchange: Exchange code (e.g., 'US')
        
    Returns:
        List[Dict]: List of symbols
    """
    params = {'exchange': exchange}
    return execute_finnhub_request(make_finnhub_request, 'stock/symbol', params)

def format_candle_data_to_dataframe(candle_data: Dict) -> pd.DataFrame:
    """
    Convert Finnhub candle data to pandas DataFrame
    
    Args:
        candle_data: Candle data from Finnhub API
        
    Returns:
        pd.DataFrame: DataFrame with OHLCV data
    """
    if not candle_data or candle_data.get('s') == 'no_data':
        return pd.DataFrame()
        
    # Extract data arrays
    timestamps = candle_data.get('t', [])
    opens = candle_data.get('o', [])
    highs = candle_data.get('h', [])
    lows = candle_data.get('l', [])
    closes = candle_data.get('c', [])
    volumes = candle_data.get('v', [])
    
    # Create DataFrame
    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=pd.DatetimeIndex([datetime.fromtimestamp(t) for t in timestamps]))
    
    return df

def get_historical_dataframe(ticker: str, timeframe: str = "3M") -> pd.DataFrame:
    """
    Get historical data as a pandas DataFrame
    
    Args:
        ticker: Stock symbol
        timeframe: Time period (1D, 1W, 1M, 3M, 6M, 1Y, 5Y)
        
    Returns:
        pd.DataFrame: DataFrame with OHLCV data
    """
    # Calculate from and to timestamps based on timeframe
    to_timestamp = int(time.time())
    
    if timeframe == "1D":
        from_timestamp = to_timestamp - (60 * 60 * 24)  # 1 day
        resolution = "5"  # 5 minutes
    elif timeframe == "1W":
        from_timestamp = to_timestamp - (60 * 60 * 24 * 7)  # 1 week
        resolution = "15"  # 15 minutes
    elif timeframe == "1M":
        from_timestamp = to_timestamp - (60 * 60 * 24 * 30)  # 1 month
        resolution = "60"  # 1 hour
    elif timeframe == "3M":
        from_timestamp = to_timestamp - (60 * 60 * 24 * 90)  # 3 months
        resolution = "D"  # Daily
    elif timeframe == "6M":
        from_timestamp = to_timestamp - (60 * 60 * 24 * 180)  # 6 months
        resolution = "D"  # Daily
    elif timeframe == "1Y":
        from_timestamp = to_timestamp - (60 * 60 * 24 * 365)  # 1 year
        resolution = "W"  # Weekly
    elif timeframe == "5Y":
        from_timestamp = to_timestamp - (60 * 60 * 24 * 365 * 5)  # 5 years
        resolution = "M"  # Monthly
    else:
        # Default to 3 months
        from_timestamp = to_timestamp - (60 * 60 * 24 * 90)  # 3 months
        resolution = "D"  # Daily
    
    # Get candle data
    candles = get_historical_data(ticker, resolution, from_timestamp, to_timestamp)
    
    # Convert to DataFrame
    return format_candle_data_to_dataframe(candles)
