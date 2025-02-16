# main.py
import sys
import os
import re
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QColor, QPixmap, QIcon, QTextCursor  # Added QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QGridLayout,
    QTabWidget,
    QFrame,
    QScrollArea,
    QDialog,
    QDialogButtonBox,
    QStackedWidget,
    QSizePolicy,
    QSystemTrayIcon,
    QComboBox  # Added QComboBox
)
import pyqtgraph as pg
import numpy as np  # Import numpy

# Check numpy version
try:
    if np.__version__ >= '1.24':
        print("Warning: It's recommended to use numpy<1.24 with pyqtgraph. Consider downgrading.")
except:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Local imports
from config import (COLOR_PALETTES, FONT_FAMILY, FONT_SIZES, FONT_CHOICES, 
                   OLLAMA_MODEL, CHAT_MODEL, NEWS_API_KEY, NEWS_API_URL, UI_CONFIG)
from widgets import KeyMetrics, RecommendationWidget,  AnalysisCard, StockChart, StockOverview
from api_client import StockAPI, AIClient  # Specify the full path
from helpers import parse_recommendations, analysis_color, remove_think_tags  # Specify the full path
from widgets import StockOverview


class ModernStockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Store icon path as class variable
        self.app_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "Axlotto transparent.ico")
        print(f"Loading icon from: {self.app_icon_path}")
        print(f"File exists: {os.path.exists(self.app_icon_path)}")
        
        self.app_icon = QIcon(self.app_icon_path)
        
        # Set window icon
        if self.app_icon.isNull():
            print("Error: Icon loaded but is null")
        else:
            print("Icon loaded successfully")
            self.setWindowIcon(self.app_icon)
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("Stoxalotl")
        if not self.app_icon.isNull():
            self.tray_icon.show()
        
        self.setWindowTitle("Stoxalotl")
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(1024, 768)
        self.current_ticker = None
        self.favorite_tickers = []
        self.recent_tickers = []  # Add list for recently viewed tickers
        self.max_recent_tickers = 5  # Maximum number of recent tickers to show

        # Initialize API clients
        self.stock_api = StockAPI()
        self.ai_client = AIClient()

        # Initialize chat box
        self.chat_box = QTextEdit()
        self.chat_input = QLineEdit()
        self.send_button = QPushButton("Send")

        # Setup UI and timer
        self._setup_ui()
        self._setup_styles()
        self._connect_signals()
        self._init_update_timer()

    def _init_update_timer(self):
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self._update_ui)

    def _setup_styles(self):
        # Apply the selected color palette
        theme = COLOR_PALETTES["Dark"]  # Default theme
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['background']};
                color: {theme['text']};
            }}
            /* Add other styles from original implementation */
        """)

        # Apply the selected font family
        app_font = QFont(FONT_FAMILY, FONT_SIZES["body"])
        QApplication.instance().setFont(app_font)

        # Apply UI configurations
        border_radius = UI_CONFIG["border_radius"]
        padding = UI_CONFIG["padding"]
        button_style = UI_CONFIG["button_style"]

        # Example: Style QPushButton based on the configuration
        if button_style == "modern":
            self.setStyleSheet(self.styleSheet() + f"""
                QPushButton {{
                    background-color: {theme['primary']};
                    color: {theme['text']};
                    border-radius: {border_radius}px;
                    padding: {padding // 2}px {padding}px;
                }}
            """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self._create_header(main_layout)

        # Create pages
        self.stacked_widget = QStackedWidget()
        self._create_home_page()
        self._create_main_app_page()

        main_layout.addWidget(self.stacked_widget)

    def _create_header(self, parent_layout):
        header = QWidget()
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        # Add spacer to push home button to the right
        header_layout.addStretch()
        
        # Home button
        self.btn_home = QPushButton("Return Home")
        self.btn_home.hide()
        header_layout.addWidget(self.btn_home)

        parent_layout.addWidget(header)

    def _create_home_page(self):
        home_page = QWidget()
        layout = QVBoxLayout(home_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Analysis Input Section
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Enter stock ticker...")
        self.investment_amount = QLineEdit(placeholderText="Investment amount ($)")
        self.investment_timeframe = QLineEdit(placeholderText="Days to invest")
        self.btn_analyze = QPushButton("Analyze")

        for widget in [self.search, self.investment_amount, self.investment_timeframe, self.btn_analyze]:
            input_layout.addWidget(widget)

        layout.addWidget(input_widget)

        # Market News Section
        news_label = QLabel("Market News")
        news_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        layout.addWidget(news_label)

        self.news_feed = QTextEdit()
        self.news_feed.setReadOnly(True)
        self.news_feed.setMaximumHeight(200)
        layout.addWidget(self.news_feed)

        # Favorite Stocks Section
        favorites_label = QLabel("Favorite Stocks")
        favorites_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        layout.addWidget(favorites_label)

        self.favorites_scroll = QScrollArea()
        self.favorites_scroll.setWidgetResizable(True)
        self.favorites_content = QWidget()
        self.favorites_layout = QHBoxLayout(self.favorites_content)
        self.favorites_layout.setSpacing(10)
        self.favorites_scroll.setWidget(self.favorites_content)
        self.favorites_scroll.setMaximumHeight(150)
        layout.addWidget(self.favorites_scroll)

        # Recently Viewed Section
        recent_label = QLabel("Recently Viewed")
        recent_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        layout.addWidget(recent_label)

        self.recent_scroll = QScrollArea()
        self.recent_scroll.setWidgetResizable(True)
        self.recent_content = QWidget()
        self.recent_layout = QHBoxLayout(self.recent_content)
        self.recent_layout.setSpacing(10)
        self.recent_scroll.setWidget(self.recent_content)
        self.recent_scroll.setMaximumHeight(150)
        layout.addWidget(self.recent_scroll)

        # Market Analysis Section
        market_analysis_label = QLabel("Market Analysis")
        market_analysis_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        layout.addWidget(market_analysis_label)

        self.market_analysis = QTextEdit()
        self.market_analysis.setReadOnly(True)
        layout.addWidget(self.market_analysis)
        
        # Initial data load
        self._load_news_feed()
        self._load_favorites(["AAPL", "MSFT", "GOOGL"])
        self._load_market_analysis()

        self.stacked_widget.addWidget(home_page)

    def _load_market_data(self):
        # Fetch data for major indices (S&P 500, NASDAQ, Dow Jones)
        indices = ["^GSPC", "^IXIC", "^DJI"]  # Ticker symbols for S&P 500, NASDAQ, Dow Jones
        for index in indices:
            try:
                stock = self.stock_api.get_stock(index)
                info = stock.info
                current_price = info.get('currentPrice', 'N/A')
                name = info.get('displayName', index)

                # Check if current_price is a number before formatting
                if isinstance(current_price, (int, float)):
                    index_label = QLabel(f"{name}: ${current_price:.2f}")
                else:
                    index_label = QLabel(f"{name}: {current_price}")  # Display as is
                self.market_overview_layout.addWidget(index_label)
            except Exception as e:
                print(f"Error loading market data for {index}: {e}")
                error_label = QLabel(f"Error loading {index}")
                self.market_overview_layout.addWidget(error_label)

    def _load_news_feed(self):
        # Fetch news articles related to market and favorite stocks
        try:
            tickers = ["market"] + self.favorite_tickers  # Include general market news
            all_news = []
            for ticker in tickers:
                try:
                    news = self.stock_api.get_news(ticker, num_articles=2)
                    if isinstance(news, list):  # Check if news is a list
                        for article in news:
                            if isinstance(article, dict) and 'title' in article and 'description' in article:
                                all_news.append(article)
                            else:
                                print(f"Invalid article format for {ticker}: {article}")
                    else:
                        print(f"Unexpected news format for {ticker}: {type(news)}")
                except Exception as e:
                    print(f"Error fetching news for {ticker}: {e}")
                    continue

            news_text = "\n\n".join(
                f"{article['title']}\n{article['description'] or 'No description'}"
                for article in all_news[:5]  # Limit to 5 articles
            )
            self.news_feed.setPlainText(news_text)
        except Exception as e:
            self.news_feed.setPlainText(f"Error loading news: {str(e)}")

    def _create_main_app_page(self):
        main_page = QWidget()
        layout = QHBoxLayout(main_page)

        # Left sidebar
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        
        # Add existing widgets
        self.overview = StockOverview()
        self.metrics = KeyMetrics()
        self.ai_recommendation = RecommendationWidget()
        self.btn_add_favorite = QPushButton("Add to Favorites")

        # Add chat section
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        
        # Chat history
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMinimumHeight(200)
        self.chat_history.setPlaceholderText("Chat with AI Assistant...")
        
        # Input area
        input_container = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask about the current stock...")
        self.chat_input.returnPressed.connect(self._send_chat_message)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._send_chat_message)
        
        input_container.addWidget(self.chat_input)
        input_container.addWidget(self.send_button)
        
        # Add all to chat layout
        chat_layout.addWidget(self.chat_history)
        chat_layout.addLayout(input_container)

        # Add all widgets to sidebar
        for widget in [self.overview, self.metrics, self.ai_recommendation, 
                      self.btn_add_favorite, chat_container]:
            sidebar_layout.addWidget(widget)

        # Right side tabs
        self.tabs = QTabWidget()
        self._create_analysis_tab()
        self._create_chart_tab()

        layout.addWidget(sidebar)
        layout.addWidget(self.tabs)
        self.stacked_widget.addWidget(main_page)

    def _create_analysis_tab(self):
        analysis_tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)  # Make scroll area resize its widget
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)  # Add some padding
        layout.setSpacing(10)  # Space between cards

        self.news_card = AnalysisCard("Latest News")
        self.long_term_card = AnalysisCard("Buy/Sell Analysis")
        self.day_trade_card = AnalysisCard("Day Trading Analysis")
        self.strategy_card = AnalysisCard("Investment Strategy")  # Add new card

        # Set size policies to make cards expand horizontally
        for card in [self.news_card, self.long_term_card, self.day_trade_card, self.strategy_card]:  # Add strategy card
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            layout.addWidget(card)

        layout.addStretch()  # Add stretch at the bottom to prevent unnecessary expansion
        scroll.setWidget(content)
        
        # Create a layout for the tab itself
        tab_layout = QVBoxLayout(analysis_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins to use full space
        tab_layout.addWidget(scroll)

        self.tabs.addTab(analysis_tab, "Analysis")

    def _create_chart_tab(self):
        chart_page = QWidget()
        layout = QVBoxLayout(chart_page)
        
        # Controls
        controls = QHBoxLayout()
        
        # Time frame selector
        self.time_frame = QComboBox()
        self.time_frame.addItems(["1D", "1W", "1M", "3M", "6M", "1Y", "5Y"])
        self.time_frame.setCurrentText("3M")
        self.time_frame.currentTextChanged.connect(self._update_chart)
        
        # Chart type selector
        self.chart_type = QComboBox()
        self.chart_type.addItems(["Line", "Candlestick", "Both"])
        self.chart_type.setCurrentText("Both")
        self.chart_type.currentTextChanged.connect(self._update_chart)
        
        # Add control widgets
        controls.addWidget(QLabel("Time Frame:"))
        controls.addWidget(self.time_frame)
        controls.addWidget(QLabel("Chart Type:"))
        controls.addWidget(self.chart_type)
        controls.addStretch()
        
        # Create chart
        self.chart = StockChart()
        
        # Add to layout
        layout.addLayout(controls)
        layout.addWidget(self.chart)
        
        self.tabs.addTab(chart_page, "Charts")

    def _update_chart(self):
        if self.current_ticker:
            self.chart.update_chart(
                self.current_ticker,
                self.time_frame.currentText(),
                self.chart_type.currentText()
            )

    def _create_stock_card(self, ticker, current_price, prev_close, container_layout):
        """Create a stock card for either favorites or recently viewed"""
        try:
            # Create stock card
            card = QFrame()
            card.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            card.setLineWidth(1)
            card_layout = QVBoxLayout(card)

            # Ticker label
            ticker_label = QLabel(ticker)
            ticker_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
            ticker_label.setAlignment(Qt.AlignCenter)

            # Price label
            price_label = QLabel(f"${current_price:.2f}")
            price_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
            price_label.setAlignment(Qt.AlignCenter)

            # Set color based on trend
            if current_price > prev_close:
                card.setStyleSheet("background-color: #1e3320; color: white;")
            elif current_price < prev_close:
                card.setStyleSheet("background-color: #3d1f1f; color: white;")
            else:
                card.setStyleSheet("background-color: #2d2d2d; color: white;")

            card_layout.addWidget(ticker_label)
            card_layout.addWidget(price_label)
            
            # Set fixed size for the card
            card.setFixedSize(120, 80)
            container_layout.addWidget(card)

        except Exception as e:
            print(f"Error creating stock card for {ticker}: {e}")

    def _load_favorites(self, tickers=None):
        # Clear existing widgets
        for i in reversed(range(self.favorites_layout.count())):
            widget = self.favorites_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        if tickers is None:
            tickers = self.favorite_tickers

        for ticker in tickers:
            try:
                stock = self.stock_api.get_stock(ticker)
                info = stock.info
                current_price = info.get('currentPrice', 'N/A')
                prev_close = info.get('previousClose', current_price)
                self._create_stock_card(ticker, current_price, prev_close, self.favorites_layout)
            except Exception as e:
                print(f"Error loading favorite stock {ticker}: {e}")

    def _load_recent_tickers(self):
        # Clear existing widgets
        for i in reversed(range(self.recent_layout.count())):
            widget = self.recent_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for ticker in self.recent_tickers:
            try:
                stock = self.stock_api.get_stock(ticker)
                info = stock.info
                current_price = info.get('currentPrice', 'N/A')
                prev_close = info.get('previousClose', current_price)
                self._create_stock_card(ticker, current_price, prev_close, self.recent_layout)
            except Exception as e:
                print(f"Error loading recent stock {ticker}: {e}")

    def _load_market_analysis(self):
        prompt = """
        Analyze the current market conditions and list specific sectors that are on uptrend or downtrend.
        Format your response exactly like this:
        UPTREND SECTORS:
        - Sector name 1: Brief reason
        - Sector name 2: Brief reason
        - Sector name 3: Brief reason

        DOWNTREND SECTORS:
        - Sector name 1: Brief reason
        - Sector name 2: Brief reason
        - Sector name 3: Brief reason
        
        Base your analysis on current market conditions, recent economic data, and sector performance.
        Be specific and concise with each sector.
        """
        try:
            # Get AI analysis
            response = self.ai_client.analyze(prompt, "sector analyst")
            content = response['message']['content']
            cleaned_content = remove_think_tags(content)
            
            # Clear existing text
            self.market_analysis.clear()
            
            # Create cursor and format sections
            cursor = self.market_analysis.textCursor()
            
            # Split content into sections
            sections = cleaned_content.split('\n\n')
            
            for section in sections:
                if "UPTREND SECTORS:" in section:
                    color = QColor("#4CAF50")  # Green
                elif "DOWNTREND SECTORS:" in section:
                    color = QColor("#F44336")  # Red
                else:
                    color = QColor("#FFFFFF")  # White for other text
                
                # Set text color
                format = cursor.charFormat()
                format.setForeground(color)
                cursor.setCharFormat(format)
                
                # Insert text with format
                cursor.insertText(section + "\n\n")
                
        except Exception as e:
            print(f"Market analysis error: {str(e)}")  # Debug print
            self.market_analysis.setPlainText(f"Error generating market analysis: {str(e)}")

    def _analyze(self):
        ticker = self.search.text().strip().upper()
        investment_amount = self.investment_amount.text().strip()
        investment_timeframe = self.investment_timeframe.text().strip()

        if not ticker or not investment_amount or not investment_timeframe:
            self._show_error("Please enter a stock ticker, investment amount, and timeframe")
            return

        try:
            investment_amount = float(investment_amount)
            investment_timeframe = int(investment_timeframe)
        except ValueError:
            self._show_error("Invalid investment amount or timeframe")
            return

        try:
            self.current_ticker = ticker
            
            # Update recent tickers list
            if ticker in self.recent_tickers:
                self.recent_tickers.remove(ticker)
            self.recent_tickers.insert(0, ticker)
            self.recent_tickers = self.recent_tickers[:self.max_recent_tickers]  # Keep only the most recent
            self._load_recent_tickers()

            stock = self.stock_api.get_stock(ticker)

            # Update UI components
            self._update_ui()
            self._update_news(ticker)
            if stock:
                self._generate_analysis(stock, investment_amount, investment_timeframe) # Pass investment details
                self._update_chart()  # Use new method
            self.chart.update_chart(ticker)

            self.stacked_widget.setCurrentIndex(1)
            self.btn_home.show()
            self.update_timer.start()

        except Exception as e:
            self._show_error(str(e))

    def _update_ui(self):
        if not self.current_ticker:
            return

        try:
            stock = self.stock_api.get_stock(self.current_ticker)
            info = stock.info

            # Check if info is None or empty
            if not info:
                print(f"Error: No data received from yfinance for {self.current_ticker}")
                self.overview.ticker.setText(self.current_ticker)
                self.overview.price.setText("N/A")
                self.metrics.update_metrics({})
                return

            # Update price and metrics
            current_price = info.get('currentPrice', 'N/A')
            prev_close = info.get('previousClose', 'N/A')

            self.overview.ticker.setText(self.current_ticker)
            self.overview.price.setText(f"${current_price:.2f}" if current_price != 'N/A' else "N/A")

            # Update metrics
            metrics = self._get_stock_metrics(stock)
            self.metrics.update_metrics(metrics)

        except Exception as e:
            print(f"Update error: {e}")

    def _get_stock_metrics(self, stock):
        metrics = {}
        info = stock.info  # Access stock info

        # Check if info is None or empty
        if not info:
            print("Error: No stock info available")
            return metrics

        # Ensure values are float64 and handle missing keys
        metrics['pe_ratio'] = np.float64(info.get('trailingPE', 0) or 0)
        metrics['dividend_yield'] = np.float64(info.get('dividendYield', 0) or 0)
        metrics['market_cap'] = np.float64(info.get('marketCap', 0) or 0)
        metrics['volume'] = np.float64(info.get('volume', 0) or 0)
        return metrics

    def _update_news(self, ticker):
        try:
            news = self.stock_api.get_news(ticker)
            news_text = ""
            for i, article in enumerate(news[:3]):
                try:
                    title = article.get('title', 'No Title')
                    description = article.get('description', 'No Description')
                    news_text += f"{title}\n{description}\n\n"
                except Exception as e:
                    news_text += f"Error processing article {i}: {str(e)}\n\n"
            self.news_card.content.setPlainText(news_text)
        except Exception as e:
            self.news_card.content.setPlainText(f"News error: {str(e)}")

    def _generate_analysis(self, stock, investment_amount, investment_timeframe):
        # Generate analysis using AI client
        try:
            # Long-term analysis
            lt_prompt = self._create_long_term_prompt(stock, investment_amount, investment_timeframe)
            lt_response = self.ai_client.analyze(lt_prompt, "financial analyst")
            lt_content = lt_response['message']['content']
            lt_content = remove_think_tags(lt_content)  # Remove <think> tags
            self.long_term_card.content.setPlainText(lt_content)

            # Day-trade analysis 
            dt_prompt = self._create_day_trade_prompt(stock, investment_amount, investment_timeframe)
            dt_response = self.ai_client.analyze(dt_prompt, "day trading expert")
            dt_content = dt_response['message']['content']
            dt_content = remove_think_tags(dt_content)  # Remove <think> tags
            self.day_trade_card.content.setPlainText(dt_content)

            # Generate investment strategy
            strategy_prompt = self._create_strategy_prompt(stock, investment_amount, investment_timeframe)
            strategy_response = self.ai_client.analyze(strategy_prompt, "investment strategist")
            strategy_content = strategy_response['message']['content']
            strategy_content = remove_think_tags(strategy_content)
            self.strategy_card.content.setPlainText(strategy_content)

            # Update recommendations
            self._update_recommendations(lt_response['message']['content'])

        except Exception as e:
            print(f"Analysis error: {e}")

    def _update_recommendations(self, analysis_text):
        recs = parse_recommendations(analysis_text)
        self.ai_recommendation.update_recommendations(recs)

    def _create_long_term_prompt(self, stock, investment_amount, investment_timeframe):
        ticker = stock.info.get('symbol', 'Unknown')
        name = stock.info.get('displayName', 'Unknown')
        industry = stock.info.get('industry', 'Unknown')
        current_price = stock.info.get('currentPrice', 'Unknown')

        prompt = f"""
        Analyze the long-term investment potential of {name} (Ticker: {ticker}) in the {industry} industry.
        The current stock price is ${current_price:.2f}.
        I am planning to invest ${investment_amount:.2f} for a timeframe of {investment_timeframe} days.
        Provide a detailed analysis covering potential growth factors, risks, and a final investment recommendation.
        Also, provide a buy, hold, and sell suggestion.
        """
        return prompt

    def _create_day_trade_prompt(self, stock, investment_amount, investment_timeframe):
        ticker = stock.info.get('symbol', 'Unknown')
        name = stock.info.get('displayName', 'Unknown')
        current_price = stock.info.get('currentPrice', 'Unknown')

        prompt = f"""
        Provide a day trading analysis for {name} (Ticker: {ticker}).
        The current stock price is ${current_price:.2f}.
        I am considering allocating ${investment_amount:.2f} for day trading over a period of {investment_timeframe} days.
        Focus on potential entry and exit points, technical indicators, and risk management strategies.
        Also, provide a buy, hold, and sell suggestion.
        """
        return prompt

    def _create_strategy_prompt(self, stock, investment_amount, investment_timeframe):
        ticker = stock.info.get('symbol', 'Unknown')
        name = stock.info.get('displayName', 'Unknown')
        current_price = stock.info.get('currentPrice', 'Unknown')
        
        prompt = f"""
        Create a clear, step-by-step investment strategy for {name} (Ticker: {ticker}).
        Investment Amount: ${investment_amount:.2f}
        Current Price: ${current_price:.2f}
        Timeframe: {investment_timeframe} days

        Please provide specific instructions for:
        1. The exact price point to enter the investment (entry price)
        2. How long to hold the investment
        3. The target price to sell and take profits
        4. Specific conditions for when to reinvest
        5. Stop loss recommendation to minimize risk

        Format the response clearly with bullet points and specific numbers.
        Avoid general advice - provide exact figures and timelines.
        """
        return prompt

    def _connect_signals(self):
        self.btn_analyze.clicked.connect(self._analyze)
        self.search.returnPressed.connect(self._analyze)
        self.btn_home.clicked.connect(self._return_home)
        self.btn_add_favorite.clicked.connect(self._add_to_favorites)

        # Connect card maximize signals
        self.news_card.maximize_signal.connect(self._show_maximized_card)
        self.long_term_card.maximize_signal.connect(self._show_maximized_card)
        self.day_trade_card.maximize_signal.connect(self._show_maximized_card)
        self.strategy_card.maximize_signal.connect(self._show_maximized_card)

        self.send_button.clicked.connect(self._send_chat_message)

    def _return_home(self):
        self.stacked_widget.setCurrentIndex(0)
        self.btn_home.hide()
        self.update_timer.stop()

    def _add_to_favorites(self):
        if self.current_ticker and self.current_ticker not in self.favorite_tickers:
            self.favorite_tickers.append(self.current_ticker)
            self._load_favorites()

    def _show_maximized_card(self, card_data):
        """
        Show a maximized version of the analysis card
        
        Args:
            card_data (dict): Dictionary containing card title and content
        """
        dialog = QDialog(self)
        dialog.setWindowIcon(self.app_icon)  # Set icon for dialog
        dialog.setWindowTitle(card_data.get('title', 'Analysis'))
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        content = QTextEdit()
        content.setPlainText(card_data.get('content', ''))
        content.setReadOnly(True)
        
        layout.addWidget(content)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        
        dialog.exec()

    def _show_error(self, message):
        error_dialog = QMessageBox(self)
        error_dialog.setWindowIcon(self.app_icon)  # Set icon for error dialog
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(message)
        error_dialog.exec()

    def _send_chat_message(self):
        if not self.chat_input.text().strip():
            return

        # Format user message with some padding
        user_message = self.chat_input.text()
        self.chat_history.append("\n<br><div style='margin: 10px 0;'><b>You:</b> " + user_message + "</div>")
        self.chat_input.clear()

        try:
            context = self._create_chat_context()
            prompt = f"""
            Context about {self.current_ticker}:
            {context}

            User Question: {user_message}
            
            Please provide a helpful answer using the context provided.
            Format your response with clear paragraphs and bullet points where appropriate.
            """

            # Use CHAT_MODEL instead of default model
            response = self.ai_client.analyze(prompt, "financial advisor", model=CHAT_MODEL)
            ai_response = response['message']['content']
            cleaned_response = remove_think_tags(ai_response)
            
            # Format AI response with improved readability
            formatted_response = cleaned_response.replace("\n", "<br>")  # Convert newlines to HTML breaks
            formatted_response = formatted_response.replace("• ", "<br>• ")  # Add spacing before bullet points
            formatted_response = formatted_response.replace("- ", "<br>• ")  # Convert dashes to bullet points
            
            # Add the formatted response with styling
            self.chat_history.append(
                f"""<div style='background-color: #1e1e1e; margin: 10px 0; padding: 10px; border-radius: 5px;'>
                <b>AI Assistant:</b><br><br>{formatted_response}
                </div><br>"""
            )
            
        except Exception as e:
            self.chat_history.append(
                """<div style='background-color: #3d1f1f; margin: 10px 0; padding: 10px; border-radius: 5px;'>
                <b>AI:</b> Sorry, I encountered an error: """ + str(e) + 
                "</div><br>"
            )

        # Scroll to bottom
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )

    def _create_chat_context(self):
        """Create context from current stock analysis for the AI"""
        if not self.current_ticker:
            return "No stock is currently selected. Please select a stock first."

        try:
            stock = self.stock_api.get_stock(self.current_ticker)
            info = stock.info
            context_parts = []
            
            # Basic stock information
            if info:
                context_parts.extend([
                    f"Stock: {info.get('longName', self.current_ticker)} ({self.current_ticker})",
                    f"Current Price: ${info.get('currentPrice', 'N/A')}",
                    f"Industry: {info.get('industry', 'N/A')}",
                    f"Market Cap: ${info.get('marketCap', 0) / 1e9:.2f}B",
                    f"P/E Ratio: {info.get('trailingPE', 'N/A')}",
                    f"52 Week Range: ${info.get('fiftyTwoWeekLow', 'N/A')} - ${info.get('fiftyTwoWeekHigh', 'N/A')}"
                ])

            # Add recent analysis
            if hasattr(self, 'long_term_card') and self.long_term_card.content.toPlainText():
                context_parts.append("\nRecent Analysis:")
                context_parts.append(self.long_term_card.content.toPlainText())

            # Add investment strategy if available
            if hasattr(self, 'strategy_card') and self.strategy_card.content.toPlainText():
                context_parts.append("\nInvestment Strategy:")
                context_parts.append(self.strategy_card.content.toPlainText())

            # Add day trading insights if available
            if hasattr(self, 'day_trade_card') and self.day_trade_card.content.toPlainText():
                context_parts.append("\nDay Trading Insights:")
                context_parts.append(self.day_trade_card.content.toPlainText())

            return "\n".join(context_parts)
            
        except Exception as e:
            return f"Error retrieving context: {str(e)}"

    # ...rest of the class remains unchanged...

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application-wide icon
    app_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(app_path, "assets", "Axlotto transparent.ico")
    print(f"Setting application icon from: {icon_path}")
    print(f"File exists: {os.path.exists(icon_path)}")
    
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    window = ModernStockApp()
    window.show()
    sys.exit(app.exec())