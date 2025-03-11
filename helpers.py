# helpers.py
import re
from config import COLOR_PALETTES, FONT_FAMILY, FONT_SIZES
from ticker_utils import (
    validate_ticker, 
    normalize_ticker, 
    find_similar_ticker as find_closest_ticker,
    get_levenshtein_distance
)
from ticker_utils import COMMON_MISSPELLINGS as COMMON_TICKER_CORRECTIONS

def parse_recommendations(text):
    """Extract recommendation points from analysis text"""
    import re
    
    # Look for bullet points or numbered lists
    bullet_pattern = r'(?:^|\n)[\s]*[-•*][\s]+(.*?)(?=$|\n)'
    numbered_pattern = r'(?:^|\n)[\s]*\d+\.[\s]+(.*?)(?=$|\n)'
    
    bullet_points = re.findall(bullet_pattern, text, re.MULTILINE)
    numbered_points = re.findall(numbered_pattern, text, re.MULTILINE)
    
    # Combine and limit to 5 points
    points = (bullet_points + numbered_points)[:5]
    
    # If we didn't find explicit bullet points, try to extract sentences with key terms
    if not points:
        key_terms = ["recommend", "consider", "suggest", "look for", "watch", "buy", "sell", "hold"]
        sentence_pattern = r'[^.!?]*(?:{})[^.!?]*[.!?]'.format('|'.join(key_terms))
        sentences = re.findall(sentence_pattern, text, re.IGNORECASE)
        points = [s.strip() for s in sentences[:5]]
    
    # If we still have nothing, just take the first few sentences
    if not points:
        sentences = re.split(r'[.!?]', text)
        points = [s.strip() for s in sentences[:5] if len(s.strip()) > 20]
    
    return points

def analysis_color(text, theme="Dark"):
    """Determine sentiment color based on text content"""
    text = text.lower()
    
    positive_words = ["buy", "positive", "bullish", "uptrend", "growth", "opportunity"]
    negative_words = ["sell", "negative", "bearish", "downtrend", "caution", "risk"]
    
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    if positive_count > negative_count:
        return "#4CAF50"  # Green
    elif negative_count > positive_count:
        return "#F44336"  # Red
    else:
        return "#FFD700"  # Yellow/gold for neutral

def remove_think_tags(text):
    """Remove <thinking> and <think> tags from text"""
    import re
    # Remove <thinking>...</thinking> tags
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    # Also remove <think>...</think> tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text

def format_price(value):
    """
    Format numeric value as currency string.
    
    Args:
        value (float): Numeric price value
        
    Returns:
        str: Formatted price string ($XX.XX)
    """
    try:
        return f"${float(value):.2f}"
    except (ValueError, TypeError):
        return "N/A"

def get_change_color(current, previous, theme="Dark"):
    """
    Determine color for price change indicators, using the specified theme.
    
    Args:
        current (float): Current price
        previous (float): Previous price
        theme (str): Theme name from COLOR_PALETTES (default: "Dark")
        
    Returns:
        str: Color code from config.COLOR_PALETTES
    """
    colors = COLOR_PALETTES.get(theme, COLOR_PALETTES["Dark"])  # Get theme colors, default to "Dark"
    
    try:
        return colors['positive'] if float(current) >= float(previous) else colors['negative']
    except (ValueError, TypeError):
        return colors['text']

def format_percentage(value, decimal_places=2):
    """Format a decimal value as percentage"""
    if value is None:
        return "--"
    
    try:
        value = float(value)
        # Convert to percentage (multiply by 100)
        percentage = value * 100
        return f"{percentage:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return str(value)

def format_number(value, decimal_places=2, use_commas=True):
    """Format a number with commas for thousands and specified decimal places"""
    if value is None:
        return "--"
    
    try:
        value = float(value)
        formatted = f"{value:,.{decimal_places}f}" if use_commas else f"{value:.{decimal_places}f}"
        return formatted
    except (ValueError, TypeError):
        return str(value)

def format_market_cap(value):
    """Format market cap in billions or trillions"""
    if value is None:
        return "--"
    
    try:
        value = float(value)
        if value >= 1_000_000:  # Trillion+
            return f"${value/1_000_000:.1f}T"
        elif value >= 1_000:  # Billion+
            return f"${value/1_000:.1f}B"
        else:  # Million
            return f"${value:.0f}M"
    except (ValueError, TypeError):
        return str(value)

def format_currency(value, decimal_places=2):
    """Format a number as currency with $ symbol"""
    if value is None:
        return "--"
    
    try:
        value = float(value)
        return f"${value:,.{decimal_places}f}"
    except (ValueError, TypeError):
        return str(value)

def extract_predictions(text):
    """Extract price predictions from analysis text"""
    import re
    
    predictions = {
        'week': {'value': None, 'confidence': None, 'range': None},
        'month': {'value': None, 'confidence': None, 'range': None},
        'year': {'value': None, 'confidence': None, 'range': None}
    }
    
    # Week prediction
    week_match = re.search(r'(?:week|7 day|short term).*?\$([0-9,]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
    week_conf = re.search(r'(?:week|7 day|short term).*?confidence.*?([0-9]+(?:\.[0-9]+)?)%', text, re.IGNORECASE)
    
    # Month prediction
    month_match = re.search(r'(?:month|30 day|mid term).*?\$([0-9,]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
    month_conf = re.search(r'(?:month|30 day|mid term).*?confidence.*?([0-9]+(?:\.[0-9]+)?)%', text, re.IGNORECASE)
    
    # Year prediction
    year_match = re.search(r'(?:year|365 day|long term).*?\$([0-9,]+(?:\.[0-9]+)?)', text, re.IGNORECASE)
    year_conf = re.search(r'(?:year|365 day|long term).*?confidence.*?([0-9]+(?:\.[0-9]+)?)%', text, re.IGNORECASE)
    
    # Store values
    predictions['week']['value'] = week_match.group(1) if week_match else None
    predictions['week']['confidence'] = week_conf.group(1) if week_conf else None
    
    predictions['month']['value'] = month_match.group(1) if month_match else None
    predictions['month']['confidence'] = month_conf.group(1) if month_conf else None
    
    predictions['year']['value'] = year_match.group(1) if year_match else None
    predictions['year']['confidence'] = year_conf.group(1) if year_conf else None
    
    return predictions