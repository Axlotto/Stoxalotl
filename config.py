# config.py
# Application Colors
COLORS = {
    "background": "#1e1e1e",    # Dark grey
    "surface": "#474747",       # Soft grey
    "primary": "#6366F1",       # Indigo
    "secondary": "#1e1e1e",     # Dark grey
    "accent": "#818CF8",        # Light indigo
    "text": "#F8FAFC",          # Off-white
    "text-secondary": "#94A3B8",# Gray-blue
    "positive": "#34D399",      # Mint green
    "negative": "#F87171",      # Coral red
    "border": "#1e1e1e"         # Dark grey
}

# Yellow for neutral/mid-range values
YELLOW = "#FFEB3B"

# Typography Settings
FONT_FAMILY = "Segoe UI"
FONT_SIZES = {
    "title": 20,
    "header": 16,
    "body": 13,
    "small": 11
}

# AI Configuration
OLLAMA_MODEL = "deepseek-r1:1.5b"

# News API Configuration
NEWS_API_KEY = "your_api_key_here"  # Replace with your actual key
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Chart Configuration
CHART_CONFIG = {
    "default_period": "3mo",     # Default historical data period
    "interval": "1d",            # Default chart interval
    "volume_height": 100,        # Height of volume subplot in pixels
    "candle_width": 0.8          # Width of candlesticks (0-1)
}

# Technical Analysis Settings
TA_CONFIG = {
    "screener": "america",
    "exchange": "NASDAQ",
    "interval": "1D"
}

# Application Defaults
DEFAULTS = {
    "investment_amount": 10000,  # Default investment amount
    "timeframe": 30              # Default investment days
}