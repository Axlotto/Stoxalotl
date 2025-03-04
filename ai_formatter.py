"""
AI Analysis Formatter
Enhances the presentation of AI-generated analysis
"""

import re
from typing import Dict, List, Tuple
import logging
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat
from PySide6.QtWidgets import QTextEdit

class AnalysisFormatter:
    """Format AI analysis text with enhanced formatting and structure"""
    
    @staticmethod
    def highlight_numbers(text: str) -> str:
        """Highlight numeric values in text"""
        # Match currency values, percentages, and numeric ranges
        pattern = r'(\$[0-9,]+(?:\.[0-9]{1,2})?)|([0-9]+(?:\.[0-9]{1,2})?\%)|([0-9]+(?:\.[0-9]{1,2})?)'
        replacement = r'<span style="color: #4fc3f7; font-weight: bold;">\1\2\3</span>'
        return re.sub(pattern, replacement, text)
    
    @staticmethod
    def highlight_keywords(text: str) -> str:
        """Highlight important keywords"""
        keywords = {
            # Positive terms - green
            r'\b(buy|bullish|uptrend|growth|increase|positive|strong|opportunity)\b': 
                r'<span style="color: #4CAF50; font-weight: bold;">\1</span>',
            
            # Negative terms - red
            r'\b(sell|bearish|downtrend|decline|decrease|negative|weak|risk)\b': 
                r'<span style="color: #F44336; font-weight: bold;">\1</span>',
                
            # Neutral/cautious terms - yellow
            r'\b(hold|neutral|sideways|consolidation|cautious|monitor|watch)\b': 
                r'<span style="color: #FFD700; font-weight: bold;">\1</span>',
                
            # Technical terms - purple
            r'\b(resistance|support|moving average|MACD|RSI|volume|indicator)\b': 
                r'<span style="color: #BB86FC; font-weight: bold;">\1</span>',
        }
        
        result = text
        for pattern, replacement in keywords.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            
        return result
    
    @staticmethod
    def create_progress_bar(value: float, max_value: float, width: int = 10) -> str:
        """Create a text-based progress bar"""
        filled = int(width * (value / max_value))
        empty = width - filled
        
        # Base color on percentage
        percentage = value / max_value
        if percentage < 0.3:
            color = "#F44336"  # Red for low values
        elif percentage < 0.7:
            color = "#FFD700"  # Yellow for medium values
        else:
            color = "#4CAF50"  # Green for high values
            
        bar = f'<span style="color: {color};">{"█" * filled}{"░" * empty}</span> {value:.1f}/{max_value:.1f}'
        return bar
    
    @staticmethod
    def format_bullet_points(text: str) -> str:
        """Format bullet points with enhanced styling"""
        # Replace bullet points with styled bullets
        bullet_pattern = r'(^|\n)[\s]*[-•][\s]+(.*?)($|\n)'
        replacement = r'\1<span style="color: #BB86FC;">•</span> <span style="color: #e0e0e0;">\2</span>\3'
        return re.sub(bullet_pattern, replacement, text, flags=re.MULTILINE)
    
    @staticmethod
    def format_sections(text: str) -> str:
        """Format section headers"""
        # Find section headers (capitalized phrases followed by colon)
        section_pattern = r'(^|\n)([A-Z][A-Z\s]+):($|\n)'
        replacement = r'\1<h3 style="color: #03DAC6; margin-top: 15px; margin-bottom: 5px;">\2:</h3>\3'
        return re.sub(section_pattern, replacement, text, flags=re.MULTILINE)
    
    @staticmethod
    def add_analysis_panel(title: str, content: str, sentiment: str = "neutral") -> str:
        """Wrap content in a styled panel based on sentiment"""
        # Choose border color based on sentiment
        if sentiment.lower() == "positive":
            border_color = "#4CAF50"  # Green
        elif sentiment.lower() == "negative":
            border_color = "#F44336"  # Red
        else:
            border_color = "#03DAC6"  # Teal (neutral)
            
        panel = f"""
        <div style="border: 1px solid {border_color}; border-radius: 5px; margin-bottom: 15px; padding: 10px;">
            <h2 style="color: {border_color}; margin-top: 0;">{title}</h2>
            {content}
        </div>
        """
        return panel
    
    @staticmethod
    def format_stock_analysis(analysis: str, ticker: str) -> str:
        """Apply comprehensive formatting to stock analysis text"""
        # First apply basic formatting to the raw text
        formatted = analysis.replace('\n', '<br>')
        
        # Apply highlight to the ticker symbol
        formatted = re.sub(f'\\b{re.escape(ticker)}\\b', f'<b style="color: #BB86FC;">{ticker}</b>', formatted, flags=re.IGNORECASE)
        
        # Apply more specific formatting
        formatted = AnalysisFormatter.highlight_numbers(formatted)
        formatted = AnalysisFormatter.highlight_keywords(formatted)
        formatted = AnalysisFormatter.format_bullet_points(formatted)
        formatted = AnalysisFormatter.format_sections(formatted)
        
        return formatted
    
    @staticmethod
    def apply_formatting_to_textedit(editor: QTextEdit, analysis: str, ticker: str):
        """Apply rich text formatting to a QTextEdit widget"""
        # Get sentiment from content
        sentiment = "positive" if re.search(r'\b(buy|bullish|uptrend)\b', analysis, re.IGNORECASE) else \
                  "negative" if re.search(r'\b(sell|bearish|downtrend)\b', analysis, re.IGNORECASE) else \
                  "neutral"

        # Format the content
        formatted_html = AnalysisFormatter.format_stock_analysis(analysis, ticker)
        
        # Set as HTML
        editor.setHtml(formatted_html)
