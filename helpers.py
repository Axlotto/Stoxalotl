# helpers.py
import re
from config import COLOR_PALETTES, FONT_FAMILY, FONT_SIZES

def parse_recommendations(text):
    """
    Parse recommendation percentages from analysis text.
    
    Args:
        text (str): Raw analysis text containing recommendations
        
    Returns:
        dict: Dictionary with Buy/Hold/Sell percentages
    """
    recs = {}
    try:
        if not text:
            return {'Buy': 'N/A', 'Hold': 'N/A', 'Sell': 'N/A'}
        
        # Look for patterns like "Buy: 65%", "Hold: 25%", etc.
        matches = re.findall(
            r'(Buy|Hold|Sell)\s*:\s*(\d+)%', 
            text, 
            flags=re.IGNORECASE
        )
        
        for match in matches:
            option = match[0].capitalize()
            percent = int(match[1])
            recs[option] = percent
            
        # Ensure all keys exist
        for option in ['Buy', 'Hold', 'Sell']:
            if option not in recs:
                recs[option] = 'N/A'
                
    except Exception as e:
        print(f"Error parsing recommendations: {e}")
        return {'Buy': 'N/A', 'Hold': 'N/A', 'Sell': 'N/A'}
    
    return recs

def analysis_color(text, theme="Dark"):
    """
    Determine color based on analysis verdict, using the specified theme.
    
    Args:
        text (str): Analysis text
        theme (str): Theme name from COLOR_PALETTES (default: "Dark")
        
    Returns:
        str: Color code from config.COLOR_PALETTES
    """
    colors = COLOR_PALETTES.get(theme, COLOR_PALETTES["Dark"])  # Get theme colors, default to "Dark"
    
    if not text:
        return colors['text']
    
    text_lower = text.lower()
    
    if 'verdict: buy' in text_lower:
        return colors['positive']
    elif 'verdict: sell' in text_lower:
        return colors['negative']
    elif 'buy' in text_lower:
        return "#90EE90"  # Light green
    elif 'sell' in text_lower:
        return "#FF6961"  # Light red
    return colors['text']

def remove_think_tags(text):
    """
    Remove content between <think> tags from text.
    
    Args:
        text (str): Original text with potential <think> tags
        
    Returns:
        str: Cleaned text without think tags
    """
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

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