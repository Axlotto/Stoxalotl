# api_client.py
import requests
from datetime import datetime, timedelta
from tradingview_ta import TA_Handler, Interval
from typing import Dict, List, Optional, Union
from config import FINNHUB_API_KEY, FINNHUB_API_URL, NEWS_API_KEY, NEWS_API_URL, OLLAMA_MODEL
from cache import Cache
import ollama  # Add this import
import time  # Add this import

# Initialize cache with a TTL of 5 minutes
cache = Cache(ttl=300)

class StockAPI:
    def __init__(self, request_counter=None):
        self.request_counter = request_counter

    def get_stock(self, ticker: str, retries: int = 3, backoff_factor: float = 0.3) -> Dict:
        """Fetch stock data using Finnhub API with caching and retry mechanism"""
        cache_key = f"stock_{ticker}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            if self.request_counter:
                self.request_counter.increment_cache()
            return cached_data

        if self.request_counter:
            self.request_counter.increment_api()

        for attempt in range(retries):
            try:
                params = {
                    'symbol': ticker,
                    'token': FINNHUB_API_KEY
                }
                response = requests.get(f"{FINNHUB_API_URL}/quote", params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                if not data:
                    raise StockAPIError(f"No data found for ticker: {ticker}")
                cache.set(cache_key, data)
                return data
            except requests.exceptions.RequestException as e:
                if hasattr(e.response, 'status_code') and e.response.status_code == 429:
                    wait_time = backoff_factor * (2 ** attempt)
                    print(f"Rate limit hit! Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise StockAPIError(f"Failed to fetch stock data: {str(e)}") from e

        raise StockAPIError("Exceeded maximum retries for fetching stock data")

    def get_news(self, ticker: str, days_back: int = 3, num_articles: int = 3, retries: int = 3, backoff_factor: float = 0.3) -> List[Dict]:
        if self.request_counter:
            self.request_counter.increment('news_api')
        """
        Fetch news articles related to the stock with caching and retry mechanism
        """
        cache_key = f"news_{ticker}_{days_back}_{num_articles}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        for attempt in range(retries):
            try:
                params = {
                    'q': ticker,
                    'from': (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d'),
                    'sortBy': 'relevancy',
                    'language': 'en',
                    'apiKey': NEWS_API_KEY,
                    'pageSize': num_articles
                }
                
                response = requests.get(NEWS_API_URL, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                if data['status'] != 'ok':
                    raise StockAPIError(f"News API error: {data.get('message', 'Unknown error')}")
                
                articles = data.get('articles', [])
                cache.set(cache_key, articles)
                return articles
            except requests.exceptions.RequestException as e:
                if response.status_code == 429:  # Too Many Requests
                    wait_time = backoff_factor * (2 ** attempt)
                    print(f"Error 429 again... Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise StockAPIError(f"News request failed: {str(e)}") from e
            except Exception as e:
                raise StockAPIError(f"News processing error: {str(e)}") from e

        raise StockAPIError("Exceeded maximum retries for fetching news")

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
            raise StockAPIError(f"Technical analysis failed: {str(e)}") from e

class AIClient:
    def __init__(self, model=OLLAMA_MODEL, request_counter=None):
        self.default_model = model
        self.request_counter = request_counter
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
        except Exception as e:
            print(f"Error checking model {model_name}: {e}")
            try:
                print(f"Pulling model {model_name}...")
                ollama.pull(model_name)
                print(f"Successfully pulled model {model_name}")
            except Exception as pull_error:
                print(f"Error pulling model: {pull_error}")
                raise

    def analyze(self, prompt, role, model=None):
        if self.request_counter:
            self.request_counter.increment('ai_api')
        """Analyzes the given prompt using the specified AI model."""
        try:
            model_to_use = model or self.default_model
            self._ensure_model_available(model_to_use)
            
            response = ollama.chat(
                model=model_to_use,
                messages=[
                    {
                        'role': 'system',
                        'content': f"You are a {role}. Provide detailed financial analysis, predictions, and risk management strategies."
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            return response
        except Exception as e:
            print(f"Error during AI analysis: {e}")
            return {'message': {'content': f"Analysis failed: {str(e)}"}}

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

class StockAPIError(Exception):
    """Custom exception for Stock API errors"""
    pass

class AIClientError(Exception):
    """Custom exception for AI client errors"""
    pass