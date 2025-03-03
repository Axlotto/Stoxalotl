"""
Fallback module for handling API failures gracefully
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def get_fallback_stock_quote(ticker):
    """
    Generate a fallback stock quote when API calls fail
    """
    logging.info(f"Using fallback stock data for {ticker}")
    
    # Use ticker to seed random generator for consistent results
    seed = sum(ord(c) for c in ticker)
    np.random.seed(seed)
    
    # Generate base values based on ticker
    base = 100.0 + (seed % 300)  # Base price: $100-$400
    
    # Generate realistic values
    current = base * (1 + np.random.normal(0, 0.03))
    prev_close = base * (1 + np.random.normal(0, 0.02))
    day_open = (current + prev_close) / 2 + np.random.normal(0, 0.5)
    day_high = max(current, day_open) * (1 + abs(np.random.normal(0, 0.01)))
    day_low = min(current, day_open) * (1 - abs(np.random.normal(0, 0.01)))
    
    # Reset seed
    np.random.seed(None)
    
    return {
        'c': current,  # Current price
        'pc': prev_close,  # Previous close
        'o': day_open,  # Open price
        'h': day_high,  # High price
        'l': day_low,  # Low price
        'v': int(np.random.normal(1000000, 200000)),  # Volume
        't': int(datetime.now().timestamp()),  # Timestamp
        'dp': ((current - prev_close) / prev_close) * 100,  # Percentage change
        'd': current - prev_close,  # Dollar change
    }

def get_fallback_news(ticker="market", count=5):
    """
    Generate fallback news articles
    """
    logging.info(f"Using fallback news for {ticker}")
    
    # Generic business news templates
    headlines = [
        "{ticker} Shows Strong Performance in Recent Trading",
        "Analysts Weigh In On {ticker}'s Market Position",
        "Economic Trends Affecting {ticker} and Similar Stocks",
        "{ticker} Announces Quarterly Results",
        "Market Volatility Impacts {ticker} Trading",
        "Industry Outlook: What It Means for {ticker}",
        "{ticker} Leadership Discusses Future Strategy"
    ]
    
    news_list = []
    now = datetime.now()
    
    for i in range(count):
        # Pick a headline based on ticker and position
        headline_idx = (sum(ord(c) for c in ticker) + i) % len(headlines)
        headline = headlines[headline_idx].format(ticker=ticker.upper())
        
        # Create article
        article = {
            "title": headline,
            "description": f"This is a placeholder description for news about {ticker}. "
                           f"This would normally contain a summary of the article content.",
            "source": {"name": "Financial News Daily"},
            "publishedAt": (now - timedelta(hours=i*4)).isoformat(),
            "url": "#",
            "urlToImage": None
        }
        news_list.append(article)
    
    return news_list

def get_fallback_chart_data(ticker, time_period="3M"):
    """
    Generate fallback chart data when API calls fail
    
    Args:
        ticker: Stock symbol
        time_period: Time period string (1D, 1W, 1M, 3M, 6M, 1Y)
    
    Returns:
        pandas DataFrame with OHLCV data
    """
    logging.info(f"Using fallback chart data for {ticker} ({time_period})")
    
    # Determine number of data points based on time period
    if time_period == "1D":
        days = 1
        points = 24  # Hourly data
    elif time_period == "1W":
        days = 7
        points = 7 * 8  # 8 points per day
    elif time_period == "1M":
        days = 30
        points = 30
    elif time_period == "3M":
        days = 90
        points = 90
    elif time_period == "6M":
        days = 180
        points = 180
    elif time_period == "1Y":
        days = 365
        points = 260  # Trading days in a year
    else:
        days = 90  # Default to 90 days
        points = 90
    
    # Seed random generator based on ticker for consistent results
    seed = sum(ord(c) for c in ticker)
    np.random.seed(seed)
    
    # Base price and trend based on ticker
    base_price = 100.0 + (seed % 400)  # Range: $100-$500
    trend = 0.0002 * (-1 if seed % 2 == 0 else 1)  # Small up/down trend
    volatility = 0.01 + (seed % 10) * 0.002  # Range: 1%-3% volatility
    
    # Generate price data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # For daily data, generate only business days
    if points <= days:
        # Create business day date range
        dates = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Monday=0, Friday=4
                dates.append(current)
            current += timedelta(days=1)
        
        # Trim to desired number of points
        dates = dates[-points:]
    else:
        # For intraday data, use evenly spaced times
        delta = timedelta(days=days) / points
        dates = [start_date + delta * i for i in range(points)]
    
    # Generate OHLC prices with random walk
    closes = []
    opens = []
    highs = []
    lows = []
    volumes = []
    
    price = base_price
    for i in range(len(dates)):
        # Add cyclical pattern
        cycle = 0.005 * np.sin(i / 20)
        
        # Calculate day's move with some randomness
        day_change = np.random.normal(trend + cycle, volatility)
        
        # Set open price (previous close or base for first day)
        if i == 0:
            open_price = base_price
        else:
            open_price = closes[-1]
        
        # Calculate close
        close_price = open_price * (1 + day_change)
        
        # Set high and low with randomness
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility/2)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility/2)))
        
        # Add volume with some correlation to price movement
        volume = int(np.random.normal(1000000, 200000) * (1 + abs(day_change) * 10))
        volume = max(1000, volume)  # Ensure positive volume
        
        opens.append(open_price)
        closes.append(close_price)
        highs.append(high_price)
        lows.append(low_price)
        volumes.append(volume)
        
        # Update for next iteration
        price = close_price
    
    # Reset random seed
    np.random.seed(None)
    
    # Create DataFrame
    return pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=pd.DatetimeIndex(dates))
