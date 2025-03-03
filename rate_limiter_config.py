"""
Configuration for rate limiters.
Adjust these values based on your API usage requirements.
"""

# YFinance rate limiting
# YFinance doesn't publish official rate limits, but users report
# issues with more than a few requests per second
YFINANCE_RATE_LIMIT = {
    "max_rate": 2.0,      # Maximum requests per second
    "burst_limit": 5,     # Maximum burst size
    "wait_on_limit": True # Wait when rate limited
}

# Finnhub API rate limiting
# Official rate limit is 60 requests per minute (1 per second) for free tier
# Set to 0.8 to stay under the limit with some margin
FINNHUB_RATE_LIMIT = {
    "max_rate": 0.8,      # Maximum requests per second
    "burst_limit": 3,     # Maximum burst size
    "wait_on_limit": True # Wait when rate limited
}

# News API rate limiting
# Free tier has limit of 100 requests per day (very restrictive)
NEWS_API_RATE_LIMIT = {
    "max_rate": 0.2,      # Maximum requests per second (1 per 5 seconds)
    "burst_limit": 2,     # Maximum burst size
    "wait_on_limit": True # Wait when rate limited
}

# Ollama (local AI) rate limiting
# This is to prevent overloading your local system
OLLAMA_RATE_LIMIT = {
    "max_rate": 0.2,      # Maximum requests per second (1 per 5 seconds)
    "burst_limit": 1,     # Maximum burst size
    "wait_on_limit": True # Wait when rate limited
}

# Queue configuration
QUEUE_CONFIG = {
    "max_queue_size": 100,  # Maximum size of request queue
    "workers": {
        "yfinance": 2,      # Number of worker threads
        "finnhub": 1,       # Finnhub has stricter limits
        "news_api": 1,      # News API has very strict limits
        "ollama": 1         # Ollama is resource intensive
    }
}

# Cache configuration
CACHE_CONFIG = {
    "enabled": True,        # Enable caching
    "ttl": {                # Time-to-live in seconds
        "stock_data": 300,  # 5 minutes for stock data
        "chart_data": 600,  # 10 minutes for chart data
        "news": 1800,       # 30 minutes for news
        "analysis": 3600    # 60 minutes for AI analysis
    }
}

# Apply these configurations by updating rate_limiter.py:
# 
# from rate_limiter_config import YFINANCE_RATE_LIMIT, FINNHUB_RATE_LIMIT, ...
#
# finnhub_limiter = RateLimiter(
#     max_rate=FINNHUB_RATE_LIMIT["max_rate"],
#     burst_limit=FINNHUB_RATE_LIMIT["burst_limit"], 
#     wait_on_limit=FINNHUB_RATE_LIMIT["wait_on_limit"],
#     name="Finnhub"
# )
