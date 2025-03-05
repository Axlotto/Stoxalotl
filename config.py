# config.py
import os
import sys

# Import dotenv_loader first to make sure environment variables are loaded
import dotenv_loader  # Load .env before using os.getenv

# Application Colors - More refined and customizable
COLOR_PALETTES = {
    "Dark": {
        "background": "#121212",       # Deeper dark grey
        "surface": "#212121",          # Elevated surface
        "primary": "#BB86FC",          # Purple (fixed from potentially invalid #BB value)
        "secondary": "#3700B3",         # Darker purple
        "accent": "#03DAC6",            # Teal accent
        "text": "#FFFFFF",              # Pure white
        "text-secondary": "#BDBDBD",     # Light grey
        "positive": "#4CAF50",          # Green
        "negative": "#F44336",          # Red
        "border": "#303030"           # Dark border
    },
    "Light": {
        "background": "#FAFAFA",       # Off-white
        "surface": "#FFFFFF",          # White
        "primary": "#6200EE",           # Deep purple
        "secondary": "#B388FF",         # Light purple
        "accent": "#03DAC6",            # Teal accent
        "text": "#212121",              # Dark grey
        "text-secondary": "#757575",     # Medium grey
        "positive": "#388E3C",          # Dark green
        "negative": "#D32F2F",          # Dark red
        "border": "#E0E0E0"           # Light border
    },
    "Custom": {  # Placeholder for user-defined colors
        "background": "#1E1E1E",
        "surface": "#474747",
        "primary": "#6366F1",
        "secondary": "#1E1E1E",
        "accent": "#818CF8",
        "text": "#F8FAFC",
        "text-secondary": "#94A3B8",
        "positive": "#34D399",
        "negative": "#F87171",
        "border": "#1E1E1E"
    }
}

# Typography Settings - Expanded font choices
FONT_CHOICES = {
    "Segoe UI": "Segoe UI, sans-serif",
    "Roboto": "Roboto, sans-serif",
    "Open Sans": "Open Sans, sans-serif",
    "Lato": "Lato, sans-serif",
    "Montserrat": "Montserrat, sans-serif"
}

FONT_FAMILY = "Segoe UI, sans-serif"  # Default font

FONT_SIZES = {
    "title": 24,       # Larger title
    "header": 18,
    "body": 14,
    "small": 12
}

# AI Configuration
OLLAMA_MODEL = "deepseek-r1:1.5b"
CHAT_MODEL = "llama3.2:1b"  # Add this line

# News API Configuration
NEWS_API_KEY = os.getenv("NEWSAPI_KEY", "c91f9673406647e280aa6faf87ef892a")  # Use env var as primary source
if not NEWS_API_KEY:
    raise ValueError("Please set a valid NEWSAPI_KEY in API.env")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Finnhub API Configuration
FINNHUB_KEY = os.getenv("FINNHUB_KEY")
if not FINNHUB_KEY:
    raise ValueError("Please set a valid FINNHUB_KEY in API.env")
FINNHUB_API_URL = "https://finnhub.io/api/v1"  # Keep this for reference but use direct URLs in code

# Chart Configuration - More options
CHART_CONFIG = {
    "default_period": "3mo",       # Default historical data period
    "interval": "1d",              # Default chart interval
    "volume_height": 120,          # Height of volume subplot in pixels
    "candle_width": 0.7,           # Width of candlesticks (0-1)
    "grid_color": "#555555",        # Grid line color
    "axis_color": "#EEEEEE",        # Axis line and tick color
    "label_color": "#EEEEEE"       # Axis label color
}

# UI Element Customization
UI_CONFIG = {
    "border_radius": 10,            # Rounded corners for widgets
    "padding": 14,                 # Spacing within widgets
    "animation_speed": 300,        # Animation speed in ms
    "button_style": "elevated",     # Button style (e.g., "modern", "classic")
    "accent_color": "#29b6f6",      # A vibrant accent color
    "font_color": "#e0e0e0",        # Readable font color
    "hover_brightness": 1.1,        # Brightness increase on hover
    "shadow_depth": 3,              # Depth of shadows
    "transition_duration": 0.2      # Transition duration in seconds
}

# Technical Analysis Settings
TA_CONFIG = {
    "screener": "america",
    "exchange": "NASDAQ",
    "interval": "1D"
}

# Configuration for dummy data generation (when APIs fail)
DUMMY_DATA_CONFIG = {
    "use_fallback": True,  # Whether to use dummy data when API calls fail
    "realistic_patterns": True,  # Whether to generate realistic price patterns
    "seed_from_ticker": True,  # Use ticker name to seed random generator for consistent results
    "volatility": 0.02,  # Base volatility for dummy data
    "base_price_range": (50, 250)  # Range of base prices for dummy data
}

# Application Defaults
DEFAULTS = {
    "investment_amount": 10000,    # Default investment amount
    "timeframe": 30,                # Default investment days
    "profit_target": 0.10           # Default profit target (10%)
}