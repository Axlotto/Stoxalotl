# main.py
import sys
import os
import re
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QColor, QPixmap, QIcon
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
    QSizePolicy
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
from config import COLOR_PALETTES, FONT_FAMILY, FONT_SIZES, FONT_CHOICES, OLLAMA_MODEL, NEWS_API_KEY, NEWS_API_URL, UI_CONFIG
from widgets import KeyMetrics, RecommendationWidget,  AnalysisCard, StockChart, StockOverview
from api_client import StockAPI, AIClient  # Specify the full path
from helpers import parse_recommendations, analysis_color, remove_think_tags  # Specify the full path
from widgets import StockOverview


class ModernStockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Analysis Pro")
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(1024, 768)
        self.current_ticker = None
        self.favorite_tickers = []

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

        # Logo and title
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_img = QLabel()
        pixmap = QPixmap(r"C:\Users\taylo\OneDrive\Desktop\Code\Axlotto transparent.png")
        if not pixmap.isNull():
            logo_img.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo = QLabel("Stoxalotl")
        self.logo.setFont(QFont(FONT_FAMILY, FONT_SIZES["title"], QFont.DemiBold))
        logo_layout.addWidget(logo_img)
        logo_layout.addWidget(self.logo)

        # Search and input fields
        self.search = QLineEdit()
        self.search.setPlaceholderText("Enter stock ticker...")
        self.investment_amount = QLineEdit(placeholderText="Investment amount ($)")
        self.investment_timeframe = QLineEdit(placeholderText="Days to invest")
        self.btn_analyze = QPushButton("Analyze")
        self.btn_home = QPushButton("Return Home")
        self.btn_home.hide()

        # Add widgets to header
        header_layout.addWidget(logo_container)
        header_layout.addStretch()
        header_layout.addWidget(self.search)
        header_layout.addWidget(self.investment_amount)
        header_layout.addWidget(self.investment_timeframe)
        header_layout.addWidget(self.btn_analyze)
        header_layout.addWidget(self.btn_home)

        parent_layout.addWidget(header)

    def _create_home_page(self):
        home_page = QWidget()
        layout = QVBoxLayout(home_page)
        layout.setContentsMargins(20, 20, 20, 20)

        # Logo
        logo_label = QLabel("Stoxalotl")
        logo_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["title"] + 8, QFont.Bold))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)

        # Market Overview
        market_overview_label = QLabel("Market Overview")
        market_overview_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        layout.addWidget(market_overview_label)

        self.market_overview_widget = QWidget()
        self.market_overview_layout = QHBoxLayout(self.market_overview_widget)
        layout.addWidget(self.market_overview_widget)
        self._load_market_data()

        # Favorites section
        favorites_label = QLabel("Favorite Stocks")
        favorites_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        layout.addWidget(favorites_label)

        self.favorites_scroll = QScrollArea()
        self.favorites_scroll.setWidgetResizable(True)
        self.favorites_content = QWidget()
        self.favorites_layout = QHBoxLayout(self.favorites_content)
        self.favorites_scroll.setWidget(self.favorites_content)
        layout.addWidget(self.favorites_scroll)

        # News Feed
        news_label = QLabel("Market News")
        news_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        layout.addWidget(news_label)

        self.news_feed = QTextEdit()
        self.news_feed.setReadOnly(True)
        layout.addWidget(self.news_feed)
        self._load_news_feed()

        self.stacked_widget.addWidget(home_page)
        self._load_favorites(["AAPL", "MSFT", "GOOGL"])

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
        self.overview = StockOverview()
        self.metrics = KeyMetrics()
        self.ai_recommendation = RecommendationWidget()
        self.btn_add_favorite = QPushButton("Add to Favorites")

        sidebar_layout.addWidget(self.overview)
        sidebar_layout.addWidget(self.metrics)
        sidebar_layout.addWidget(self.ai_recommendation)
        sidebar_layout.addWidget(self.btn_add_favorite)

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
        content = QWidget()
        layout = QVBoxLayout(content)

        self.news_card = AnalysisCard("Latest News")
        self.long_term_card = AnalysisCard("Buy/Sell Analysis")
        self.day_trade_card = AnalysisCard("Day Trading Analysis")

        layout.addWidget(self.news_card)
        layout.addWidget(self.long_term_card)
        layout.addWidget(self.day_trade_card)

        scroll.setWidget(content)
        self.tabs.addTab(scroll, "Analysis")

    def _create_chart_tab(self):
        self.chart = StockChart()
        self.tabs.addTab(self.chart, "Charts")

    def _load_favorites(self, tickers):
        # Implementation from original code
        pass

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
            stock = self.stock_api.get_stock(ticker)

            # Update UI components
            self._update_ui()
            self._update_news(ticker)
            if stock:
                self._generate_analysis(stock, investment_amount, investment_timeframe) # Pass investment details
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

            # Update price and metrics
            current_price = info.get('currentPrice', 'N/A')
            prev_close = info.get('previousClose', 'N/A')

            self.overview.ticker.setText(self.current_ticker)
            self.overview.price.setText(f"${current_price:.2f}" if current_price != 'N/A' else "N/A")

            # Update metrics
            metrics = self._get_stock_metrics(stock)
            # Convert metrics values to float64 if needed before passing to widgets
            # metrics = {k: np.float64(v) if isinstance(v, (int, float)) else v for k, v in metrics.items()}
            self.metrics.update_metrics(metrics)

        except Exception as e:
            print(f"Update error: {e}")

    def _get_stock_metrics(self, stock):
        # Implementation from original code
        # Example:
        metrics = {}
        # Ensure values are float64
        # metrics['pe_ratio'] = np.float64(stock.info.get('trailingPE', 0))
        return metrics

    def _update_news(self, ticker):
        try:
            news = self.stock_api.get_news(ticker)
            news_text = "\n\n".join(
                f"{article['title']}\n{article['description'] or 'No description'}"
                for article in news['articles'][:3]
            )
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

            # Update recommendations
            self._update_recommendations(lt_response['message']['content'])

        except Exception as e:
            print(f"Analysis error: {e}")

    def _update_recommendations(self, analysis_text):
        recs = parse_recommendations(analysis_text)
        self.ai_recommendation.update_recommendations(recs)

    def _create_long_term_prompt(self, stock, investment_amount, investment_timeframe):
        # Implementation from original code
        # Include investment_amount and investment_timeframe in the prompt
        pass

    def _create_day_trade_prompt(self, stock, investment_amount, investment_timeframe):
        # Implementation from original code
        # Include investment_amount and investment_timeframe in the prompt
        pass

    def _connect_signals(self):
        self.btn_analyze.clicked.connect(self._analyze)
        self.search.returnPressed.connect(self._analyze)
        self.btn_home.clicked.connect(self._return_home)
        self.btn_add_favorite.clicked.connect(self._add_to_favorites)

        # Connect card maximize signals
        self.news_card.clicked.connect(self._show_maximized_card)
        self.long_term_card.clicked.connect(self._show_maximized_card)
        self.day_trade_card.clicked.connect(self._show_maximized_card)

        self.send_button.clicked.connect(self._send_chat_message)

    def _return_home(self):
        self.stacked_widget.setCurrentIndex(0)
        self.btn_home.hide()
        self.update_timer.stop()

    def _add_to_favorites(self):
        if self.current_ticker and self.current_ticker not in self.favorite_tickers:
            self.favorite_tickers.append(self.current_ticker)
            self._load_favorites()

    def _show_maximized_card(self, title, text, color):
        dialog = QDialog(self)
        # Implementation from original code
        pass

    def _show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def _send_chat_message(self):
        message = self.chat_input.text()
        self.chat_box.append(f"User: {message}")
        self.chat_input.clear()

        # Send message to AI and display response
        ai_response = self.ai_client.analyze(message, "financial analyst")
        self.chat_box.append(f"AI: {ai_response['message']['content']}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(r"C:\Users\taylo\OneDrive\Desktop\Code\Axlotto transparent.ico"))
    window = ModernStockApp()
    window.show()
    sys.exit(app.exec())