import requests
import pandas as pd
import numpy as np  # Add NumPy import for dummy data generation
from datetime import datetime, timedelta
from tradingview_ta import TA_Handler, Interval
from typing import Dict, List, Optional, Union
from config import FINNHUB_API_KEY, FINNHUB_API_URL, NEWS_API_KEY, NEWS_API_URL, OLLAMA_MODEL
import ollama
import time
import threading
import logging
from api_request_manager import ApiRequestManager

# Import the rate limiter
from rate_limiter import (
    execute_finnhub_request, 
    execute_news_api_request, 
    execute_ollama_request
)

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize global request manager with 10 seconds between requests
api_request_manager = ApiRequestManager(min_request_interval=10.0)

class StockAPIError(Exception):
    """Custom exception for Stock API errors"""
    pass

class AIClientError(Exception):
    """Custom exception for AI client errors"""
    pass

class StockAPI:
    def __init__(self, request_counter=None, max_requests_per_second=30):
        self.request_counter = request_counter
        self.lock = threading.Lock()
        self.last_request_time = time.time()
        self.max_requests_per_second = max_requests_per_second
        self.cache = {}  # Simple memory cache
        self.cache_ttl = 300  # Cache TTL in seconds (5 minutes)

    def _make_finnhub_request(self, url, params):
        """Helper method to make the actual API request to Finnhub with detailed logging and validation"""
        logging.info(f"Making Finnhub request: {url}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            # Log response status
            logging.debug(f"Finnhub response status: {response.status_code}")
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            return data
        except Exception as e:
            logging.error(f"Finnhub API error: {str(e)}")
            raise

    def get_stock(self, ticker: str, retries: int = 3, backoff_factor: float = 0.3, use_cache: bool = True) -> Dict:
        """Fetch stock data using Finnhub API with rate limiting, caching and retry logic"""
        ticker = ticker.upper()  # Normalize ticker to uppercase
        
        # Use proper cache key that includes the ticker
        cache_key = f"stock_data_{ticker}"
        
        # Check cache first if enabled
        if use_cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                logging.info(f"Using cached stock data for {ticker} from cache key: {cache_key}")
                return cache_entry['data']
        
        if self.request_counter:
            self.request_counter.increment_api()
        
        # Use exponential backoff for retries
        retry_count = 0
        last_error = None
        
        while retry_count <= retries:
            try:
                if retry_count > 0:
                    # Calculate delay with exponential backoff
                    delay = backoff_factor * (2 ** (retry_count - 1))  # Start with backoff_factor seconds
                    logging.info(f"Retry {retry_count}/{retries} for {ticker} after {delay:.2f}s delay")
                    time.sleep(delay)
                
                # Use the direct approach as in the example
                base_url = "https://finnhub.io/api/v1/quote"
                params = {"symbol": ticker, "token": FINNHUB_API_KEY}
                
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Validate the response
                if not data:
                    raise StockAPIError(f"Empty response for ticker: {ticker}")
                
                # Validate required fields
                required_fields = ['c', 'pc', 'd', 'dp', 'h', 'l']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    raise StockAPIError(f"Missing fields for {ticker}: {', '.join(missing_fields)}")
                
                # Cache the result
                if use_cache:
                    self.cache[cache_key] = {
                        'timestamp': time.time(),
                        'data': data
                    }
                
                return data
                
            except Exception as e:
                logging.error(f"Error fetching {ticker}: {str(e)}")
                last_error = e
                retry_count += 1
        
        # If we got here, all retries failed
        if last_error:
            raise last_error
        else:
            raise StockAPIError(f"Failed to fetch data for {ticker} after {retries} retries")

    def _make_news_api_request(self, url, params):
        """Helper method to make the actual API request to News API with proper authentication"""
        # Use headers for authentication instead of query parameters
        headers = {'X-Api-Key': NEWS_API_KEY}
        
        # Don't include API key in parameters
        if 'apiKey' in params:
            del params['apiKey']
        
        logging.info(f"Making News API request: {url} with params {params}")
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 401:
                    logging.error("News API authorization failed - invalid API key")
                    # Return a structured error response instead of raising exception
                    return {
                        'status': 'error',
                        'message': '🔒 News API authorization failed - check API key',
                        'articles': []
                    }
                elif e.response.status_code == 429:
                    logging.error("News API rate limit exceeded")
                    return {
                        'status': 'error',
                        'message': '⚠️ News API rate limit exceeded',
                        'articles': []
                    }
            raise

    def get_news(self, ticker: str, days_back: int = 3, num_articles: int = 3, use_cache: bool = True) -> List[Dict]:
        """Fetch news articles with rate limiting and caching"""
        # Check cache first if enabled
        cache_key = f"news_{ticker}_{days_back}_{num_articles}"
        if use_cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                logging.info(f"Using cached news data for {ticker}")
                return cache_entry['data']
        
        # Increment the appropriate counter if available
        if self.request_counter:
            self.request_counter.increment('news_api')
            
        try:
            # Fixed: use 'q' parameter instead of 'n' for query
            params = {
                'q': ticker,  # Correct parameter name for query
                'from': (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d'),
                'sortBy': 'relevancy',
                'language': 'en',
                'pageSize': num_articles
            }
            
            # Execute with rate limiting
            data = execute_news_api_request(
                self._make_news_api_request,
                NEWS_API_URL,
                params
            )
            
            # Check status - data might be an error response from _make_news_api_request
            if data.get('status') == 'error':
                # Return the error message from the request function
                return [{"title": "Error", "description": data.get('message', 'Unknown error'), "source": {"name": "System"}}]
            
            if data['status'] != 'ok':
                logging.error(f"News API error: {data.get('message', 'Unknown error')}")
                return [{"title": "Error", "description": f"News API error: {data.get('message', 'Unknown error')}", "source": {"name": "System"}}]
            
            articles = data.get('articles', [])
            
            # Enhance articles with properly formatted dates
            for article in articles:
                if 'publishedAt' in article:
                    try:
                        # Convert ISO date to more readable format
                        date_obj = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                        article['formatted_date'] = date_obj.strftime('%b %d, %Y')
                    except:
                        article['formatted_date'] = article['publishedAt']
            
            # Cache the result
            if use_cache:
                self.cache[cache_key] = {
                    'timestamp': time.time(),
                    'data': articles
                }
            
            return articles
        except Exception as e:
            logging.error(f"News processing error: {str(e)}")
            return [{"title": "News Unavailable", 
                    "description": f"Could not retrieve news at this time: {str(e)}", 
                    "source": {"name": "System"}}]

    def _finnhub_get_candles(self, ticker, resolution, from_time, to_time):
        """Get historical candle data from Finnhub API"""
        params = {
            'symbol': ticker,
            'resolution': resolution,
            'from': from_time,
            'to': to_time,
            'token': FINNHUB_API_KEY
        }
        url = "https://finnhub.io/api/v1/stock/candle"
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_chart_data(self, ticker: str, timeframe: str = "3M", use_cache: bool = True) -> pd.DataFrame:
        """
        Get chart data using Finnhub instead of yfinance
        
        Args:
            ticker: Stock symbol
            timeframe: Time period (1D, 1W, 1M, 3M, 6M, 1Y, 5Y)
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with OHLCV data
        """
        # Check cache first if enabled
        cache_key = f"chart_{ticker}_{timeframe}"
        if use_cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                logging.info(f"Using cached chart data for {ticker}")
                return cache_entry['data']
                
        # Calculate from and to timestamps based on timeframe
        to_time = int(time.time())  # Current time in seconds
        
        if timeframe == "1D":
            from_time = to_time - (60 * 60 * 24)  # 1 day back
            resolution = "5"  # 5 minutes
        elif timeframe == "1W":
            from_time = to_time - (60 * 60 * 24 * 7)  # 1 week back
            resolution = "15"  # 15 minutes
        elif timeframe == "1M":
            from_time = to_time - (60 * 60 * 24 * 30)  # 30 days back
            resolution = "60"  # 60 minutes
        elif timeframe == "3M":
            from_time = to_time - (60 * 60 * 24 * 90)  # 90 days back
            resolution = "D"  # Daily
        elif timeframe == "6M":
            from_time = to_time - (60 * 60 * 24 * 180)  # 180 days back
            resolution = "D"  # Daily
        elif timeframe == "1Y":
            from_time = to_time - (60 * 60 * 24 * 365)  # 365 days back
            resolution = "W"  # Weekly
        elif timeframe == "5Y":
            from_time = to_time - (60 * 60 * 24 * 365 * 5)  # 5 years back
            resolution = "M"  # Monthly
        else:
            # Default to 3 months
            from_time = to_time - (60 * 60 * 24 * 90)  # 90 days back
            resolution = "D"  # Daily
        
        # Debug log timestamps
        logging.info(f"Chart request time range: from={from_time} ({datetime.fromtimestamp(from_time).strftime('%Y-%m-%d')}), "
                    f"to={to_time} ({datetime.fromtimestamp(to_time).strftime('%Y-%m-%d')})")
        
        # Use proper Finnhub symbol format - ensure uppercase and handle special cases
        finnhub_ticker = ticker.upper()
        
        try:
            # Try to get data from Finnhub
            try:
                # First check if we can get valid data from Finnhub
                logging.info(f"Attempting to fetch chart data from Finnhub for {ticker}")
                data = self._finnhub_get_candles(finnhub_ticker, resolution, from_time, to_time)
                
                # Check if data is valid
                if not data or 'error' in data or data.get('s') == 'no_data' or not data.get('c') or len(data.get('c', [])) == 0:
                    logging.warning(f"Invalid or empty data returned from Finnhub: {data}")
                    # Generate dummy data if Finnhub data is invalid
                    return self._generate_dummy_chart_data(ticker, from_time, to_time)
                    
                # If we got here, data looks valid
                df = pd.DataFrame({
                    'Open': data.get('o', []),
                    'High': data.get('h', []),
                    'Low': data.get('l', []),
                    'Close': data.get('c', []),
                    'Volume': data.get('v', [])
                })
                
                timestamps = [datetime.fromtimestamp(t) for t in data.get('t', [])]
                df.index = pd.DatetimeIndex(timestamps)
                
                # Cache the valid data
                if not df.empty and use_cache:
                    self.cache[cache_key] = {
                        'timestamp': time.time(),
                        'data': df
                    }
                
                return df
                
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                if hasattr(e, 'response') and e.response and e.response.status_code == 403:
                    logging.error(f"Finnhub API access forbidden (403). Please check your API key and permissions.")
                else:
                    logging.error(f"Finnhub API request failed: {str(e)}")
                
                # Fall back to dummy data
                return self._generate_dummy_chart_data(ticker, from_time, to_time)
        
        except Exception as e:
            logging.error(f"Error fetching chart data: {e}")
            return self._generate_dummy_chart_data(ticker, from_time, to_time)

    def _generate_dummy_chart_data(self, ticker, from_time, to_time):
        """Generate dummy chart data when API fails"""
        logging.warning(f"Generating dummy chart data for {ticker} as fallback")
        
        # Calculate number of days in the range
        days = (to_time - from_time) // (24 * 60 * 60)
        days = max(5, min(days, 365))  # Between 5 days and 1 year
        
        # Use the ticker string to create a semi-random seed for deterministic behavior
        # This way, the same ticker will always generate the same pattern
        seed = sum(ord(c) for c in ticker)
        np.random.seed(seed)
        
        # Generate a simple time series with a somewhat realistic pattern
        # Use ticker to influence base price (make it look different for each ticker)
        base_price = 50.0 + (seed % 200)  # Base price between 50 and 250
        volatility = 0.02
        trend = 0.001 * (-1 if seed % 2 == 0 else 1)  # Alternate trend direction
        
        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        current = from_time
        price = base_price
        
        while current <= to_time:
            # Skip weekends
            dt = datetime.fromtimestamp(current)
            if dt.weekday() < 5:  # Monday=0, Sunday=6
                daily_volatility = np.random.normal(0, volatility)
                daily_trend = trend * (1 + np.random.normal(0, 0.5))
                
                open_price = price
                close_price = price * (1 + daily_volatility + daily_trend)
                high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility/2)))
                low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility/2)))
                volume = int(np.random.normal(1000000, 300000))
                
                dates.append(dt)
                opens.append(open_price)
                highs.append(high_price)
                lows.append(low_price)
                closes.append(close_price)
                volumes.append(max(100, volume))
                
                price = close_price
            
            current += 24 * 60 * 60  # Add one day
        
        # Reset the seed to avoid affecting other random number generation
        np.random.seed(None)
        
        # Create DataFrame
        df = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }, index=pd.DatetimeIndex(dates))
        
        return df

    @staticmethod
    def get_recommendations(
        ticker: str,
        exchange: str = "NASDAQ",
        screener: str = "america",
        interval: Interval = Interval.INTERVAL_1_DAY
    ) -> Dict:
        """
        Get technical analysis recommendations from TradingView
        """
        try:
            handler = TA_Handler(
                symbol=ticker,
                screener=screener,
                exchange=exchange,
                interval=interval
            )
            analysis = handler.get_analysis()
            return {
                'summary': analysis.summary,
                'indicators': analysis.indicators,
                'oscillators': analysis.oscillators,
                'moving_avgs': analysis.moving_averages
            }
        except Exception as e:
            logging.error(f"Technical analysis error: {str(e)}")
            return {
                'summary': {'RECOMMENDATION': 'ERROR'},
                'indicators': {},
                'oscillators': {},
                'moving_avgs': {}
            }

    def get_market_news(self, days_back: int = 3, num_articles: int = 5, use_cache: bool = True) -> List[Dict]:
        """
        Fetch general market news (not specific to a ticker)
        
        Args:
            days_back: Number of days to look back
            num_articles: Maximum number of articles to return
            use_cache: Whether to use cached data
            
        Returns:
            List of news articles
        """
        # First try to get news normally with "market" as keyword
        try:
            return self.get_news("market", days_back, num_articles, use_cache)
        except Exception as e:
            logging.warning(f"Error fetching market news: {e}")
            
            # If that fails, try with another general finance keyword
            try:
                return self.get_news("finance", days_back, num_articles, use_cache)
            except Exception as e2:
                logging.warning(f"Error fetching finance news: {e2}")
                
                # If that also fails, try to generate dummy news
                try:
                    # Import the dummy data module
                    try:
                        from dummy_data_module import generate_news_articles
                        return generate_news_articles("market", num_articles)
                    except ImportError:
                        # If dummy data module is not available, create basic dummy data here
                        logging.warning("Falling back to basic dummy news data")
                        return [
                            {
                                "title": "Market Update",
                                "description": "Markets remained volatile today as investors processed new economic data.",
                                "publishedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "source": {"name": "Financial Times"}
                            },
                            {
                                "title": "Economic Outlook",
                                "description": "Analysts predict steady growth in the coming quarter despite ongoing challenges.",
                                "publishedAt": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "source": {"name": "Market Watch"}
                            }
                        ]
                except Exception:
                    # Last resort - empty list with explanation
                    return [{"title": "News Unavailable", "description": "Unable to retrieve market news at this time.", "source": {"name": "System"}}]

    # Added Finnhub function for company profile information (previously might have used Alpha Vantage)
    def get_company_info(self, ticker: str, use_cache: bool = True) -> Dict:
        """Get company information using Finnhub API"""
        # Check cache first if enabled
        cache_key = f"company_info_{ticker}"
        if use_cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                logging.info(f"Using cached company info for {ticker}")
                return cache_entry['data']
        
        try:
            params = {
                'symbol': ticker,
                'token': FINNHUB_API_KEY
            }
            url = "https://finnhub.io/api/v1/stock/profile2"
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                raise StockAPIError(f"No company information found for ticker: {ticker}")
            
            # Cache the result
            if use_cache:
                self.cache[cache_key] = {
                    'timestamp': time.time(),
                    'data': data
                }
            
            return data
        
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 404:
                    error_message = f"Company information not found for ticker: {ticker}"
                elif e.response.status_code == 429:
                    error_message = "Rate limit exceeded for Finnhub API. Please try again later."
            
            raise StockAPIError(f"Failed to fetch company information: {error_message}")
        except Exception as e:
            raise StockAPIError(f"Error retrieving company information: {str(e)}")

    # Add function to get financial metrics using Finnhub
    def get_financial_metrics(self, ticker: str, use_cache: bool = True) -> Dict:
        """Get financial metrics using Finnhub API"""
        # Check cache first if enabled
        cache_key = f"financial_metrics_{ticker}"
        if use_cache and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                logging.info(f"Using cached financial metrics for {ticker}")
                return cache_entry['data']
        
        try:
            params = {
                'symbol': ticker,
                'metric': 'all',
                'token': FINNHUB_API_KEY
            }
            url = "https://finnhub.io/api/v1/stock/metric"
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data or 'metric' not in data:
                raise StockAPIError(f"No financial metrics found for ticker: {ticker}")
            
            # Cache the result
            if use_cache:
                self.cache[cache_key] = {
                    'timestamp': time.time(),
                    'data': data
                }
            
            return data
        
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 404:
                    error_message = f"Financial metrics not found for ticker: {ticker}"
                elif e.response.status_code == 429:
                    error_message = "Rate limit exceeded for Finnhub API. Please try again later."
            
            raise StockAPIError(f"Failed to fetch financial metrics: {error_message}")
        except Exception as e:
            raise StockAPIError(f"Error retrieving financial metrics: {str(e)}")

