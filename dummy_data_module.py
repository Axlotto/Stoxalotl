"""
Dummy Data Generator Module
Provides realistic financial data for testing and development purposes
when the actual API services are unavailable.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

def generate_stock_candles(ticker, from_timestamp, to_timestamp):
    """
    Generate realistic-looking stock candle data
    
    Args:
        ticker (str): Stock symbol
        from_timestamp (int): Start timestamp
        to_timestamp (int): End timestamp
        
    Returns:
        pd.DataFrame: DataFrame with OHLCV data
    """
    logging.info(f"Generating dummy candle data for {ticker}")
    
    # Calculate number of days
    days_diff = (to_timestamp - from_timestamp) // (60 * 60 * 24)
    num_days = min(max(days_diff, 5), 365)  # Between 5 days and 1 year
    
    # Use the ticker string to create a seed for predictable randomness
    ticker_seed = sum(ord(c) for c in ticker)
    np.random.seed(ticker_seed)
    
    # Base parameters - vary by ticker for unique patterns
    base_price = 50.0 + (ticker_seed % 200)  # Range: $50-$250
    volatility = 0.01 + (ticker_seed % 10) * 0.001  # Range: 1%-2% daily volatility
    trend = 0.0005 * (-1 if ticker_seed % 2 == 0 else 1)  # Small up/down trend
    
    # Generate dates, ensuring we only use trading days (Mon-Fri)
    dates = []
    current_date = datetime.fromtimestamp(from_timestamp)
    
    while len(dates) < num_days:
        if current_date.weekday() < 5:  # Monday=0, Friday=4
            dates.append(current_date)
        current_date += timedelta(days=1)
        
        # Stop if we've gone past the end timestamp
        if current_date.timestamp() > to_timestamp:
            break
    
    # Generate price data
    price = base_price
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []
    
    # Add some market cycles (bull/bear periods)
    cycle_period = num_days // 3
    cycle_amplitude = 0.2  # 20% cycle
    
    for i, date in enumerate(dates):
        # Apply market cycle influence
        cycle_influence = np.sin(2 * np.pi * i / cycle_period) * cycle_amplitude * 0.01
        
        # Generate daily random walk
        daily_return = np.random.normal(trend + cycle_influence, volatility)
        
        # Opening price is previous close or base price for first day
        if i == 0:
            open_price = base_price
        else:
            open_price = closes[-1]
        
        # Calculate OHLC with realistic relationships
        close_price = open_price * (1 + daily_return)
        
        # High is above both open and close
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility/2)))
        
        # Low is below both open and close
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility/2)))
        
        # Volume - higher on more volatile days
        vol_factor = 1 + 5 * abs(daily_return) / volatility  # Scale volume with volatility
        volume = int(np.random.normal(1000000, 300000) * vol_factor)
        volume = max(100, volume)  # Ensure positive volume
        
        # Store values
        opens.append(open_price)
        closes.append(close_price)
        highs.append(high_price)
        lows.append(low_price)
        volumes.append(volume)
        
        # Update price for next iteration
        price = close_price
    
    # Reset the random seed
    np.random.seed(None)
    
    # Create DataFrame
    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)
    
    return df

def generate_stock_quote(ticker):
    """
    Generate a realistic stock quote with current price info
    
    Args:
        ticker (str): Stock symbol
        
    Returns:
        dict: Dictionary with quote data
    """
    # Use ticker to seed random generator for consistent results
    ticker_seed = sum(ord(c) for c in ticker)
    np.random.seed(ticker_seed)
    
    # Generate base price based on ticker
    base_price = 50.0 + (ticker_seed % 200)
    
    # Add some randomization
    current_price = base_price * (1 + np.random.normal(0, 0.02))
    prev_close = current_price * (1 + np.random.normal(0, 0.01))
    day_high = current_price * (1 + abs(np.random.normal(0, 0.01)))
    day_low = current_price * (1 - abs(np.random.normal(0, 0.01)))
    day_open = prev_close * (1 + np.random.normal(0, 0.005))
    
    # Reset random seed
    np.random.seed(None)
    
    return {
        'c': current_price,  # Current price
        'pc': prev_close,    # Previous close
        'o': day_open,       # Open price
        'h': day_high,       # High price
        'l': day_low,        # Low price
        'v': int(np.random.normal(1000000, 300000)),  # Volume
        't': int(datetime.now().timestamp()),  # Timestamp
        's': 'ok'  # Status
    }

def generate_news_articles(ticker, count=3):
    """
    Generate dummy news articles for a ticker
    
    Args:
        ticker (str): Stock symbol
        count (int): Number of articles to generate
        
    Returns:
        list: List of news article dictionaries
    """
    articles = []
    
    # Common headline templates
    headlines = [
        "{ticker} Reports Strong Quarterly Earnings",
        "{ticker} Announces New Product Line",
        "{ticker} Stock Rises on Market Optimism",
        "{ticker} Expands into New Markets",
        "Analysts Upgrade {ticker} Stock Rating",
        "{ticker} CEO Discusses Future Growth Plans",
        "{ticker} Forms Strategic Partnership",
        "Investors React to {ticker}'s Latest Financial Report",
        "{ticker} Stock Falls Despite Positive Earnings",
        "{ticker} Introduces Innovative Technology"
    ]
    
    # Description templates
    descriptions = [
        "{ticker} reported quarterly earnings that exceeded analyst expectations, driven by strong performance in its core business segments.",
        "The company announced plans to expand its product portfolio, aiming to capture additional market share in emerging sectors.",
        "Market sentiment toward {ticker} improved following positive industry trends and favorable economic indicators.",
        "In a strategic move, {ticker} is entering new geographic markets, potentially adding significant revenue streams.",
        "Several financial analysts have revised their outlook on {ticker}, citing improved fundamentals and growth prospects.",
        "During an investor call, {ticker}'s CEO outlined ambitious plans for technology investment and market expansion.",
        "A new partnership between {ticker} and industry leaders aims to accelerate innovation and product development cycles.",
        "Despite beating earnings expectations, investors had mixed reactions to {ticker}'s forward-looking statements.",
        "The stock price declined following concerns about increasing competition and margin pressures.",
        "The company unveiled new technology that could disrupt existing market dynamics and strengthen its competitive position."
    ]
    
    # Use ticker to seed random generator for consistent but varied results
    ticker_seed = sum(ord(c) for c in ticker)
    np.random.seed(ticker_seed)
    
    # Generate articles
    for i in range(count):
        # Select headline and description templates
        headline_idx = (ticker_seed + i) % len(headlines)
        desc_idx = (ticker_seed + i * 3) % len(descriptions)
        
        # Format with ticker
        headline = headlines[headline_idx].format(ticker=ticker)
        description = descriptions[desc_idx].format(ticker=ticker)
        
        # Create publication date (newer articles first)
        pub_date = (datetime.now() - timedelta(days=i, hours=np.random.randint(0, 12))).isoformat()
        
        # Create article
        article = {
            'title': headline,
            'description': description,
            'publishedAt': pub_date,
            'source': {'name': f"Financial Source {(ticker_seed + i) % 5 + 1}"},
            'url': f"https://example.com/news/{ticker.lower()}-{i+1}",
            'urlToImage': f"https://example.com/images/{ticker.lower()}-{i+1}.jpg"
        }
        
        articles.append(article)
    
    # Reset random seed
    np.random.seed(None)
    
    return articles
