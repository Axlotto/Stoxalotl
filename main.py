# main.py
import sys
import os
import re
import time  # Add this import
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QSettings, QPropertyAnimation, QEasingCurve  # Added QSettings, QPropertyAnimation, and QEasingCurve here
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
    QComboBox,  # Added QComboBox
    QProgressBar  # Add QProgressBar
)
import pyqtgraph as pg
import numpy as np  # Import numpy
from request_counter import RequestCounter

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
from api_client import StockAPI, AIClient, StockAPIError, AIClientError  # Specify the full path and import StockAPIError and AIClientError
from helpers import parse_recommendations, analysis_color, remove_think_tags  # Specify the full path
from widgets import StockOverview
from cache import Cache

# Initialize cache with a TTL of 5 minutes
cache = Cache(ttl=300)

class ModernStockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize settings first
        self.settings = QSettings("Stoxalotl", "Preferences")
        
        # Get current theme from settings or use default
        self.current_theme = self.settings.value("Theme", "Dark")
        
        # Rest of initialization
        self.app_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "Axlotto transparent.ico")
        self.app_icon = QIcon(self.app_icon_path)
        
        # Set window icon
        self.setWindowIcon(self.app_icon)
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("Stoxalotl")
        self.tray_icon.show()
        
        self.setWindowTitle("Stoxalotl")
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(1024, 768)
        self.current_ticker = None
        self.recent_tickers = []  # Add list for recently viewed tickers
        self.max_recent_tickers = 5  # Maximum number of recent tickers to show

        # Initialize request counter
        self.request_counter = RequestCounter()
        
        # Initialize API clients with counter
        self.stock_api = StockAPI(request_counter=self.request_counter)
        self.ai_client = AIClient(request_counter=self.request_counter)

        # Initialize chat box
        self.chat_box = QTextEdit()
        self.chat_input = QLineEdit()
        self.send_button = QPushButton("Send")

        # Setup UI and timer
        self._setup_ui()
        self._setup_styles()
        self._setup_status_bar()
        self._connect_signals()
        self._init_update_timer()

        # Initialize debounce timer
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._analyze)

        # Initialize loading circle
        self.loading_circle = QProgressBar(self)
        self.loading_circle.setRange(0, 100)
        self.loading_circle.setValue(0)
        self.loading_circle.setTextVisible(False)
        self.loading_circle.setFixedSize(100, 100)
        self.loading_circle.setStyleSheet("""
            QProgressBar {
                border: 2px solid #00bcd4;
                border-radius: 50px;
                background-color: #1a1a1a;
            }
            QProgressBar::chunk {
                background-color: #00bcd4;
                border-radius: 50px;
            }
        """)
        self.loading_circle.hide()

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
        header_layout.setContentsMargins(24, 0, 12, 0)  # Reduced right margin
        header_layout.setSpacing(0)  # Remove default spacing

        # Logo/Brand section (left side)
        brand_label = QLabel("Stoxalotl")
        brand_label.setFont(QFont(FONT_FAMILY, 18, QFont.Bold))
        brand_label.setStyleSheet(f"color: {COLOR_PALETTES['Dark']['primary']};")
        
        # Search container
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)  # Small gap between search and button

        # Search bar
        self.search = QLineEdit()
        self.search.setPlaceholderText("Enter ticker...")
        self.search.setFixedWidth(150)
        self.search.setFixedHeight(32)  # Match button height
        self.search.setStyleSheet("""
            QLineEdit {
                border: 1px solid #333;
                border-radius: 4px;
                padding: 0 10px;
                background: #1a1a1a;
                color: white;
            }
            QLineEdit:focus {
                border-color: #00bcd4;
            }
        """)
        self.search.textChanged.connect(self._on_search_text_changed)  # Connect to debounce method

        # Analyze button
        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setFixedSize(90, 32)  # Match search bar height
        self.btn_analyze.setStyleSheet("""
            QPushButton {
                background-color: #00bcd4;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0097a7;
            }
            QPushButton:pressed {
                background-color: #006064;
            }
        """)
        self.btn_analyze.clicked.connect(self._analyze)  # Connect directly to analyze method

        # Home button
        self.btn_home = QPushButton("Return Home")
        self.btn_home.hide()
        self.btn_home.setFixedHeight(32)  # Match other buttons
        self.btn_home.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #858585;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
                color: white;
            }
        """)
        self.btn_home.clicked.connect(self._return_home)

        # Add widgets to layouts
        search_layout.addWidget(self.search)
        search_layout.addWidget(self.btn_analyze)
        
        # Add all sections to header
        header_layout.addWidget(brand_label)
        header_layout.addStretch()
        header_layout.addWidget(search_container)
        header_layout.addSpacing(12)  # Space before home button
        header_layout.addWidget(self.btn_home)

        parent_layout.addWidget(header)

    def _on_search_text_changed(self):
        """Debounce method for search input"""
        self.debounce_timer.start(500)  # Wait for 500ms before triggering the analyze method

    def _create_home_page(self):
        home_page = QWidget()
        layout = QVBoxLayout(home_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Remove the search section from home page since it's now in the header
        
        # Market News Section
        news_label = QLabel("Market News")
        news_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        layout.addWidget(news_label)

        self.news_feed = QTextEdit()
        self.news_feed.setReadOnly(True)
        self.news_feed.setMaximumHeight(200)
        layout.addWidget(self.news_feed)

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
        self._load_recent_tickers()
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
            tickers = ["market"]  # Include general market news
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
                except StockAPIError as e:
                    print(f"Error fetching news for {ticker}: {e}")
                    continue

            news_text = "\n\n".join(
                f"{article['title']}\n{article['description'] or 'No description'}"
                for article in all_news[:5]  # Limit to 5 articles
            )
            self.news_feed.setPlainText(news_text)
        except StockAPIError as e:
            self.news_feed.setPlainText(f"Error loading news: {str(e)}")
        except Exception as e:
            self.news_feed.setPlainText(f"Error loading news: {str(e)}")

    def _create_main_app_page(self):
        main_page = QWidget()
        layout = QHBoxLayout(main_page)

        # Left sidebar
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        
        # Add existing widgets (removed btn_add_favorite)
        self.overview = StockOverview()
        self.metrics = KeyMetrics()
        self.ai_recommendation = RecommendationWidget()

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

        # Add widgets to sidebar (removed btn_add_favorite)
        for widget in [self.overview, self.metrics, self.ai_recommendation, chat_container]:
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

    def _load_recent_tickers(self):
        # Clear existing widgets
        for i in reversed(range(self.recent_layout.count())):
            widget = self.recent_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for ticker in self.recent_tickers:
            try:
                stock_data = self.stock_api.get_stock(ticker)
                current_price = stock_data['c']
                prev_close = stock_data['pc']

                self._create_stock_card(ticker, current_price, prev_close, self.recent_layout)
            except StockAPIError as e:
                print(f"Error loading recent stock {ticker}: {e}")
            except Exception as e:
                print(f"Error loading recent stock {ticker}: {e}")
            time.sleep(1)  # Add delay between requests

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

        if not ticker:
            self._show_error("Please enter a stock ticker")
            return

        try:
            self.current_ticker = ticker
            
            # Update recent tickers list
            if (ticker in self.recent_tickers):
                self.recent_tickers.remove(ticker)
            self.recent_tickers.insert(0, ticker)
            self.recent_tickers = self.recent_tickers[:self.max_recent_tickers]
            self._load_recent_tickers()

            stock = self.stock_api.get_stock(ticker)

            # Update UI components with default values for analysis
            self._update_ui()
            self._update_news(ticker)
            if stock:
                self._generate_analysis(stock, investment_amount=10000, investment_timeframe=30)
                self._update_chart()
            self.chart.update_chart(ticker)

            self.stacked_widget.setCurrentIndex(1)
            self.btn_home.show()
            self.update_timer.start()

        except StockAPIError as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"An unexpected error occurred: {str(e)}")

    def _update_ui(self):
        if not self.current_ticker:
            return

        try:
            stock_data = self.stock_api.get_stock(self.current_ticker)
            current_price = stock_data['c']
            prev_close = stock_data['pc']

            # Calculate price change
            change_amount = current_price - prev_close
            change_percent = (change_amount / prev_close) * 100 if prev_close != 0 else 0
            change_text = f"{change_amount:+.2f} ({change_percent:+.2f}%)"

            # Update overview with all information including favorite status
            self.overview.update_overview(
                self.current_ticker,
                current_price,
                change_text
            )

            # Update metrics
            metrics = self._get_stock_metrics(stock_data)
            self.metrics.update_metrics(metrics)

        except StockAPIError as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"An unexpected error occurred: {str(e)}")

    def _get_stock_metrics(self, stock_data):
        metrics = {}
        # Ensure values are float64 and handle missing keys
        metrics['pe_ratio'] = np.float64(stock_data.get('pe_ratio', 0) or 0)
        metrics['dividend_yield'] = np.float64(stock_data.get('dividend_yield', 0) or 0)
        metrics['market_cap'] = np.float64(stock_data.get('market_cap', 0) or 0)
        metrics['volume'] = np.float64(stock_data.get('volume', 0) or 0)
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

        except AIClientError as e:
            self._show_error(str(e))
        except Exception as e:
            self._show_error(f"An unexpected error occurred: {str(e)}")

    def _update_recommendations(self, analysis_text):
        recs = parse_recommendations(analysis_text)
        self.ai_recommendation.update_recommendations(recs)

    def _create_long_term_prompt(self, stock_data, investment_amount, investment_timeframe):
        current_price = stock_data['c']

        prompt = f"""
        Analyze the long-term investment potential of {self.current_ticker}.
        The current stock price is ${current_price:.2f}.
        I am planning to invest ${investment_amount:.2f} for a timeframe of {investment_timeframe} days.
        Provide a detailed analysis covering potential growth factors, risks, and a final investment recommendation.
        Also, provide a buy, hold, and sell suggestion.
        """
        return prompt

    def _create_day_trade_prompt(self, stock_data, investment_amount, investment_timeframe):
        current_price = stock_data['c']

        prompt = f"""
        Provide a day trading analysis for {self.current_ticker}.
        The current stock price is ${current_price:.2f}.
        I am considering allocating ${investment_amount:.2f} for day trading over a period of {investment_timeframe} days.
        Focus on potential entry and exit points, technical indicators, and risk management strategies.
        Also, provide a buy, hold, and sell suggestion.
        """
        return prompt

    def _create_strategy_prompt(self, stock_data, investment_amount, investment_timeframe):
        current_price = stock_data['c']

        prompt = f"""
        Create a clear, step-by-step investment strategy for {self.current_ticker}.
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
        # Remove search functionality from home page and use header only
        self.search.returnPressed.connect(self._analyze)
        self.btn_analyze.clicked.connect(self._analyze)
        self.btn_home.clicked.connect(self._return_home)

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
        error_dialog.setInformativeText("Please try again later or contact support if the issue persists.")
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
            stock_data = self.stock_api.get_stock(self.current_ticker)
            current_price = stock_data['c']
            market_cap = stock_data.get('marketCap', 0)
            pe_ratio = stock_data.get('trailingPE', 0)
            dividend_yield = stock_data.get('dividendYield', 0)

            context_parts = [
                f"Stock: {self.current_ticker}",
                f"Current Price: ${current_price:.2f}",
                f"Market Cap: ${market_cap / 1e9:.2f}B",
                f"P/E Ratio: {pe_ratio:.2f}",
                f"Dividend Yield: {dividend_yield:.2f}%"
            ]

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

    def _setup_status_bar(self):
        self.statusBar().showMessage('')
        
        # Create labels for different types of requests
        self.api_requests_label = QLabel("API Calls: 0")
        self.cache_requests_label = QLabel("Cached: 0")
        self.total_requests_label = QLabel("Total: 0")
        
        # Style the labels
        for label in [self.api_requests_label, self.cache_requests_label, self.total_requests_label]:
            label.setStyleSheet("""
                QLabel {
                    padding: 5px;
                    font-weight: bold;
                    margin-right: 10px;
                }
            """)
        
        # Set specific colors
        self.api_requests_label.setStyleSheet(self.api_requests_label.styleSheet() + "color: #ff4444;")  # Red for API calls
        self.cache_requests_label.setStyleSheet(self.cache_requests_label.styleSheet() + "color: #00C851;")  # Green for cache
        self.total_requests_label.setStyleSheet(self.total_requests_label.styleSheet() + "color: #00bcd4;")  # Blue for total
        
        # Add labels to status bar
        self.statusBar().addPermanentWidget(self.api_requests_label)
        self.statusBar().addPermanentWidget(self.cache_requests_label)
        self.statusBar().addPermanentWidget(self.total_requests_label)

        # Add rate limit warning label
        self.rate_limit_label = QLabel("Rate Limit: 30/sec")
        self.rate_limit_label.setStyleSheet("color: #FF8800; font-weight: bold; padding: 5px;")
        self.statusBar().addPermanentWidget(self.rate_limit_label)

        # Update request counts every second
        self.request_timer = QTimer(self)
        self.request_timer.timeout.connect(self._update_request_count)
        self.request_timer.start(1000)  # Update every second

    def _update_request_count(self):
        counts = self.request_counter.get_counts()
        time_since_reset = self.request_counter.time_since_reset()
        
        self.api_requests_label.setText(f"API Calls: {counts['api']}")
        self.cache_requests_label.setText(f"Cached: {counts['cache']}")
        self.total_requests_label.setText(
            f"Total: {counts['total']} | Reset: {time_since_reset.seconds}s ago"
        )
        
        # Update rate limit warning color based on API call count
        if counts['api'] > 25:  # Warning when close to limit
            self.rate_limit_label.setStyleSheet("color: #ff4444; font-weight: bold; padding: 5px;")
        else:
            self.rate_limit_label.setStyleSheet("color: #FF8800; font-weight: bold; padding: 5px;")

    def closeEvent(self, event):
        self.request_timer.stop()
        # ...existing code...

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