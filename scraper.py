import sys
import re
import yfinance as yf
import ollama
import requests
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox,
                               QGridLayout, QStyle, QTabWidget, QFrame, QScrollArea,
                               QDialog, QDialogButtonBox, QStackedWidget, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor
import pyqtgraph as pg
import time

# Configuration
NEWS_API_KEY = "c91f9673406647e280aa6faf87ef892a"
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Modern design constants
COLORS = {
    "background": "#0a0a0a",
    "surface": "#1a1a1a",
    "primary": "#00bcd4",
    "secondary": "#2d2d2d",
    "text": "#ffffff",
    "text-secondary": "#858585",
    "positive": "#4caf50",  # Green
    "negative": "#f44336",  # Red
    "border": "#333333"
}
# Yellow colour used for mid-range percentages
YELLOW = "#FFEB3B"

FONT_FAMILY = "Segoe UI"
FONT_SIZES = {
    "title": 18,
    "header": 14,
    "body": 12,
    "small": 10
}

class StockOverview(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("overview")
        self.setMinimumSize(280, 160)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        self.ticker = QLabel("")
        self.ticker.setFont(QFont(FONT_FAMILY, 24, QFont.Bold))
        self.ticker.setStyleSheet(f"color: {COLORS['primary']}")
        
        self.price = QLabel("")
        self.price.setFont(QFont(FONT_FAMILY, 28, QFont.Medium))
        
        self.change = QLabel("")
        self.change.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
        
        layout.addWidget(self.ticker)
        layout.addWidget(self.price)
        layout.addWidget(self.change)
        layout.addStretch()

class KeyMetrics(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("metrics")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        title = QLabel("Key Metrics")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        
        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(8)
        self.grid.setHorizontalSpacing(16)
        
        layout.addWidget(title)
        layout.addLayout(self.grid)
        layout.addStretch()
        
    def update_metrics(self, metrics):
        # Clear previous metrics
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
            
        row = 0
        for label, value, color in metrics:
            lbl = QLabel(label)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
            lbl.setStyleSheet(f"color: {COLORS['text-secondary']}")
            
            val = QLabel(value)
            val.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"], QFont.Medium))
            val.setStyleSheet(f"color: {color}")
            
            self.grid.addWidget(lbl, row, 0)
            self.grid.addWidget(val, row, 1)
            row += 1

class RecommendationWidget(QFrame):
    """
    New widget to display the AI recommendation percentages for Buy, Hold, and Sell.
    """
    def __init__(self):
        super().__init__()
        self.setObjectName("recommendation")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        title = QLabel("Suggestions")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        layout.addWidget(title)
        
        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(8)
        self.grid.setHorizontalSpacing(16)
        layout.addLayout(self.grid)
        layout.addStretch()
        
    def update_recommendations(self, recs):
        """
        Update the grid with recommendation percentages.
        recs: a dictionary with keys 'Buy', 'Hold', 'Sell' and values as percentages (int)
        """
        # Clear previous entries
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        row = 0
        for option in ["Buy", "Hold", "Sell"]:
            lbl = QLabel(option)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
            lbl.setStyleSheet(f"color: {COLORS['text-secondary']}")
            
            percentage = recs.get(option, "N/A")
            if isinstance(percentage, int):
                text_value = f"{percentage}%"
                if 0 <= percentage <= 35:
                    color = COLORS['negative']  # Red
                elif 36 <= percentage <= 65:
                    color = YELLOW
                elif 66 <= percentage <= 100:
                    color = COLORS['positive']  # Green
                else:
                    color = COLORS['text']
            else:
                text_value = str(percentage)
                color = COLORS['text']
            val = QLabel(text_value)
            val.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"], QFont.Medium))
            val.setStyleSheet(f"color: {color}")
            
            self.grid.addWidget(lbl, row, 0)
            self.grid.addWidget(val, row, 1)
            row += 1

class AnalysisCard(QFrame):
    clicked = Signal(str, str, str)

    def __init__(self, title):
        super().__init__()
        self.setObjectName("analysisCard")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        self.title = title
        self.color = COLORS['text']

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        
        self.header_label = QLabel(title)
        self.header_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        
        self.btn_maximize = QPushButton()
        self.btn_maximize.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.btn_maximize.setFlat(True)
        self.btn_maximize.setFixedSize(24, 24)
        self.btn_maximize.clicked.connect(self._on_maximize_clicked)
        self.btn_maximize.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['secondary']};
                border-radius: 4px;
            }}
        """)
        
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_maximize)
        
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
        
        layout.addWidget(header)
        layout.addWidget(self.content)

    def _on_maximize_clicked(self):
        self.clicked.emit(self.title, self.content.toPlainText(), self.color)

# Basic StockChart implementation using pyqtgraph
class StockChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)
        self.plot_widget.setBackground(COLORS["surface"])
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.getAxis("left").setPen(pg.mkPen(COLORS["text"]))
        self.plot_widget.getAxis("bottom").setPen(pg.mkPen(COLORS["text"]))
        # Placeholder: set a default plot
        self.plot_widget.plot([1, 2, 3, 4, 5], pen=pg.mkPen(COLORS["primary"], width=2))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

class ModernStockApp(QMainWindow):

    def _setup_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
            }}
            #header {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
            QLineEdit {{
                background-color: {COLORS['secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: {FONT_SIZES['body']}pt;
                color: {COLORS['text']};
            }}
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['text']};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: medium;
            }}
            QPushButton:hover {{
                background-color: #00a5bb;
            }}
            #overview, #metrics, #analysisCard, #recommendation {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
            QTabWidget::pane {{
                border: none;
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {COLORS['text-secondary']};
                padding: 8px 16px;
                font-weight: medium;
                border: none;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['primary']};
                border-bottom: 2px solid {COLORS['primary']};
            }}
            QTextEdit {{
                background-color: {COLORS['secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 12px;
                font-size: {FONT_SIZES['body']}pt;
                color: {COLORS['text']};
            }}
        """)
        
        app_font = QFont(FONT_FAMILY, FONT_SIZES["body"])
        QApplication.instance().setFont(app_font)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analysis Pro")
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(1024, 768)
        self.current_ticker = None
        
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self._update_ui)
        
        # New stacked widget and pages for home/main app navigation
        self.stacked_widget = QStackedWidget()
        self.home_page = QWidget()
        self.main_app_page = QWidget()
        
        self._setup_ui()
        self._setup_styles()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header (modified to include home button)
        header = QWidget()
        header.setFixedHeight(60)
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        
        self.btn_home = QPushButton("🏠")
        self.btn_home.setFixedSize(40, 36)
        self.btn_home.hide()
        
        self.logo = QLabel("📈 StockPro")
        self.logo.setFont(QFont(FONT_FAMILY, FONT_SIZES["title"], QFont.DemiBold))
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Enter stock ticker...")
        self.search.setFixedWidth(300)
        self.search.setClearButtonEnabled(True)
        
        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setFixedSize(100, 36)
        
        header_layout.addWidget(self.btn_home)
        header_layout.addWidget(self.logo)
        header_layout.addStretch()
        header_layout.addWidget(self.search)
        header_layout.addWidget(self.btn_analyze)
        
        # Create pages
        self._setup_home_page()
        self._setup_main_app_page()
        
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.main_app_page)
        
        main_layout.addWidget(header)
        main_layout.addWidget(self.stacked_widget)

    def _setup_home_page(self):
        layout = QVBoxLayout(self.home_page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        # Favorites Section
        favorites_label = QLabel("Favorite Stocks")
        favorites_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        
        self.favorites_scroll = QScrollArea()
        self.favorites_scroll.setWidgetResizable(True)
        self.favorites_scroll.setFixedHeight(100)

        favorites_content = QWidget()
        self.favorites_layout = QHBoxLayout(favorites_content)
        self.favorites_layout.setContentsMargins(0, 0, 0, 0)
        self.favorites_layout.setSpacing(16)
        
        self.favorites_scroll.setWidget(favorites_content)
        
        # Recommendations Section
        rec_label = QLabel("AI Recommendations")
        rec_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        
        self.rec_scroll = QScrollArea()
        self.rec_scroll.setWidgetResizable(True)
        rec_content = QWidget()
        self.rec_layout = QVBoxLayout(rec_content)
        self.rec_layout.setContentsMargins(0, 0, 0, 0)
        self.rec_layout.setSpacing(8)
        
        self.rec_scroll.setWidget(rec_content)
        
        layout.addWidget(favorites_label)
        layout.addWidget(self.favorites_scroll)
        layout.addWidget(rec_label)
        layout.addWidget(self.rec_scroll)
        
        # Load initial data
        self._load_favorites(["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"])
        self._generate_recommendations()

    def _setup_main_app_page(self):
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)
        
        # Left sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(16)
        
        self.overview = StockOverview()
        self.metrics = KeyMetrics()
        # New AI Recommendation widget added below Key Metrics
        self.ai_recommendation = RecommendationWidget()
        
        sidebar_layout.addWidget(self.overview)
        sidebar_layout.addWidget(self.metrics)
        sidebar_layout.addWidget(self.ai_recommendation)
        sidebar_layout.addStretch()
        
        # Main tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        
        # Analysis tab
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        analysis_layout.setSpacing(16)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 16, 0)
        scroll_layout.setSpacing(16)
        
        self.news_card = AnalysisCard("Latest News")
        self.long_term_card = AnalysisCard("Long-Term Analysis")
        self.day_trade_card = AnalysisCard("Day Trading Analysis")
        
        scroll_layout.addWidget(self.news_card)
        scroll_layout.addWidget(self.long_term_card)
        scroll_layout.addWidget(self.day_trade_card)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        analysis_layout.addWidget(scroll)
        
        # Charts tab
        self.chart = StockChart()
        self.tabs.addTab(analysis_tab, "Analysis")
        self.tabs.addTab(self.chart, "Charts")
        
        content_layout.addWidget(sidebar)
        content_layout.addWidget(self.tabs)
        
        self.main_app_page.setLayout(content_layout)

    def _load_favorites(self, tickers):
        # Clear existing favorites
        for i in reversed(range(self.favorites_layout.count())):
            widget = self.favorites_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
            
        for ticker in tickers:
            card = QPushButton(ticker)
            card.setFixedSize(120, 80)
            card.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    font-size: {FONT_SIZES['header']}px;
                    color: {COLORS['primary']};
                }}
                QPushButton:hover {{
                    border-color: {COLORS['primary']};
                }}
            """)
            card.clicked.connect(lambda _, t=ticker: self._load_stock(t))
            self.favorites_layout.addWidget(card)

    def _generate_recommendations(self):
        try:
            # Predefined list of popular stocks to analyze
            predefined_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META',
                'BRK-B', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'DIS', 'HD',
                'BAC', 'XOM', 'WMT', 'PYPL', 'INTC', 'ADBE', 'CRM',
                'NFLX', 'KO', 'PEP', 'ABT', 'TMO', 'AVGO', 'QCOM'
            ]
            
            top_gainers = []
            
            for ticker in predefined_tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period='2d')
                    
                    if len(hist) < 2:
                        continue
                    
                    prev_close = hist['Close'].iloc[-2]
                    current_close = hist['Close'].iloc[-1]
                    change_pct = ((current_close - prev_close) / prev_close) * 100
                    
                    # Get current price for display
                    current_price = stock.info.get('currentPrice', current_close)
                    
                    top_gainers.append((ticker, change_pct, current_price))
                except Exception as e:
                    print(f"Error processing {ticker}: {str(e)}")
                    continue
            
            # Sort by percentage change descending
            top_gainers.sort(key=lambda x: x[1], reverse=True)
            
            # Take top 5 performers
            self._load_recommendations(top_gainers[:5])
            
        except Exception as e:
            print(f"Recommendation error: {e}")

    # Updated _load_recommendations method
    def _load_recommendations(self, tickers):
        # Clear existing recommendations
        for i in reversed(range(self.rec_layout.count())):
            widget = self.rec_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        for ticker, change_pct, price in tickers:
            color = COLORS['positive'] if change_pct >= 0 else COLORS['negative']
            btn = QPushButton()
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 12px;
                    background-color: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 8px;
                    color: {color};
                }}
                QPushButton:hover {{
                    border-color: {COLORS['primary']};
                }}
            """)
            
            # Format the text with HTML-like styling
            btn.setTextFormat(Qt.RichText)
            btn.setText(
            f"<span style='font-weight:600;'>{ticker}</span><br>"
            f"Price: ${price:.2f}<br>"
            f"Change: {change_pct:+.2f}%"
            )
            
            btn.clicked.connect(lambda _, t=ticker: self._load_stock(t))
        self.rec_layout.addWidget(btn)

    def _load_stock(self, ticker):
        self.search.setText(ticker)
        self._analyze()
        self.stacked_widget.setCurrentIndex(1)
        self.btn_home.show()

    def _analyze(self):
        ticker = self.search.text().strip().upper()
        if not ticker:
            self._show_error("Please enter a stock ticker")
            return
        
        if self.update_timer.isActive():
            self.update_timer.stop()
            
        try:
            self.current_ticker = ticker
            stock = yf.Ticker(ticker)
            
            # Initial data load
            self._update_ui()
            
            # Generate analysis and news
            self.news_card.content.setPlainText(self._get_stock_news(ticker))
            self._generate_analysis(stock, "long_term", self.long_term_card)
            self._generate_analysis(stock, "day_trade", self.day_trade_card)
            # Generate AI recommendation percentages for Buy, Hold, Sell
            self._generate_buy_hold_sell(stock)
            
            # Start updates (only price info and metrics will update every second)
            self.update_timer.start()
            
        except Exception as e:
            self._show_error(str(e))

    def _update_ui(self):
        if not self.current_ticker:
            return
            
        try:
            stock = yf.Ticker(self.current_ticker)
            info = stock.info
            hist = stock.history(period="1d", interval="1m", prepost=True)  # Add prepost=True
            
            current_price = info.get('currentPrice', 'N/A')
            prev_close = info.get('previousClose', 'N/A')
            
            if current_price != 'N/A' and prev_close != 'N/A':
                price_change = current_price - prev_close
                percent_change = (price_change / prev_close) * 100
                change_text = f"{price_change:+.2f} ({percent_change:+.2f}%)"
                change_color = COLORS['positive'] if price_change >= 0 else COLORS['negative']
            else:
                change_text = "N/A"
                change_color = COLORS['text']
            
            self.overview.ticker.setText(self.current_ticker)
            self.overview.price.setText(f"${current_price:.2f}" if current_price != 'N/A' else "N/A")
            self.overview.change.setText(change_text)
            self.overview.change.setStyleSheet(f"color: {change_color}")
            
            self.metrics.update_metrics(self._get_stock_metrics(stock))
            
        except Exception as e:
            print(f"Update error: {e}")

    def _get_stock_metrics(self, stock):
        info = stock.info
        metrics = []
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        previous_close = info.get('previousClose', 'N/A')
        post_price = info.get('postMarketPrice')
        pre_price = info.get('preMarketPrice')
        extended_price = post_price if post_price else pre_price
        if extended_price and extended_price != current_price:
            self._show_extended_hours_price(current_price, extended_price)
        else:
            self.overview.price.setText(f"${current_price:.2f}" if current_price != 'N/A' else "N/A")
        
        if current_price != 'N/A' and previous_close != 'N/A':
            price_color = COLORS['positive'] if current_price > previous_close else COLORS['negative']
            metrics.append(("Current Price", f"${current_price:.2f}", price_color))
            metrics.append(("Previous Close", f"${previous_close:.2f}", COLORS['text']))
        else:
            metrics.append(("Current Price", "N/A", COLORS['text']))
            metrics.append(("Previous Close", "N/A", COLORS['text']))
        
        hist = stock.history(period="1y")
        if not hist.empty:
            performance = (hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0] * 100
            perf_color = COLORS['positive'] if performance > 0 else COLORS['negative']
            metrics.append(("1Y Performance", f"{performance:.2f}%", perf_color))
        
        pe = info.get('trailingPE', 'N/A')
        metrics.append(("P/E Ratio", str(pe), COLORS['text']))
        
        market_cap = info.get('marketCap', 'N/A')
        if market_cap != 'N/A':
            market_cap = f"${market_cap/1e9:.1f}B"
        metrics.append(("Market Cap", market_cap, COLORS['text']))
        
        return metrics

    def _get_stock_news(self, ticker):
        try:
            params = {
                'q': ticker,
                'from': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'sortBy': 'relevancy',
                'language': 'en',
                'apiKey': NEWS_API_KEY
            }
            response = requests.get(NEWS_API_URL, params=params)
            response.raise_for_status()
            news = response.json()
            
            if not news.get('articles'):
                return "No recent news found"
                
            return "\n\n".join(
                f"• {article['title']}\n  {article['description'] or 'No description'}"
                for article in news['articles'][:3]
            )
        except Exception as e:
            print(f"News error: {e}")
            return "Could not fetch news"

    def _generate_analysis(self, stock, analysis_type, card):
        try:
            if analysis_type == "long_term":
                prompt = self._long_term_prompt(stock)
            else:
                prompt = self._day_trade_prompt(stock)
                
            response = ollama.generate(model='deepseek-r1:1.5b', prompt=prompt)
            analysis = response['response']
            # Remove text between <think> and </think>
            analysis = self._remove_think_tags(analysis)
            
            formatted = analysis.replace('\n', '\n\n')
            color = self._get_analysis_color(analysis)
            card.content.setTextColor(QColor(color))
            card.content.setPlainText(formatted)
            
        except Exception as e:
            card.content.setPlainText(f"Analysis failed: {str(e)}")

    def _remove_think_tags(self, text):
        """Removes any text enclosed between <think> and </think> tags."""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    def _long_term_prompt(self, stock):
        info = stock.info
        return f"""Analyze {self.current_ticker} as a long-term investment considering:
- Current price: ${info.get('currentPrice', 'N/A')}
- Market cap: {info.get('marketCap', 'N/A')}
- P/E ratio: {info.get('trailingPE', 'N/A')}
- Dividend yield: {info.get('dividendYield', 'N/A')}

Provide detailed analysis covering:
1. Fundamental financial health
2. Growth potential
3. Industry position
4. Risk factors
5. Long-term outlook

Format response with clear sections and bullet points."""
    
    def _day_trade_prompt(self, stock):
        hist = stock.history(period="1d", interval="15m")
        latest_price = hist['Close'][-1] if not hist.empty else 'N/A'
        low_range = hist['Low'].min() if not hist.empty else 'N/A'
        high_range = hist['High'].max() if not hist.empty else 'N/A'
        latest_volume = f"{hist['Volume'][-1]:,}" if not hist.empty else 'N/A'
        
        return f"""Analyze {self.current_ticker} for day trading based on:
- Latest price: ${latest_price}
- Today's range: ${low_range} - ${high_range}
- Volume: {latest_volume}

Provide analysis covering:
1. Intraday patterns
2. Key support/resistance levels
3. Momentum indicators
4. Entry/exit points
5. Risk management strategies

Keep response concise and action-oriented."""
    
    def _generate_buy_hold_sell(self, stock):
        """
        Generates AI-based percentages for Buy, Hold, and Sell recommendations.
        The prompt instructs the AI to return the percentages indicating the probability
        that the stock will increase in price.
        """
        try:
            info = stock.info
            current_price = info.get('currentPrice', 'N/A')
            previous_close = info.get('previousClose', 'N/A')
            market_cap = info.get('marketCap', 'N/A')
            prompt = f"""Based on the following stock data:
Current Price: ${current_price}
Previous Close: ${previous_close}
Market Cap: {market_cap}

Provide a recommendation breakdown for Buy, Hold, and Sell as percentages that indicate the probability that the stock will increase in price. Ensure the percentages sum to 100 and return the result in the following format:

Buy: X%
Hold: Y%
Sell: Z%
"""
            response = ollama.generate(model='deepseek-r1:1.5b', prompt=prompt)
            result_text = response['response']
            recs = self._parse_recommendations_from_text(result_text)
            self.ai_recommendation.update_recommendations(recs)
        except Exception as e:
            print(f"Recommendation generation error: {e}")
            self.ai_recommendation.update_recommendations({"Buy": "N/A", "Hold": "N/A", "Sell": "N/A"})

    def _parse_recommendations_from_text(self, text):
        """
        Parses the AI response text to extract percentages for Buy, Hold, and Sell.
        Expects text in the format:
            Buy: X%
            Hold: Y%
            Sell: Z%
        """
        recs = {}
        try:
            lines = text.splitlines()
            for line in lines:
                match = re.search(r'(Buy|Hold|Sell)\s*:\s*(\d+)%', line, re.IGNORECASE)
                if match:
                    option = match.group(1).capitalize()
                    percent = int(match.group(2))
                    recs[option] = percent
        except Exception as e:
            print(f"Error parsing recommendation: {e}")
        # Ensure all keys are present
        for opt in ["Buy", "Hold", "Sell"]:
            if opt not in recs:
                recs[opt] = "N/A"
        return recs

    def _get_analysis_color(self, text):
        text_lower = text.lower()
        if any(word in text_lower for word in ["buy", "positive", "bullish"]):
            return COLORS['positive']
        elif any(word in text_lower for word in ["sell", "negative", "bearish"]):
            return COLORS['negative']
        return COLORS['text']

    def show_maximized_card(self, title, text, color):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setWindowFlags(dialog.windowFlags() | 
                            Qt.WindowMaximizeButtonHint |
                            Qt.WindowMinimizeButtonHint)
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        content = QTextEdit()
        content.setReadOnly(True)
        content.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
        content.setTextColor(QColor(color))
        content.setPlainText(text)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        
        layout.addWidget(content)
        layout.addWidget(buttons)
        
        dialog.exec()

    def _show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def _connect_signals(self):
        self.btn_analyze.clicked.connect(self._analyze)
        self.search.returnPressed.connect(self._analyze)
        self.news_card.clicked.connect(self.show_maximized_card)
        self.long_term_card.clicked.connect(self.show_maximized_card)
        self.day_trade_card.clicked.connect(self.show_maximized_card)
        self.btn_home.clicked.connect(self._go_home)

    def _go_home(self):
        # Stop the update timer if running
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        # Reset current ticker and UI elements
        self.current_ticker = None
        self.overview.ticker.setText("")
        self.overview.price.setText("")
        self.overview.change.setText("")
        self.metrics.update_metrics([])
        self.ai_recommendation.update_recommendations({"Buy": "N/A", "Hold": "N/A", "Sell": "N/A"})
        
        # Switch to home page
        self.stacked_widget.setCurrentIndex(0)
        self.btn_home.hide()
        self.search.clear()

class StockWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, ticker):
        super().__init__()
        self.ticker = ticker
        self._active = True
        self.exchange = "NASDAQ"  # Default exchange, modify as needed
        self.screener = "america" # Default screener, modify as needed

    def run(self):
        try:
            while self._active:
                start_time = time.time()
                
                # Get TradingView analysis
                handler = TA_Handler(
                    symbol=self.ticker,
                    screener=self.screener,
                    exchange=self.exchange,
                    interval=Interval.INTERVAL_1_MINUTE
                )
                
                analysis = handler.get_analysis()
                summary = analysis.summary
                indicators = analysis.indicators
                oscillators = analysis.oscillators
                moving_avgs = analysis.moving_averages

                # Get additional technical indicators
                data = {
                    'current_price': indicators.get("close"),
                    'previous_close': indicators.get("open"),
                    'high': indicators.get("high"),
                    'low': indicators.get("low"),
                    'volume': indicators.get("volume"),
                    'metrics': self._get_metrics(analysis),
                    'recommendation': summary.get('RECOMMENDATION', 'N/A'),
                    'rsi': indicators.get("RSI"),
                    'macd': indicators.get("MACD.macd"),
                    'signal': indicators.get("MACD.signal"),
                    'histogram': indicators.get("MACD.hist"),
                    'stoch_k': indicators.get("Stoch.K"),
                    'stoch_d': indicators.get("Stoch.D"),
                    'ema_20': moving_avgs.get("EMA20"),
                    'sma_50': moving_avgs.get("SMA50"),
                    'sma_200': moving_avgs.get("SMA200"),
                }

                self.finished.emit(data)
                
                # Maintain 2-second interval to avoid rate limits
                elapsed = time.time() - start_time
                sleep_time = max(2.0 - elapsed, 0)
                time.sleep(sleep_time)

        except Exception as e:
            self.error.emit(str(e))
            time.sleep(5)  # Backoff on errors

    def _get_metrics(self, analysis):
        """Convert TradingView data to our metric format"""
        indicators = analysis.indicators
        summary = analysis.summary
        oscillators = analysis.oscillators
        moving_avgs = analysis.moving_averages

        metrics = [
            ("Price", self._format_price(indicators.get("close")), COLORS['text']),
            ("Change", self._get_price_change(indicators), self._get_change_color(indicators)),
            ("Recommendation", summary.get('RECOMMENDATION', 'N/A'), 
             self._get_recommendation_color(summary)),
            ("RSI (14)", self._format_rsi(indicators.get("RSI")), 
             self._get_rsi_color(indicators.get("RSI"))),
            ("Volume", f"{indicators.get('volume', 0):,}", COLORS['text']),
            ("MACD", self._format_macd(indicators), COLORS['text']),
            ("Stochastic", self._format_stochastic(indicators), COLORS['text']),
            ("EMA 20", self._format_price(moving_avgs.get("EMA20")), COLORS['text']),
            ("SMA 50", self._format_price(moving_avgs.get("SMA50")), COLORS['text']),
            ("SMA 200", self._format_price(moving_avgs.get("SMA200")), COLORS['text'])
        ]
        return metrics

    def _format_price(self, value):
        return f"${value:.2f}" if value is not None else "N/A"

    def _get_price_change(self, indicators):
        close = indicators.get("close")
        open_price = indicators.get("open")
        if close and open_price:
            change = close - open_price
            pct_change = (change / open_price) * 100
            return f"{change:+.2f} ({pct_change:+.2f}%)"
        return "N/A"

    def _get_change_color(self, indicators):
        close = indicators.get("close")
        open_price = indicators.get("open")
        if close and open_price:
            return COLORS['positive'] if close >= open_price else COLORS['negative']
        return COLORS['text']

    def _get_recommendation_color(self, summary):
        rec = summary.get('RECOMMENDATION', '').upper()
        if 'STRONG_BUY' in rec:
            return COLORS['positive']
        if 'STRONG_SELL' in rec:
            return COLORS['negative']
        if 'BUY' in rec:
            return "#90EE90"  # Light green
        if 'SELL' in rec:
            return "#FF6961"  # Light red
        return YELLOW

    def _format_rsi(self, rsi):
        if rsi is not None:
            return f"{rsi:.2f} ({self._get_rsi_strength(rsi)})"
        return "N/A"

    def _get_rsi_strength(self, rsi):
        if rsi > 70: return "Overbought"
        if rsi < 30: return "Oversold"
        return "Neutral"

    def _get_rsi_color(self, rsi):
        if rsi is None:
            return COLORS['text']
        if rsi > 70: return COLORS['negative']
        if rsi < 30: return COLORS['positive']
        return YELLOW

    def _format_macd(self, indicators):
        macd = indicators.get("MACD.macd")
        signal = indicators.get("MACD.signal")
        hist = indicators.get("MACD.hist")
        
        if all(v is not None for v in [macd, signal, hist]):
            return f"{macd:.2f}/{signal:.2f} ({hist:+.2f})"
        return "N/A"

    def _format_stochastic(self, indicators):
        k = indicators.get("Stoch.K")
        d = indicators.get("Stoch.D")
        if k and d:
            return f"{k:.2f}/{d:.2f}"
        return "N/A"

    def stop(self):
        self._active = False



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernStockApp()
    window.show()
    sys.exit(app.exec())
