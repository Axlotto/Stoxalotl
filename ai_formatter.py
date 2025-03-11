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
                
            # Technical terms - purple - fix potential invalid color
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

    @staticmethod
    def parse_ollama_response(response: str) -> dict:
        """
        Enforce structured format:
        [Current Price] $999.99
        [30-Day Target] $1234.56 (±10%)
        [Action] Buy/Hold/Sell
        [Rationale] Short explanation
        """
        lines = response.splitlines()
        result = {}
        for line in lines:
            if line.startswith("[Current Price]"):
                result["price"] = line.split("$")[1].strip()
            elif line.startswith("[30-Day Target]"):
                # Extract target and optional confidence
                # ...existing logic to parse...
                pass
            elif line.startswith("[Action]"):
                result["action"] = line.split("]", 1)[1].strip()
            elif line.startswith("[Rationale]"):
                result["rationale"] = line.split("]", 1)[1].strip()
        return result

    @staticmethod
    def format_analysis(parsed: dict) -> str:
        """
        Return bullet points with color-coded action:
        • 📈 Current Price...
        • 🎯 30-Day Target...
        • 🚀 Recommendation...
        • 💡 Reason...
        """
        action_color = "#2ECC71" if parsed.get("action", "").lower() == "buy" \
                    else "#E74C3C" if parsed.get("action", "").lower() == "sell" \
                    else "#F39C12"
        return f"""
        • <b>📈 Current Price</b>: ${parsed.get('price','--')}
        • <b>🎯 30-Day Target</b>: $-- (--% confidence)
        • <b style="color: {action_color};">🚀 Recommendation</b>: {parsed.get('action','N/A')}
        • <b>💡 Reason</b>: {parsed.get('rationale','No rationale provided')}
        """

    @staticmethod
    def get_safe_analysis(response: str) -> str:
        """Try to parse and format the analysis, return fallback if any error."""
        try:
            parsed = AnalysisFormatter.parse_ollama_response(response)
            return AnalysisFormatter.format_analysis(parsed)
        except Exception as e:
            return f"""
            ⚠️ Analysis Unavailable
            Error: {str(e)}
            Last Price: $--
            """
    
    @staticmethod
    def format_enhanced_analysis(analysis_text: str, ticker: str, financial_data: Dict) -> str:
        """
        Format analysis with enhanced visual structure and sections
        
        Args:
            analysis_text: The AI-generated analysis text
            ticker: Stock symbol
            financial_data: Dictionary containing financial metrics
            
        Returns:
            str: HTML-formatted analysis with structured sections
        """
        try:
            # Extract sections from analysis text using regex patterns
            overview_match = re.search(r'(?:OVERVIEW|STOCK OVERVIEW|SUMMARY):(.*?)(?=\n\n|\Z)', 
                                      analysis_text, re.IGNORECASE | re.DOTALL)
            financial_match = re.search(r'(?:FINANCIAL|FINANCIAL SITUATION|FINANCIALS):(.*?)(?=\n\n|\Z)', 
                                       analysis_text, re.IGNORECASE | re.DOTALL)
            news_match = re.search(r'(?:NEWS IMPACT|RECENT NEWS|NEWS ANALYSIS):(.*?)(?=\n\n|\Z)', 
                                  analysis_text, re.IGNORECASE | re.DOTALL)
            trajectory_match = re.search(r'(?:TRAJECTORY|TREND|MOMENTUM):(.*?)(?=\n\n|\Z)', 
                                        analysis_text, re.IGNORECASE | re.DOTALL)
            prediction_match = re.search(r'(?:PREDICTION|FORECAST|OUTLOOK|TARGET):(.*?)(?=\n\n|\Z)', 
                                        analysis_text, re.IGNORECASE | re.DOTALL)
            
            # If sections aren't found, try to extract them based on the content
            sections = analysis_text.split('\n\n')
            
            overview_text = overview_match.group(1).strip() if overview_match else sections[0] if sections else ""
            financial_text = financial_match.group(1).strip() if financial_match else ""
            news_text = news_match.group(1).strip() if news_match else ""
            trajectory_text = trajectory_match.group(1).strip() if trajectory_match else ""
            prediction_text = prediction_match.group(1).strip() if prediction_match else ""
            
            # Apply formatting to each section
            overview_formatted = AnalysisFormatter.format_section_content(overview_text, ticker)
            financial_formatted = AnalysisFormatter.format_section_content(financial_text, ticker)
            news_formatted = AnalysisFormatter.format_section_content(news_text, ticker)
            trajectory_formatted = AnalysisFormatter.format_section_content(trajectory_text, ticker)
            prediction_formatted = AnalysisFormatter.format_section_content(prediction_text, ticker)
            
            # Extract prediction values using regex
            eow_prediction = AnalysisFormatter._extract_prediction(prediction_text, "week|7 days|short term")
            eom_prediction = AnalysisFormatter._extract_prediction(prediction_text, "month|30 days|mid term")
            eoy_prediction = AnalysisFormatter._extract_prediction(prediction_text, "year|365 days|long term")
            
            # Generate HTML for the enhanced analysis
            html = f"""
            <div style="font-family: Segoe UI, sans-serif; margin: 0; padding: 0;">
                <!-- Stock Overview Section -->
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #BB86FC; margin-top: 0; border-bottom: 1px solid #555;">
                        <span style="font-size: 18px;">&#128200;</span> Stock Overview: {ticker}
                    </h3>
                    <div style="padding: 10px; background-color: rgba(40, 40, 40, 0.6); border-radius: 8px;">
                        {overview_formatted}
                    </div>
                </div>
                
                <!-- Financial Analysis Section -->
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #03DAC6; margin-top: 0; border-bottom: 1px solid #555;">
                        <span style="font-size: 18px;">&#128202;</span> Financial Situation Analysis
                    </h3>
                    <div style="padding: 10px; background-color: rgba(40, 40, 40, 0.6); border-radius: 8px;">
                        {financial_formatted}
                        {AnalysisFormatter._generate_financial_metrics_html(financial_data)}
                    </div>
                </div>
                
                <!-- News Impact Section -->
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #03DAC6; margin-top: 0; border-bottom: 1px solid #555;">
                        <span style="font-size: 18px;">&#128240;</span> Recent News Impact
                    </h3>
                    <div style="padding: 10px; background-color: rgba(40, 40, 40, 0.6); border-radius: 8px;">
                        {news_formatted}
                    </div>
                </div>
                
                <!-- Trajectory Analysis Section -->
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #03DAC6; margin-top: 0; border-bottom: 1px solid #555;">
                        <span style="font-size: 18px;">&#128176;</span> Trajectory Analysis
                    </h3>
                    <div style="padding: 10px; background-color: rgba(40, 40, 40, 0.6); border-radius: 8px;">
                        {trajectory_formatted}
                    </div>
                </div>
                
                <!-- Predictions Section -->
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #03DAC6; margin-top: 0; border-bottom: 1px solid #555;">
                        <span style="font-size: 18px;">&#128302;</span> Price Predictions
                    </h3>
                    <div style="padding: 10px; background-color: rgba(40, 40, 40, 0.6); border-radius: 8px;">
                        {prediction_formatted}
                        <div style="display: flex; justify-content: space-around; margin-top: 15px; flex-wrap: wrap;">
                            {AnalysisFormatter._create_prediction_box("End of Week", eow_prediction)}
                            {AnalysisFormatter._create_prediction_box("End of Month", eom_prediction)}
                            {AnalysisFormatter._create_prediction_box("End of Year", eoy_prediction)}
                        </div>
                    </div>
                </div>
            </div>
            """
            return html
        except Exception as e:
            logging.error(f"Error formatting enhanced analysis: {e}")
            # Return a basic formatted version of the original text if there's an error
            return AnalysisFormatter.format_stock_analysis(analysis_text, ticker)
    
    @staticmethod
    def format_section_content(content: str, ticker: str) -> str:
        """Format the content of a section with highlighting and structure"""
        if not content:
            return "<p><i>No information available</i></p>"
        
        # Replace bullet points for better spacing
        content = content.replace("\n- ", "\n• ")
        content = content.replace("\n* ", "\n• ")
        
        # Convert newlines to HTML breaks
        content = content.replace("\n", "<br>")
        
        # Apply highlighting
        content = AnalysisFormatter.highlight_numbers(content)
        content = AnalysisFormatter.highlight_keywords(content)
        
        # Highlight the ticker symbol
        content = re.sub(f'\\b{re.escape(ticker)}\\b', 
                         f'<span style="color: #BB86FC; font-weight: bold;">{ticker}</span>', 
                         content, flags=re.IGNORECASE)
        
        # Improve bullet points formatting
        content = re.sub(r'•\s*', '<br>• ', content)
        
        return f"<p>{content}</p>"
    
    @staticmethod
    def _extract_prediction(text: str, time_pattern: str) -> Dict:
        """Extract prediction value from analysis text"""
        # Try to find price predictions with values
        price_match = re.search(
            rf'(?:{time_pattern}).*?(?:\$([0-9,]+(?:\.[0-9]+)?)|\$?\s*([0-9,]+(?:\.[0-9]+)?))(?:\s*[-–]?\s*\$?([0-9,]+(?:\.[0-9]+)?))?',
            text, re.IGNORECASE
        )
        
        # Try to find confidence percentage
        confidence_match = re.search(
            rf'(?:{time_pattern}).*?confidence.*?([0-9]+(?:\.[0-9]+)?)%',
            text, re.IGNORECASE
        )
        
        # Look for directional indicators
        direction = "neutral"
        if re.search(r'\b(?:increase|rise|grow|up|higher|bullish)\b', text, re.IGNORECASE):
            direction = "positive"
        elif re.search(r'\b(?:decrease|fall|drop|down|lower|bearish)\b', text, re.IGNORECASE):
            direction = "negative"
        
        result = {
            "value": price_match.group(1) or price_match.group(2) if price_match else None,
            "range_high": price_match.group(3) if price_match and price_match.group(3) else None,
            "confidence": confidence_match.group(1) if confidence_match else None,
            "direction": direction
        }
        
        return result
    
    @staticmethod
    def _create_prediction_box(title: str, prediction: Dict) -> str:
        """Create a visually appealing prediction box"""
        if not prediction or not prediction.get("value"):
            return f"""
            <div style="width: 180px; margin: 8px; text-align: center; border: 1px solid #444; border-radius: 8px; padding: 10px;">
                <h4 style="margin-top: 0; color: #e0e0e0;">{title}</h4>
                <p style="font-size: 18px; font-weight: bold;">No prediction</p>
                <div style="font-size: 12px; color: #999;">Insufficient data</div>
            </div>
            """
        
        # Determine color based on direction
        color = "#4CAF50" if prediction["direction"] == "positive" else \
                "#F44336" if prediction["direction"] == "negative" else "#FFD700"
        
        # Direction indicator
        indicator = "↑" if prediction["direction"] == "positive" else \
                    "↓" if prediction["direction"] == "negative" else "→"
        
        # Format value
        value = prediction["value"].replace(",", "")
        try:
            value_display = f"${float(value):.2f}"
        except:
            value_display = f"${value}"
        
        # Format range if available
        range_text = ""
        if prediction["range_high"]:
            range_high = prediction["range_high"].replace(",", "")
            try:
                range_text = f" - ${float(range_high):.2f}"
            except:
                range_text = f" - ${range_high}"
        
        # Format confidence
        confidence_text = ""
        if prediction["confidence"]:
            confidence_text = f"Confidence: {prediction['confidence']}%"
            # Create confidence bar
            try:
                confidence_val = float(prediction["confidence"])
                confidence_width = min(100, max(10, confidence_val))  # between 10-100%
                confidence_bar = f"""
                <div style="width: 100%; background-color: #333; height: 6px; border-radius: 3px; margin-top: 8px;">
                    <div style="width: {confidence_width}%; background-color: {color}; height: 6px; border-radius: 3px;"></div>
                </div>
                """
            except:
                confidence_bar = ""
        else:
            confidence_bar = ""
        
        return f"""
        <div style="width: 180px; margin: 8px; text-align: center; border: 1px solid #444; border-radius: 8px; padding: 10px;">
            <h4 style="margin-top: 0; color: #e0e0e0;">{title}</h4>
            <p style="font-size: 20px; font-weight: bold; color: {color};">{indicator} {value_display}{range_text}</p>
            <div style="font-size: 12px; color: #bbb;">{confidence_text}</div>
            {confidence_bar}
        </div>
        """
    
    @staticmethod
    def _generate_financial_metrics_html(financial_data: Dict) -> str:
        """Generate HTML for financial metrics grid"""
        if not financial_data or not isinstance(financial_data, dict) or "metric" not in financial_data:
            return ""
        
        metrics = financial_data.get("metric", {})
        
        # Extract key metrics with labels and formatting
        key_metrics = [
            {"label": "P/E Ratio", "value": metrics.get("peNormalizedAnnual"), "format": "decimal"},
            {"label": "P/E (TTM)", "value": metrics.get("peTTM"), "format": "decimal"},
            {"label": "P/B Ratio", "value": metrics.get("pbAnnual"), "format": "decimal"},
            {"label": "P/S Ratio", "value": metrics.get("psTTM"), "format": "decimal"},
            {"label": "Dividend Yield", "value": metrics.get("dividendYieldIndicatedAnnual"), "format": "percent"},
            {"label": "52-Week High", "value": metrics.get("52WeekHigh"), "format": "currency"},
            {"label": "52-Week Low", "value": metrics.get("52WeekLow"), "format": "currency"}
        ]
        
        # Create metrics HTML
        metrics_html = '<div style="display: flex; flex-wrap: wrap; justify-content: space-between; margin-top: 15px;">'
        
        for metric in key_metrics:
            if metric["value"] is None:
                formatted_value = "N/A"
                color = "#999"
            else:
                try:
                    value = float(metric["value"])
                    if metric["format"] == "percent":
                        formatted_value = f"{value:.2f}%"
                    elif metric["format"] == "currency":
                        formatted_value = f"${value:.2f}"
                    else:  # decimal
                        formatted_value = f"{value:.2f}"
                        
                    # Set reasonable color thresholds for different metrics
                    if metric["label"] == "P/E Ratio" or metric["label"] == "P/E (TTM)":
                        color = "#4CAF50" if value < 20 else "#FFD700" if value < 40 else "#F44336"
                    elif metric["label"] == "P/B Ratio":
                        color = "#4CAF50" if value < 3 else "#FFD700" if value < 5 else "#F44336"
                    elif metric["label"] == "P/S Ratio":
                        color = "#4CAF50" if value < 2 else "#FFD700" if value < 5 else "#F44336"
                    elif metric["label"] == "Dividend Yield":
                        color = "#4CAF50" if value > 2 else "#FFD700" if value > 0 else "#999"
                    else:
                        color = "#e0e0e0"  # default color
                except:
                    formatted_value = "N/A"
                    color = "#999"
            
            metrics_html += f"""
            <div style="width: calc(33.33% - 10px); margin-bottom: 10px;">
                <div style="font-size: 12px; color: #aaa;">{metric["label"]}</div>
                <div style="font-size: 14px; font-weight: bold; color: {color};">{formatted_value}</div>
            </div>
            """
        
        metrics_html += '</div>'
        return metrics_html
            
    @staticmethod
    def apply_enhanced_formatting(editor: QTextEdit, analysis: str, ticker: str, financial_data: Dict = None):
        """Apply enhanced rich text formatting to a QTextEdit widget"""
        # Use the new formatter with financial data if provided
        if financial_data is None:
            financial_data = {}
            
        formatted_html = AnalysisFormatter.format_enhanced_analysis(analysis, ticker, financial_data)
        editor.setHtml(formatted_html)
