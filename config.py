# config.py
# Application Colors - More refined and customizable
COLOR_PALETTES = {
    "Dark": {
        "background": "#121212",       # Deeper dark grey
        "surface": "#212121",          # Elevated surface
        "primary": "#BB86FC",           # Purple
        "secondary": "#3700B3",         # Darker purple
        "accent": "#03DAC6",            # Teal accent
        "text": "#FFFFFF",              # Pure white
        "text-secondary": "#BDBDBD",     # Light grey
        "positive": "#4CAF50",          # Green
        "negative": "#F44336",          # Red
        "border": "#303030",           # Dark border
        "card_up": "#1e3320",           # Green background for uptrend
        "card_down": "#3d1f1f",         # Red background for downtrend
        "card_neutral": "#2d2d2d"       # Neutral background
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

# News API Configuration
NEWS_API_KEY = "c91f9673406647e280aa6faf87ef892a"  # Replace with your actual key
NEWS_API_URL = "https://newsapi.org/v2/everything"

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
    "border_radius": 8,            # Rounded corners for widgets
    "padding": 12,                 # Spacing within widgets
    "animation_speed": 250,        # Animation speed in ms
    "button_style": "modern"       # Button style (e.g., "modern", "classic")
}

# Technical Analysis Settings
TA_CONFIG = {
    "screener": "america",
    "exchange": "NASDAQ",
    "interval": "1D"
}

# Application Defaults
DEFAULTS = {
    "investment_amount": 10000,    # Default investment amount
    "timeframe": 30                # Default investment days
}