# api_client.py
import yfinance as yf
import ollama
import requests
from datetime import datetime, timedelta
from tradingview_ta import TA_Handler, Interval
from typing import Dict, List, Optional, Union
from config import NEWS_API_KEY, NEWS_API_URL, OLLAMA_MODEL

class StockAPI:
    @staticmethod
    def get_stock(ticker: str) -> yf.Ticker:
        """
        Fetch stock data using yfinance
        """
        try:
            stock = yf.Ticker(ticker)
            # Fetch live data to ensure the ticker is valid and data is available
            stock_info = stock.info
            if not stock_info:
                raise StockAPIError(f"No data found for ticker: {ticker}")
            return stock
        except Exception as e:
            raise StockAPIError(f"Failed to fetch stock data: {str(e)}") from e

    @staticmethod
    def get_news(ticker: str, days_back: int = 3, num_articles: int = 3) -> List[Dict]:
        """
        Fetch news articles related to the stock
        """
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
            
            return data.get('articles', [])
            
        except requests.exceptions.RequestException as e:
            raise StockAPIError(f"News request failed: {str(e)}") from e
        except Exception as e:
            raise StockAPIError(f"News processing error: {str(e)}") from e

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
    def __init__(self, model=OLLAMA_MODEL):
        self.default_model = model
        self._ensure_model_available(model)

    def _ensure_model_available(self, model_name):
        """Ensure the model is pulled and available"""
        try:
            # Try to get model info - this will fail if model isn't pulled
            ollama.show(model_name)
        except Exception as e:
            if "not found" in str(e):
                print(f"Model {model_name} not found. Pulling now...")
                try:
                    ollama.pull(model_name)
                    print(f"Successfully pulled model {model_name}")
                except Exception as pull_error:
                    print(f"Error pulling model: {pull_error}")
                    raise

    def analyze(self, prompt, role, model=None):
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