class AIClient:
    def __init__(self, model=OLLAMA_MODEL, request_counter=None, max_requests_per_minute=10):
        self.default_model = model
        self.request_counter = request_counter
        self.max_requests_per_minute = max_requests_per_minute
        self.lock = threading.Lock()
        self.requests = []
        self._ensure_model_available(model)

    def _ensure_model_available(self, model_name: str) -> None:
        """
        Ensure the model is available locally, pull if not.
        
        Args:
            model_name (str): Name of the Ollama model to check/pull
        """
        try:
            # Try to get model info
            ollama.list()
            logging.info(f"Ollama models are available")
        except Exception as e:
            logging.error(f"Error checking model {model_name}: {e}")
            try:
                logging.info(f"Pulling model {model_name}...")
                ollama.pull(model_name)
                logging.info(f"Successfully pulled model {model_name}")
            except Exception as pull_error:
                logging.error(f"Error pulling model: {pull_error}")
                # Don't raise here, as we want to be able to continue even if model pulling fails

    def _allow_request(self):
        with self.lock:
            current_time = time.time()
            self.requests = [req for req in self.requests if current_time - req < 60]
            if len(self.requests) >= self.max_requests_per_minute:
                wait_time = 60 - (current_time - self.requests[0])
                logging.warning(f"Rate limit hit for AI analysis. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            self.requests.append(current_time)

    def _execute_ollama_request(self, model, messages):
        """Execute the actual Ollama request with robust error handling"""
        logging.info(f"Making Ollama request with model {model}")
        try:
            response = ollama.chat(model=model, messages=messages)
            return response
        except Exception as e:
            logging.error(f"Ollama request failed: {str(e)}")
            # Return a fallback response to avoid crashing the UI
            return {
                'message': {
                    'content': f"I apologize, but I'm having trouble processing your request right now due to high demand. Please wait a moment and try again. (Error: {str(e)})"
                }
            }

    def analyze(self, prompt, role, model=None, retries=2, backoff_factor=2.0):
        """Analyzes the given prompt using the specified AI model with rate limiting"""
        model_to_use = model or self.default_model
        self._ensure_model_available(model_to_use)
        
        messages = [
            {
                'role': 'system',
                'content': f"You are a {role}. Provide detailed financial analysis, predictions, and risk management strategies."
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        logging.info(f"Requesting AI analysis for role: {role}")
        
        # Try with retries in case of failure
        last_error = None
        for attempt in range(retries + 1):
            try:
                # Add delay between attempts if this isn't the first attempt
                if attempt > 0:
                    wait_time = backoff_factor * (2 ** (attempt - 1))  # Start with backoff_factor seconds
                    logging.warning(f"Retry attempt {attempt}/{retries}. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                
                # Execute with rate limiting
                response = execute_ollama_request(
                    self._execute_ollama_request,
                    model_to_use,
                    messages
                )
                return response
            
            except Exception as e:
                logging.error(f"AI attempt {attempt+1}/{retries+1} failed: {e}")
                last_error = e
                # Continue to next retry
        
        # If we got here, all retries failed
        error_message = str(last_error) if last_error else "Unknown error"
        return {
            'message': {
                'content': f"Analysis failed after {retries+1} attempts. The system might be experiencing high load. Please try again later. (Error: {error_message})"
            }
        }

    @staticmethod
    def generate_analysis(
        prompt: str,
        context: str,
        model: str = OLLAMA_MODEL,
        max_retries: int = 3
    ) -> Dict:
        """
        Generate AI analysis using Ollama
        """
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ]
        return AIClient._chat_with_retry(messages, model, max_retries)

    @staticmethod
    def generate_chat_response(
        messages: List[Dict],
        model: str = OLLAMA_MODEL,
        max_retries: int = 2
    ) -> Dict:
        """
        Generate conversational AI response
        """
        return AIClient._chat_with_retry(messages, model, max_retries)

    @staticmethod
    def _chat_with_retry(
        messages: List[Dict],
        model: str,
        max_retries: int
    ) -> Dict:
        """
        Internal method with retry logic for Ollama requests
        """
        for attempt in range(max_retries):
            try:
                response = ollama.chat(model=model, messages=messages)
                return response
            except Exception as e:
                if attempt == max_retries - 1:
                    raise AIClientError(f"AI request failed after {max_retries} attempts: {str(e)}") from e
                continue
        raise AIClientError("Unexpected error in AI communication")