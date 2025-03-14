# main.py
import sys
import os
import re
import time
import logging
import traceback
import fix_missing_methods
from fix_missing_methods import safe_widget_call

# Set up exception handling to capture all errors
def global_exception_handler(exctype, value, tb):
    """Global exception handler to log unhandled exceptions"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    logging.error(f"Unhandled exception: {error_msg}")
    # Still call the original exception handler
    sys.__excepthook__(exctype, value, tb)

# Install the global exception handler
sys.excepthook = global_exception_handler

# Set up logging to file as well as console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stoxalotl.log"),
        logging.StreamHandler()
    ]
)

# Log startup information
logging.info("Application starting")

from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QSettings, QPropertyAnimation, QEasingCurve, QPoint, QSize
from PySide6.QtGui import QFont, QColor, QPixmap, QIcon, QTextCursor, QAction  # Move QAction to QtGui import
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
    QComboBox,
    QProgressBar,
    QMenu,  # Keep QMenu in QtWidgets
    QCheckBox,
    QSlider,
    QGroupBox
)
import pyqtgraph as pg
import numpy as np
from request_counter import RequestCounter

# Check numpy version
try:
    if (np.__version__ >= '1.24'):
        print("Warning: It's recommended to use numpy<1.24 with pyqtgraph. Consider downgrading.")
except:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Local imports
from config import (COLOR_PALETTES, FONT_FAMILY, FONT_SIZES, FONT_CHOICES, 
                   OLLAMA_MODEL, CHAT_MODEL, NEWS_API_KEY, NEWS_API_URL, UI_CONFIG)
from widgets import KeyMetrics, RecommendationWidget, AnalysisCard, StockChart, StockOverview
from api_client import StockAPI, AIClient, StockAPIError, AIClientError
from helpers import parse_recommendations, analysis_color, remove_think_tags
from widgets import ProfitTarget

# Import our rate limiter system
from rate_limiter import get_rate_limiter_stats, shutdown_all

# Update imports to include the new ticker_utils module
from ticker_utils import validate_ticker, normalize_ticker, find_similar_ticker
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Import this at the top of the file with other imports
import logging
from types import MethodType

# Import the formatter
from ai_formatter import AnalysisFormatter

class ModernStockApp(QMainWindow):
    def __init__(self):
        # Wrap initialization in try-except for better error catching
        try:
            super().__init__()
            
            # Log app configuration
            logging.info("Initializing application...")
            
            # Initialize settings first
            self.settings = QSettings("Stoxalotl", "Preferences")
            
            # Get current theme from settings or use default
            self.current_theme = self.settings.value("Theme", "Dark")
            
            # Rest of initialization
            self.app_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "Axlotto transparent.ico")
            
            # Check if icon file exists
            if not os.path.exists(self.app_icon_path):
                logging.warning(f"Icon file not found at {self.app_icon_path}")
                # Use a default icon or none
                self.app_icon = QIcon()
            else:
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
            self.stock_api = StockAPI(request_counter=self.request_counter, max_requests_per_second=30)
            self.ai_client = AIClient()

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

            # Initialize debounce timer with longer timeout and don't connect it yet
            self.debounce_timer = QTimer(self)
            self.debounce_timer.setSingleShot(True)
            self.debounce_timer.timeout.connect(self._check_analyze_ready)  # Connect to check function instead

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

            # Add stock data cache with last update time tracking
            self.stock_data_cache = {}
            self.last_stock_update = {}
            self.stock_cache_ttl = 30  # Cache data for 30 seconds

            # Add a flag to prevent multiple simultaneous analyses
            self.analysis_in_progress = False

            # Add settings stacked widget
            self.settings_stack = QStackedWidget()
            
            # Create settings pages
            self._create_settings_page()
            self._create_ui_settings_page()

            # Add a persistent dialog for showing maximized cards
            self._create_persistent_dialog()

        except Exception as e:
            # Log any initialization errors
            logging.critical(f"Initialization error: {str(e)}")
            logging.critical(traceback.format_exc())
            # Show error to the user
            QMessageBox.critical(None, "Initialization Error", 
                                 f"An error occurred during application initialization:\n{str(e)}\n\n"
                                 f"Please check the log file for details.")
            # Re-raise to terminate application
            raise

    def _init_update_timer(self):
        self.update_timer = QTimer(self)
        # Change update frequency to 10 seconds instead of 1 second
        self.update_timer.setInterval(10000)
        self.update_timer.timeout.connect(self._update_ui)

    def _setup_styles(self):
        # Apply the selected color palette
        theme = COLOR_PALETTES["Dark"]  # Default theme
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['background']};
                color: {theme['text']};
            }}
            /* Check for any hardcoded colors like #BB that might be incomplete */
        """)

        # Apply the selected font family
        app_font = QFont(FONT_FAMILY, FONT_SIZES["body"])
        QApplication.instance().setFont(app_font)

        # Apply UI configurations
        border_radius = UI_CONFIG["border_radius"]
        padding = UI_CONFIG["padding"]
        button_style = UI_CONFIG["button_style"]
        accent_color = UI_CONFIG["accent_color"]
        font_color = UI_CONFIG["font_color"]
        hover_brightness = UI_CONFIG["hover_brightness"]
        shadow_depth = UI_CONFIG["shadow_depth"]
        transition_duration = UI_CONFIG["transition_duration"]
        
        self.setStyleSheet(self.styleSheet() + f"""
                QPushButton {{
                    background-color: {theme['primary']};
                    color: {font_color};
                    border-radius: {border_radius}px;
                    padding: {padding // 2}px {padding}px;
                    border: 1px solid {theme['border']};
                }}
                QPushButton:hover {{
                    background-color: {accent_color};
                }}
                QPushButton:pressed {{
                    background-color: {theme['secondary']};
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
        header_layout.setContentsMargins(24, 0, 24, 0)  # Added right padding for symmetry
        header_layout.setSpacing(0)  # Remove default spacing

        # Settings button (replacing the text brand button)
        self.brand_button = QPushButton()  # Empty button without text
        self.brand_button.setIcon(self.app_icon)  # Use app icon instead
        self.brand_button.setIconSize(QSize(64, 64))  # Increased from 24x24 to 32x32
        self.brand_button.setFixedSize(40, 40)  # Increased from 32x32 to 40x40
        self.brand_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #333333;
                border-radius: 4px;
            }
        """)
        self.brand_button.setCursor(Qt.PointingHandCursor)
        self.brand_button.clicked.connect(self._show_settings_menu)
        self.brand_button.setToolTip("Settings")
        
        # Add brand button
        header_layout.addWidget(self.brand_button)
        
        # Add stretch to push everything else to the right
        header_layout.addStretch(1)
        
        # Create a container for the home icon and search elements with zero spacing
        control_container = QWidget()
        control_layout = QHBoxLayout(control_container)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(8)  # Small spacing between home icon and search
        
        # Home icon button - replaced text button with icon
        self.btn_home = QPushButton()
        self.btn_home.setFixedSize(32, 32)  # Square button for icon
        
        # Load home icon
        home_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "home.png")
        if os.path.exists(home_icon_path):
            self.btn_home.setIcon(QIcon(home_icon_path))
        else:
            # Fallback if icon not found - use text "🏠" as unicode home symbol
            self.btn_home.setText("🏠")
        
        self.btn_home.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
        """)
        self.btn_home.setToolTip("Return to Home")
        self.btn_home.hide()  # Hidden by default until needed
        self.btn_home.clicked.connect(self._return_home)
        
        # Create search container
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)  # No spacing between search field and button
        
        # Search bar with styling
        self.search = QLineEdit()
        self.search.setPlaceholderText("Enter ticker...")
        self.search.setFixedWidth(150)
        self.search.setFixedHeight(32)
        self.search.setStyleSheet("""
            QLineEdit {
                border: 1px solid #333;
                border-right: none; /* Remove right border to connect with button */
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 0 10px;
                margin: 0px; /* Ensure no margins */
                background: #1a1a1a;
                color: white;
            }
            QLineEdit:focus {
                border-color: #00bcd4;
                border-right: none; /* Keep right border removed even when focused */
            }
        """)
        
        # Analyze button with styling to connect with search bar - update color to match theme
        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setFixedSize(90, 32)
        self.btn_analyze.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PALETTES['Dark']['primary']};
                color: white;
                border: none;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                margin: 0px; /* Ensure no margins */
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background-color: #A370E0;
            }}
            QPushButton:pressed {{
                background-color: {COLOR_PALETTES['Dark']['secondary']};
            }}
        """)
        self.btn_analyze.clicked.connect(self._analyze)
        
        # Add search and analyze button to search layout
        search_layout.addWidget(self.search)
        search_layout.addWidget(self.btn_analyze)
        
        # Add home button and search container to control layout
        control_layout.addWidget(self.btn_home)
        control_layout.addWidget(search_container)
        
        # Add the control container to header layout
        header_layout.addWidget(control_container)
        
        parent_layout.addWidget(header)

    def _on_search_text_changed(self):
        """Handle search text changes with debouncing to limit API calls"""
        # Reset the debounce timer
        if hasattr(self, 'search_debounce_timer'):
            self.search_debounce_timer.stop()
            # Only trigger after 500ms of inactivity
            self.search_debounce_timer.start(500)

    def _check_analyze_ready(self):
        """DISABLED: This function previously triggered search after debounce timer expiration"""
        # We're disabling automatic search - do nothing when timer expires
        pass

    def _debounced_search(self):
        """Debounced function for search suggestions"""
        # Get current search text
        search_text = self.search.text().strip()
        
        # Don't process very short inputs
        if not search_text or len(search_text) < 2:
            return
        
        # Check if this might be a valid ticker and suggest corrections
        try:
            normalized = normalize_ticker(search_text)
            # Only check for invalid tickers - don't validate with API yet
            _, is_valid, suggestion = validate_ticker(normalized)
            if not is_valid and suggestion:
                # Show suggestion in a non-intrusive way (status bar)
                self.statusBar().showMessage(f"Did you mean {suggestion}?", 3000)
        except Exception as e:
            logging.debug(f"Error in search suggestion: {e}")

    def _connect_signals(self):
        """Connect all UI signals with proper error handling"""
        # IMPORTANT: Use safe signal disconnect pattern
        def safe_disconnect(obj, signal_name, slot=None):
            """Safely disconnect a signal with proper error handling"""
            try:
                if hasattr(obj, signal_name):
                    # Get the signal object
                    signal = getattr(obj, signal_name)
                    # Check if the signal object exists and is actually a signal
                    if signal is None:
                        logging.debug(f"Signal {signal_name} is None on {obj}")
                        return
                    # Check if there are any connections
                    if hasattr(signal, 'disconnect'):
                        if slot is None:
                            # Check if we have any connections before trying to disconnect all
                            try:
                                # PySide6-specific way to check if signal is connected
                                if not getattr(signal, 'receivers', []):
                                    return  # No connections to disconnect
                                # Disconnect all connections if no specific slot provided
                                signal.disconnect()
                            except TypeError:
                                # This means there were no connections
                                pass
                        else:
                            # Try to disconnect specific slot
                            try:
                                signal.disconnect(slot)
                            except TypeError:
                                # This means the slot wasn't connected
                                pass
            except (TypeError, RuntimeError) as e:
                # This is normal if the signal was not connected
                logging.debug(f"Signal disconnect information: {e}")
            except Exception as e:
                # Log other errors but don't crash
                logging.warning(f"Unexpected error during signal disconnect: {e}")

        # Completely disconnect ALL existing signals first
        safe_disconnect(self.search, 'returnPressed')
        safe_disconnect(self.btn_analyze, 'clicked')
        safe_disconnect(self.btn_home, 'clicked')
        safe_disconnect(self.send_button, 'clicked')
        safe_disconnect(self.search, 'textChanged')
        safe_disconnect(self.chat_input, 'returnPressed')  # Ensure chat input return is also disconnected

        # Disconnect card signals - make sure we're accessing the signal name correctly
        for card_name in ['strategy_card', 'news_card', 'long_term_card']:  # Removed 'day_trade_card'
            if hasattr(self, card_name):
                card = getattr(self, card_name)
                if hasattr(card, 'maximize_signal'):
                    try:
                        safe_disconnect(card, 'maximize_signal')
                    except Exception as e:
                        logging.debug(f"Error disconnecting maximize_signal from {card_name}: {e}")

        # Now connect signals once with try/except for each connection to prevent duplicates
        try:
            self.search.returnPressed.connect(self._analyze)
            logging.debug("Connected search.returnPressed to _analyze")
        except Exception as e:
            logging.error(f"Failed to connect search.returnPressed: {e}")

        try:
            self.btn_analyze.clicked.connect(self._analyze)
            logging.debug("Connected btn_analyze.clicked to _analyze")
        except Exception as e:
            logging.error(f"Failed to connect btn_analyze.clicked: {e}")

        try:
            self.btn_home.clicked.connect(self._return_home)
            logging.debug("Connected btn_home.clicked to _return_home")
        except Exception as e:
            logging.error(f"Failed to connect btn_home.clicked: {e}")

        # Connect card signals with existence checks and better error handling
        for card_name in ['strategy_card', 'news_card', 'long_term_card']:  # Removed 'day_trade_card'
            if hasattr(self, card_name):
                card = getattr(self, card_name)
                if hasattr(card, 'maximize_signal'):
                    try:
                        logging.info(f"Connecting maximize_signal for {card_name}")
                        card.maximize_signal.connect(self._show_maximized_card)
                    except Exception as e:
                        logging.error(f"Failed to connect maximize_signal for {card_name}: {e}")

        # Connect chat message input signals
        try:
            self.send_button.clicked.connect(self._send_chat_message)
            logging.debug("Connected send_button.clicked to _send_chat_message")
        except Exception as e:
            logging.error(f"Failed to connect send_button.clicked: {e}")

        try:
            self.chat_input.returnPressed.connect(self._send_chat_message)
            logging.debug("Connected chat_input.returnPressed to _send_chat_message")
        except Exception as e:
            logging.error(f"Failed to connect chat_input.returnPressed: {e}")

        try:
            self.search.textChanged.connect(self._on_search_text_changed)
            logging.debug("Connected search.textChanged to _on_search_text_changed")
        except Exception as e:
            logging.error(f"Failed to connect search.textChanged: {e}")

        # Set up debounce timer if not already
        if not hasattr(self, 'search_debounce_timer'):
            self.search_debounce_timer = QTimer(self)
            self.search_debounce_timer.setSingleShot(True)
            self.search_debounce_timer.timeout.connect(self._debounced_search)

    def _create_home_page(self):
        home_page = QWidget()
        layout = QVBoxLayout(home_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Market News Section
        self.news_label = QLabel("Market News")
        self.news_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        layout.addWidget(self.news_label)
        self.news_feed = QTextEdit()
        self.news_feed.setReadOnly(True)
        self.news_feed.setMaximumHeight(200)
        layout.addWidget(self.news_feed)

        # Recently Viewed Section - Redesigned without grey background
        self.recent_label = QLabel("Recently Viewed")
        self.recent_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        self.recent_label.setStyleSheet("margin-top: 10px;")  # Add some margin above
        layout.addWidget(self.recent_label)

        # Create a simple container without scroll area
        recent_container = QWidget()
        recent_container.setMaximumHeight(100)  # Reduced height from 150 to 100

        # Use a flow layout (horizontal with wrapping) for the cards
        self.recent_layout = QHBoxLayout(recent_container)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)  # No margins
        self.recent_layout.setSpacing(10)  # Space between cards
        self.recent_layout.setAlignment(Qt.AlignLeft)  # Align left

        # Add the container directly to main layout
        layout.addWidget(recent_container)

        # Store reference to container for updates
        self.recent_content = recent_container

        # Market Analysis Section
        self.market_analysis_label = QLabel("Market Analysis")
        self.market_analysis_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        layout.addWidget(self.market_analysis_label)
        self.market_analysis = QTextEdit()
        self.market_analysis.setReadOnly(True)
        layout.addWidget(self.market_analysis)

        # Initial data load
        self._load_news_feed()
        self._load_recent_tickers()
        self._load_market_analysis()

        self.stacked_widget.addWidget(home_page)

    def _load_market_data(self):
        try:
            # Fetch data for major indices (S&P 500, NASDAQ, Dow Jones)
            indices = ["^GSPC", "^IXIC", "^DJI"]  # Ticker symbols for S&P 500, NASDAQ, Dow Jones
            for index in indices:
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
            # Fetch and process news
            all_news = self.stock_api.get_market_news()  # Assuming this method exists
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
        self.profit_target = ProfitTarget()  # Add profit target widget

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
        for widget in [self.overview, self.metrics, self.ai_recommendation, self.profit_target, chat_container]:
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
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Create cards with explicit connections to maximize signal
        self.news_card = AnalysisCard("Latest News")
        self.news_card.maximize_signal.connect(self._show_maximized_card)

        self.long_term_card = AnalysisCard("Buy/Sell Analysis")
        self.long_term_card.maximize_signal.connect(self._show_maximized_card)

        # Removed day_trade_card

        self.strategy_card = AnalysisCard("Investment Strategy")
        self.strategy_card.maximize_signal.connect(self._show_maximized_card)

        # Add cursor to indicate clickability and add to layout
        for card in [self.news_card, self.long_term_card, self.strategy_card]:  # Removed day_trade_card from list
            card.setCursor(Qt.PointingHandCursor)  # Show hand cursor to indicate clickable
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            layout.addWidget(card)

        # Set initial content with HTML formatting
        self.news_card.content.setHtml("<i>Search for a stock to view news...</i>")
        self.long_term_card.content.setHtml("<i>Search for a stock to view analysis...</i>")
        # Removed day_trade_card HTML initialization
        self.strategy_card.content.setHtml("<i>Search for a stock to view analysis...</i>")

        # Add stretch to push cards to the top
        layout.addStretch()

        # Complete the scroll area setup
        scroll.setWidget(content)

        # Create a layout for the tab itself
        tab_layout = QVBoxLayout(analysis_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        # Add the tab to the tabwidget
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

        # Create chart using our custom class from stock_chart.py
        # which includes the inverted drag behavior
        from stock_chart import StockChart
        self.chart = StockChart()
        self._fix_chart_orientation()  # Fix chart orientation after creation

        # Add to layout
        layout.addLayout(controls)
        layout.addWidget(self.chart)

        self.tabs.addTab(chart_page, "Charts")

    def _fix_chart_orientation(self):
        """Fix chart orientation to ensure proper mouse drag direction"""
        try:
            # Access the chart's ViewBox(es) and fix orientation
            if hasattr(self, 'chart') and self.chart is not None:
                # Most charts in pyqtgraph have a plotItem with a viewBox
                if hasattr(self.chart, 'plotItem') and self.chart.plotItem is not None:
                    # Set invertX to False to ensure proper drag direction
                    self.chart.plotItem.getViewBox().invertX(False)
                    logging.info("Fixed chart X-axis orientation")
                
                # Some charts might have multiple plots (e.g. for Both chart type)
                if hasattr(self.chart, 'plots') and isinstance(self.chart.plots, dict):
                    for plot_name, plot_item in self.chart.plots.items():
                        if hasattr(plot_item, 'getViewBox'):
                            plot_item.getViewBox().invertX(False)
                            logging.info(f"Fixed orientation for plot: {plot_name}")
        except Exception as e:
            logging.error(f"Error fixing chart orientation: {e}")

    def _update_chart(self):
        if (self.current_ticker):
            try:
                # Make sure we have valid data
                logging.info(f"Updating chart for {self.current_ticker}")

                # Try to safe guard against errors
                try:
                    time_frame = self.time_frame.currentText()
                    chart_type = self.chart_type.currentText()
                except AttributeError:
                    # If the combo boxes are not available, use defaults
                    time_frame = "3M"
                    chart_type = "Both"

                # Log important info before calling chart update
                logging.info(f"Chart update with ticker={self.current_ticker}, time_frame={time_frame}, type={chart_type}")

                # Use a try-except block to catch specific errors
                try:
                    # Update the chart in one place only
                    self.chart.update_chart(
                        self.current_ticker,
                        time_frame,
                        chart_type,
                    )
                    logging.info("Chart update method called successfully")
                    
                    # Fix chart orientation after update
                    self._fix_chart_orientation()
                except Exception as chart_error:
                    logging.error(f"Chart update_chart method failed: {chart_error}")
                    # Try a fallback approach
                    self.chart.clear()
                    self.chart.addItem(pg.TextItem(
                        text=f"Error rendering chart for {self.current_ticker}: {str(chart_error)}",
                        color=(255, 0, 0)
                    ))
            except Exception as e:
                logging.error(f"Error in _update_chart outer block: {e}")
                # Don't show error message here as it might cause recursive issues

    def _create_stock_card(self, ticker, current_price, prev_close, container_layout):
        """Create a stock card for recently viewed stocks"""
        try:
            # Create stock card with more minimalist design
            card = QFrame()
            card.setFrameStyle(QFrame.NoFrame)  # No frame border
            card.setLineWidth(0)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 8, 8, 8)  # Smaller internal padding

            # Ticker label
            ticker_label = QLabel(ticker)
            ticker_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
            ticker_label.setAlignment(Qt.AlignCenter)

            # Price label
            price_label = QLabel(f"${current_price:.2f}")
            price_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
            price_label.setAlignment(Qt.AlignCenter)

            # Set color based on trend (more subtle background)
            if current_price > prev_close:
                card.setStyleSheet("background-color: rgba(30, 51, 32, 0.7); color: white; border-radius: 6px;")
            elif current_price < prev_close:
                card.setStyleSheet("background-color: rgba(61, 31, 31, 0.7); color: white; border-radius: 6px;")
            else:
                card.setStyleSheet("background-color: rgba(45, 45, 45, 0.7); color: white; border-radius: 6px;")

            card_layout.addWidget(ticker_label)
            card_layout.addWidget(price_label)

            # Set fixed size for the card - smaller than before
            card.setFixedSize(100, 70)
            container_layout.addWidget(card)
        except Exception as e:
            print(f"Error creating stock card for {ticker}: {e}")

    def _load_recent_tickers(self):
        # Clear existing widgets
        for i in reversed(range(self.recent_layout.count())):
            widget = self.recent_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        if not self.recent_tickers:
            # Add a placeholder message if no recent tickers
            placeholder = QLabel("No recently viewed stocks. Search for a ticker to begin.")
            placeholder.setStyleSheet("color: #757575; font-style: italic;")
            self.recent_layout.addWidget(placeholder)
            return

        # Add recent ticker cards
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

        # Add stretch to push cards to the left
        self.recent_layout.addStretch()

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
        # Prevent multiple simultaneous analyses
        if self.analysis_in_progress:
            logging.info("Analysis already in progress, ignoring duplicate request")
            return

        raw_ticker = self.search.text().strip().upper()
        if not raw_ticker:
            self._show_error("Please enter a stock ticker")
            return

        # Add ticker validation and normalization
        ticker, is_valid, suggestion = validate_ticker(raw_ticker)

        # Handle invalid ticker with suggestion if available
        if not is_valid:
            suggestion_msg = f" Did you mean {suggestion}?" if suggestion else ""
            self._show_error(f"Invalid ticker symbol: {raw_ticker}.{suggestion_msg}")
            return

        # Set the flag to prevent duplicate processing
        self.analysis_in_progress = True

        # Show loading indicator
        self.statusBar().showMessage(f"Loading data and generating analysis for {ticker}...")
        QApplication.processEvents()

        try:
            # Update current_ticker ONLY after validation
            self.current_ticker = ticker

            # Update recent tickers list with validated ticker
            if (ticker in self.recent_tickers):
                self.recent_tickers.remove(ticker)
            self.recent_tickers.insert(0, ticker)
            self.recent_tickers = self.recent_tickers[:self.max_recent_tickers]
            self._load_recent_tickers()

            # Clear cache for previous searches that aren't the current ticker
            # This ensures we don't reuse cached data from different symbols
            self._clear_irrelevant_cache(ticker)

            # Get stock data first and store in cache with properly namespaced key
            logging.info(f"Requesting fresh data for ticker: {ticker}")
            stock = self.stock_api.get_stock(ticker, use_cache=False)  # Force fresh data for new searches

            # Store in cache with proper cache key that includes the ticker
            cache_key = f"stock_data_{ticker}"
            self.stock_data_cache[cache_key] = stock
            self.last_stock_update[cache_key] = time.time()

            # Switch to analysis page
            self.stacked_widget.setCurrentIndex(1)
            self.btn_home.show()
            self.update_timer.start()

            # Show loading placeholders
            self.news_card.content.setPlainText("Loading news...")
            self.long_term_card.content.setPlainText("Loading analysis...")
            self.strategy_card.content.setPlainText("Loading analysis...")

            # Update UI with stock data
            self._update_ui()

            # Load news in background (doesn't use LLM)
            QApplication.processEvents()
            self._update_news(ticker)

            # Update chart
            QApplication.processEvents()
            self._update_chart()

            # Generate the AI analysis
            try:
                self._generate_combined_analysis(stock)
            except Exception as e:
                logging.error(f"Analysis generation failed: {e}")
                self.long_term_card.content.setPlainText(
                    f"Error generating analysis: {e}\n\nPlease try again later or use the chat feature to ask specific questions."
                )

            self.statusBar().showMessage(f"Analysis of {ticker} complete", 3000)
        except StockAPIError as e:
            logging.error(f"Error analyzing stock {ticker}: {e}")
            self.statusBar().showMessage("Analysis failed", 3000)
            self._show_error(str(e))
        except Exception as e:
            logging.error(f"Unexpected error during analysis of {ticker}: {e}")
            self.statusBar().showMessage("Analysis failed", 3000)
            self._show_error(f"An unexpected error occurred: {str(e)}")
        finally:
            # Always reset the flag when done
            self.analysis_in_progress = False

    def _clear_irrelevant_cache(self, current_ticker):
        """Clear cache entries that aren't related to the current ticker to avoid using wrong data"""
        # Define patterns for ticker-specific cache keys
        patterns = [
            f"stock_data_",  # Stock data cache
            f"chart_",       # Chart data cache
            f"news_"         # News cache
        ]

        # Collect keys to delete (to avoid modifying dict during iteration)
        keys_to_delete = []

        # Check stock data cache
        for cache_key in self.stock_data_cache.keys():
            # Only keep cache entries related to current ticker
            if not any(p + current_ticker in cache_key for p in patterns):
                keys_to_delete.append(cache_key)

        # Delete keys
        for key in keys_to_delete:
            logging.info(f"Clearing cache entry: {key}")
            if key in self.stock_data_cache:
                del self.stock_data_cache[key]
            if key in self.last_stock_update:
                del self.last_stock_update[key]

    def _update_ui(self):
        if not self.current_ticker:
            return

        try:
            # Show loading indicators
            if hasattr(self, 'overview') and hasattr(self.overview, 'show_loading'):
                safe_widget_call(self.overview, 'show_loading')

            current_time = time.time()
            refresh_needed = False

            # Use proper cache key that includes ticker
            cache_key = f"stock_data_{self.current_ticker}"

            # Check if stock data needs to be refreshed
            if (cache_key not in self.stock_data_cache or
                cache_key not in self.last_stock_update or
                (current_time - self.last_stock_update[cache_key]) > self.stock_cache_ttl):
                # Only make API call when cache is expired
                logging.info(f"Cache expired or not found for {self.current_ticker}, refreshing stock data")
                stock_data = self.stock_api.get_stock(self.current_ticker)
                self.stock_data_cache[cache_key] = stock_data
                self.last_stock_update[cache_key] = current_time
                refresh_needed = True
            else:
                # Use cached data
                stock_data = self.stock_data_cache[cache_key]
                logging.debug(f"Using cached stock data for {self.current_ticker} from key: {cache_key}")

            # Only update UI elements if data was refreshed or this is the first update cycle
            if refresh_needed or not hasattr(self, '_ui_updated'):
                current_price = stock_data['c']
                prev_close = stock_data['pc']

                # Calculate price change
                change_amount = current_price - prev_close
                change_percent = (change_amount / prev_close) * 100 if prev_close != 0 else 0
                change_text = f"{change_amount:+.2f} ({change_percent:+.2f}%)"

                # Update overview with all information including favorite status
                safe_widget_call(self.overview, 'update_overview', self.current_ticker, current_price, change_text)

                # Update metrics - with additional logging
                logging.info(f"Getting stock metrics for {self.current_ticker}...")
                metrics = self._get_stock_metrics(self.current_ticker)  # Pass ticker directly, not stock data

                # Log metrics data to help debugging
                logging.info(f"Got metrics data: {metrics}")

                # Update the metrics widget with the data
                if metrics and hasattr(self, 'metrics'):
                    logging.info("Updating metrics widget with data")
                    safe_widget_call(self.metrics, 'update_metrics', metrics)
                else:
                    logging.error("Failed to update metrics - no data or widget")

                # Update profit target
                safe_widget_call(self.profit_target, 'update_profit_target', current_price)

                # Mark that UI has been updated at least once
                self._ui_updated = True
        except StockAPIError as e:
            logging.error(f"Error updating UI for {self.current_ticker}: {e}")
            self._show_error(str(e))
        except Exception as e:
            logging.error(f"Unexpected error during UI update for {self.current_ticker}: {e}")
            self._show_error(f"An unexpected error occurred: {str(e)}")

    def _format_news_html(self, news_items):
        """Format news items as HTML for better presentation"""
        if not news_items:
            return "<i>No news available.</i>"

        html = "<div style='font-family: Segoe UI, sans-serif;'>"

        for article in news_items:
            # Extract article data
            title = article.get('title', 'No Title')
            description = article.get('description', 'No description available.')
            source = article.get('source', {}).get('name', 'Unknown Source')
            date = article.get('formatted_date', article.get('publishedAt', ''))[:10]
            url = article.get('url', '#')

            # Format as a nice HTML card
            html += f"""
            <div style='margin-bottom: 15px; padding: 10px; border-left: 3px solid #00bcd4; background-color: #1a1a1a;'>
                <h3 style='margin-top: 0; margin-bottom: 5px; color: #e0e0e0;'>{title}</h3>
                <div style='font-size: 12px; color: #757575; margin-bottom: 8px;'>
                    {source} • {date}
                </div>
                <p style='margin-bottom: 5px; color: #bdbdbd;'>{description}</p>
            </div>
            """

        html += "</div>"
        return html

    def _update_news(self, ticker):
        try:
            # Show loading state
            self.news_card.show_loading()
            QApplication.processEvents()

            # Get news with proper error handling
            news = self.stock_api.get_news(ticker)
            QApplication.processEvents()

            # Format news as HTML and update the card
            html_content = self._format_news_html(news)
            self.news_card.content.setHtml(html_content)
        except Exception as e:
            logging.error(f"Error updating news: {e}")
            self.news_card.content.setHtml(
                f"<div style='color: #F44336;'>Error loading news: {str(e)}</div>"
            )

    def _generate_combined_analysis(self, stock):
        try:
            # Show loading state
            self.long_term_card.content.setHtml("<i>Loading analysis...</i>")
            self.strategy_card.content.setHtml("<i>Loading analysis...</i>")
            QApplication.processEvents()

            # Get financial metrics for the ticker
            financial_metrics = self._get_stock_metrics(self.current_ticker)
            
            # Create enhanced prompt with clear sections for structured output
            combined_prompt = f"""
            Analyze {self.current_ticker} stock and provide a comprehensive investment analysis with the following sections:
            
            STOCK OVERVIEW:
            Provide a brief overview of {self.current_ticker} including what they do, market position, and current price trend.
            Current stock price: ${stock['c']:.2f}
            
            FINANCIAL SITUATION:
            Analyze key financial metrics, revenue trends, profitability, and financial health.
            
            NEWS IMPACT:
            Summarize how recent news and events affect the stock's outlook.
            
            TRAJECTORY ANALYSIS:
            Evaluate the stock's recent performance trend and technical indicators.
            
            PREDICTION:
            Forecast end of week price: $XX.XX (with confidence level)
            Forecast end of month price: $XX.XX (with confidence level)
            Forecast end of year price: $XX.XX (with confidence level)
            
            For each prediction, provide a specific price target and confidence level percentage.
            Base predictions on financial data, market trends, and recent news.
            """

            # Generate analysis
            response = self.ai_client.analyze(
                combined_prompt, 
                "financial analyst", 
                model=OLLAMA_MODEL,  
                retries=3, 
                backoff_factor=2.0
            )
            content = response['message']['content']
            cleaned_content = remove_think_tags(content)

            # Use the enhanced formatter for the long-term analysis card
            AnalysisFormatter.apply_enhanced_formatting(
                self.long_term_card.content, 
                cleaned_content, 
                self.current_ticker,
                financial_metrics
            )
            
            # Extract investment strategy section for the strategy card
            strategy_match = re.search(r'(?:PREDICTION|FORECAST|OUTLOOK|TARGET):(.*?)(?=\n\n|\Z)', 
                                     cleaned_content, re.IGNORECASE | re.DOTALL)
            if strategy_match:
                strategy_text = strategy_match.group(1).strip()
            else:
                # If no prediction section found, use the latter half of the content
                sections = cleaned_content.split('\n\n')
                half = len(sections) // 2
                strategy_text = "\n\n".join(sections[half:])
            
            # Apply the strategy-focused formatting to the strategy card
            AnalysisFormatter.apply_formatting_to_textedit(
                self.strategy_card.content, 
                strategy_text, 
                self.current_ticker
            )

            # Update recommendations based on the analysis
            self._update_recommendations(cleaned_content)
            
        except AIClientError as e:
            logging.error(f"Error generating combined analysis: {e}")
            self._show_error(str(e))
        except Exception as e:
            logging.error(f"Unexpected error during combined analysis generation: {e}")
            self._show_error(f"An unexpected error occurred: {str(e)}")

    def _update_recommendations(self, analysis_text):
        recs = parse_recommendations(analysis_text)
        self.ai_recommendation.update_recommendations(recs)

    def _return_home(self):
        self.stacked_widget.setCurrentIndex(0)
        self.btn_home.hide()
        self.update_timer.stop()

    def _create_persistent_dialog(self):
        """Create a persistent dialog that we'll reuse rather than create/destroy repeatedly"""
        self.persistent_dialog = QDialog(self)
        self.persistent_dialog.setWindowIcon(self.app_icon)
        self.persistent_dialog.setMinimumSize(600, 400)
        
        # Setup dialog layout
        layout = QVBoxLayout(self.persistent_dialog)
        
        # Create content area
        self.dialog_content = QTextEdit()
        self.dialog_content.setReadOnly(True)
        layout.addWidget(self.dialog_content)
        
        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self._handle_dialog_close)
        layout.addWidget(button_box)
        
        # Don't show initially
        self.persistent_dialog.finished.connect(self._handle_dialog_close)
        
        # Flag to track dialog state
        self._dialog_active = False

    def _handle_dialog_close(self):
        """Handle dialog close events centrally"""
        logging.info("Dialog close handler called")
        self._dialog_active = False
        self.persistent_dialog.hide()  # Hide instead of destroying

    def _show_maximized_card(self, card_data):
        """Show a maximized view of the card content using the persistent dialog"""
        # If already active, just exit
        if self._dialog_active:
            logging.info("Dialog already active, ignoring request")
            return
        
        # Set the flag to prevent multiple dialogs
        self._dialog_active = True
        
        try:
            # Update the persistent dialog with new content
            self.persistent_dialog.setWindowTitle(card_data.get('title', 'Analysis'))
            
            # Update content based on format
            data_content = card_data.get('content', '')
            if '<' in data_content and '>' in data_content:
                self.dialog_content.setHtml(data_content)
            else:
                self.dialog_content.setPlainText(data_content)
            
            # Show the dialog
            logging.info(f"Showing dialog with title: {card_data.get('title', 'Analysis')}")
            self.persistent_dialog.show()
        except Exception as e:
            logging.error(f"Error showing maximized card: {e}")
            self._dialog_active = False

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

        user_message = self.chat_input.text()
        self.chat_history.append("\n<br><div style='margin: 10px 0;'><b>You:</b> " + user_message + "</div>")
        self.chat_input.clear()
        self.chat_history.append(
            """<div style='background-color: #333333; margin: 10px 0; padding: 10px; border-radius: 5px;'>
            <b>AI Assistant:</b><br><br>Thinking...</div><br>
            """
        )
        QApplication.processEvents()  # Update UI immediately

        try:
            context = self._create_chat_context()
            prompt = f"""
            Context about {self.current_ticker}:
            {context}
            User Question: {user_message}
            Please provide a helpful answer using the context provided.
            Format your response with clear paragraphs and bullet points where appropriate.
            """

            response = self.ai_client.analyze(
                prompt, 
                "financial advisor", 
                model=OLLAMA_MODEL,  
                retries=3, 
                backoff_factor=2.0
            )
            ai_response = response['message']['content']
            cleaned_response = remove_think_tags(ai_response)
            formatted_response = cleaned_response.replace("\n", "<br>")  # Convert newlines to HTML breaks
            formatted_response = formatted_response.replace("• ", "<br>• ")  # Add spacing before bullet points
            formatted_response = formatted_response.replace("- ", "<br>• ")  # Convert dashes to bullet points

            cursor = self.chat_history.textCursor()
            cursor.movePosition(QTextCursor.End)
            last_block_pos = cursor.position()
            cursor.setPosition(last_block_pos, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.chat_history.append(
                f"""<div style='background-color: #1e1e1e; margin: 10px 0; padding: 10px; border-radius: 5px;'>
                <b>AI Assistant:</b><br><br>{formatted_response}
                </div><br>
                """
            )
        except Exception as e:
            cursor = self.chat_history.textCursor()
            cursor.movePosition(QTextCursor.End)
            last_block_pos = cursor.position()
            cursor.setPosition(last_block_pos, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.chat_history.append(
                """<div style='background-color: #3d1f1f; margin: 10px 0; padding: 10px; border-radius: 5px;'>
                <b>AI:</b> Sorry, I encountered an error: """ + str(e) + """
                </div><br>
                """
            )

        self.chat_history.verticalScrollBar().setValue(self.chat_history.verticalScrollBar().maximum())

    def _create_chat_context(self):
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

            if hasattr(self, 'long_term_card') and self.long_term_card.content.toPlainText():
                context_parts.append("\nRecent Analysis:")
                context_parts.append(self.long_term_card.content.toPlainText())

            if hasattr(self, 'strategy_card') and self.strategy_card.content.toPlainText():
                context_parts.append("\nInvestment Strategy:")
                context_parts.append(self.strategy_card.content.toPlainText())

            return "\n".join(context_parts)
        except Exception as e:
            return f"Error retrieving context: {str(e)}"

    def _setup_status_bar(self):
        self.statusBar().showMessage('')

        # Rate limit indicators with traffic light colors
        self.finnhub_status = QLabel("Finnhub: Ready")
        self.news_api_status = QLabel("NewsAPI: Ready")
        self.ollama_status = QLabel("Ollama: Ready")
        self.ollama_status = QLabel("Ollama: Ready")

        for label in [self.finnhub_status, self.news_api_status, self.ollama_status]:
            label.setStyleSheet("""
                QLabel {
                    background-color: #2d2d2d; 
                    color: #00C851;  /* Green by default */
                    padding: 2px 5px;
                    margin-right: 5px;        
                    border-radius: 3px;       
                }
            """)

        self.api_requests_label = QLabel("Total: 0")
        self.api_requests_label.setStyleSheet("color: #00bcd4; font-weight: bold; padding: 5px;")

        self.statusBar().addPermanentWidget(self.finnhub_status)
        self.statusBar().addPermanentWidget(self.news_api_status)
        self.statusBar().addPermanentWidget(self.ollama_status)
        self.statusBar().addPermanentWidget(self.api_requests_label)

        self.rate_limit_timer = QTimer(self)
        self.rate_limit_timer.timeout.connect(self._update_rate_limit_status)
        self.rate_limit_timer.start(2000)  # Update every 2 seconds

    def _update_rate_limit_status(self):
        """Update the status indicators for rate limiting"""
        stats = get_rate_limiter_stats()

        # Update Finnhub status
        finnhub = stats["finnhub"]
        self._update_status_indicator(
            self.finnhub_status, 
            "Finnhub", 
            finnhub["waiters"],
            finnhub["requests_limited"],
            finnhub["current_tokens"],
        )

        # Update News API status
        news_api = stats["news_api"]
        self._update_status_indicator(
            self.news_api_status, 
            "NewsAPI", 
            news_api["waiters"],
            news_api["requests_limited"],
            news_api["current_tokens"]        
        )

        # Update Ollama status
        ollama = stats["ollama"]
        self._update_status_indicator(
            self.ollama_status, 
            "Ollama", 
            ollama["waiters"],
            ollama["requests_limited"],
            ollama["current_tokens"],
        )

        # Update total requests
        total_requests = sum(s["requests_made"] for s in stats.values())
        self.api_requests_label.setText(f"Total: {total_requests}")

    def _update_status_indicator(self, label, name, waiters, limited, tokens):
        """Update a status label based on rate limit stats"""
        if waiters > 0:
            # Red if requests are waiting
            label.setText(f"{name}: Waiting ({waiters})")
            label.setStyleSheet("QLabel { background-color: #2d2d2d; color: #FF4444; padding: 2px 5px; margin-right: 5px; border-radius: 3px; }")
        elif limited > 0 and tokens < 1.0:
            # Yellow if limited recently and low on tokens
            label.setText(f"{name}: Limited")
            label.setStyleSheet("QLabel { background-color: #2d2d2d; color: #FFBB33; padding: 2px 5px; margin-right: 5px; border-radius: 3px; }")
        else:
            # Green if all good
            label.setText(f"{name}: Ready")
            label.setStyleSheet("QLabel { background-color: #2d2d2d; color: #00C851; padding: 2px 5px; margin-right: 5px; border-radius: 3px; }")

    def closeEvent(self, event):
        """Clean up resources when closing the application"""
        # Disconnect signals to avoid referencing deleted objects
        if hasattr(self, 'debounce_timer'):
            try:
                self.debounce_timer.timeout.disconnect()
            except (TypeError, RuntimeError):
                pass  # Already disconnected or invalid
            self.debounce_timer.deleteLater()

        # Stop all timers first - important to do this before deleting widgets
        timers = ['update_timer', 'rate_limit_timer', 'request_timer']
        for timer_name in timers:
            if hasattr(self, timer_name):
                timer = getattr(self, timer_name)
                if timer:
                    timer.stop()

        # Clear reference to widgets that might be accessed during shutdown
        # Store widget names to safely delete
        widgets_to_cleanup = [
            'label_status', 'overview', 'metrics', 'ai_recommendation', 
            'profit_target', 'news_card', 'long_term_card', 'strategy_card', 
            'chat_history', 'chart'
        ]
        for widget_name in widgets_to_cleanup:
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                if widget is not None:
                    try:
                        # Set the attribute to None first to avoid further references
                        setattr(self, widget_name, None)
                    except:
                        pass

        # Shut down all request queues
        try:
            shutdown_all()
        except Exception as e:
            logging.error(f"Error shutting down API queues: {e}")

        event.accept()

    def _load_news_feed(self):
        """Fetch general market news for the home page"""
        try:
            self.news_feed.setPlainText("Loading market news...")
            QApplication.processEvents()  # Update UI immediately

            # Try to get market news (general financial news)
            try:
                news = self.stock_api.get_news("market", days_back=2, num_articles=5)
                news_text = ""

                # Process each news article
                for i, article in enumerate(news[:5]):  # Limit to 5 articles
                    try:
                        title = article.get('title', 'No Title')
                        description = article.get('description', 'No Description')
                        source = article.get('source', {}).get('name', 'Unknown Source')
                        date = article.get('publishedAt', '')[:10]  # Just get the date part

                        # Format the article
                        news_text += f"[{date}] {title}\n"
                        news_text += f"Source: {source}\n"
                        news_text += f"{description}\n\n"
                    except Exception as e:
                        logging.warning(f"Error processing article {i}: {e}")
                        news_text += f"Error processing article {i}: {str(e)}\n\n"

                # Set the compiled news text
                if news_text:
                    self.news_feed.setPlainText(news_text)
                else:
                    self.news_feed.setPlainText("No market news found. Try searching for a specific stock.")
            except Exception as e:
                # Try to fall back to dummy market news
                logging.error(f"Error loading market news: {e}")
                # Fallback news
                fallback_news = [
                    {
                        "title": "Market Overview",
                        "description": "Markets remain volatile amid economic uncertainty. Investors are closely monitoring central bank decisions and corporate earnings reports.",
                        "source": {"name": "Financial Daily"},
                        "publishedAt": datetime.now().strftime("%Y-%m-%d")
                    },
                    {
                        "title": "Tech Stocks Lead Market Rally",
                        "description": "Technology sector continues to show strength as investors favor growth stocks in the current environment.",
                        "source": {"name": "Market Insights"},
                        "publishedAt": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                    }
                ]

                # Format fallback news
                news_text = ""
                for article in fallback_news:
                    title = article.get('title', '')
                    description = article.get('description', '')
                    source = article.get('source', {}).get('name', '')
                    date = article.get('publishedAt', '')[:10]

                    news_text += f"[{date}] {title}\n"
                    news_text += f"Source: {source}\n"
                    news_text += f"{description}\n\n"

                self.news_feed.setPlainText(news_text)
        except Exception as e:
            logging.error(f"Error in news feed function: {e}")
            self.news_feed.setPlainText(f"Unable to load news: {str(e)}")

    def _get_stock_metrics(self, data_or_ticker):
        """Get financial metrics for a stock
        Args:
            data_or_ticker: Either a stock data dictionary or ticker symbol string
        Returns:
            Dictionary containing financial metrics data
        """
        try:
            # Check if we were passed stock data or a ticker string
            if isinstance(data_or_ticker, dict):
                # Extract ticker from cached data
                # Note: Finnhub doesn't include ticker in quote response
                # so we need to use our current_ticker
                ticker = self.current_ticker
            else:
                # Use the ticker string directly
                ticker = data_or_ticker

            logging.info(f"Getting financial metrics for {ticker}")

            if not hasattr(self, 'stock_api') or self.stock_api is None:
                logging.error("Stock API not initialized")
                return None

            # Make the API call to get metrics
            metrics = self.stock_api.get_financial_metrics(ticker)

            # Log successful retrieval
            if metrics and isinstance(metrics, dict) and 'metric' in metrics:
                logging.info(f"Successfully retrieved metrics for {ticker}")
            else:
                logging.warning(f"Retrieved empty or invalid metrics for {ticker}")

            return metrics
        except Exception as e:
            logging.error(f"Error in _get_stock_metrics: {e}")
            return {
                "metric": {
                    "peNormalizedAnnual": None,
                    "peTTM": None,
                    "pbAnnual": None,
                    "psTTM": None,
                    "dividendYieldIndicatedAnnual": None,
                    "52WeekHigh": None,
                    "52WeekLow": None,
                }
            }

    def _show_settings_menu(self):
        """Show dropdown menu when Stoxalotl title is clicked"""
        # Create menu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #212121;
                color: white;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
            }
            QMenu::item:selected {
                background-color: #BB86FC;
                color: black;
            }
        """)

        # Add menu items
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._navigate_to_settings)
        menu.addAction(settings_action)
        menu.addSeparator()
        about_action = QAction("About", self)
        menu.addAction(about_action)

        # Show menu under the title
        menu.exec(self.brand_button.mapToGlobal(QPoint(0, self.brand_button.height())))

    def _create_settings_page(self):
        """Create the main settings page with category tabs"""
        settings_page = QWidget()
        layout = QVBoxLayout(settings_page)

        # Header with back button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)

        back_button = QPushButton("← Back")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #BB86FC;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                color: #A370E0;
            }
        """)
        back_button.clicked.connect(self._return_from_settings)

        # Title
        title_label = QLabel("Settings")
        title_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))

        header_layout.addWidget(back_button)
        header_layout.addStretch(1)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        layout.addWidget(header_widget)

        # Settings categories
        categories_frame = QFrame()
        categories_frame.setStyleSheet("background-color: #1a1a1a; border-radius: 8px;")
        categories_layout = QVBoxLayout(categories_frame)
        categories_layout.setSpacing(10)

        # Create buttons
        general_btn = QPushButton("General")
        general_btn.setStyleSheet(self._get_settings_button_style())

        account_btn = QPushButton("Account")
        account_btn.setStyleSheet(self._get_settings_button_style())

        privacy_btn = QPushButton("Privacy")
        privacy_btn.setStyleSheet(self._get_settings_button_style())

        ui_btn = QPushButton("UI Settings")
        ui_btn.setStyleSheet(self._get_settings_button_style())
        ui_btn.clicked.connect(self._navigate_to_ui_settings)

        # Add all buttons
        categories_layout.addWidget(general_btn)
        categories_layout.addWidget(account_btn)
        categories_layout.addWidget(privacy_btn)
        categories_layout.addWidget(ui_btn)
        categories_layout.addStretch()

        layout.addWidget(categories_frame)

        # Add page to settings stack
        self.settings_stack.addWidget(settings_page)

    def _create_ui_settings_page(self):
        """Create UI settings page with various options"""
        ui_settings_page = QWidget()
        layout = QVBoxLayout(ui_settings_page)

        # Header with back button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)

        back_button = QPushButton("← Back to Settings")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #BB86FC;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                color: #A370E0;
            }
        """)
        back_button.clicked.connect(self._return_to_settings)

        title_label = QLabel("UI Settings")
        title_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))

        header_layout.addWidget(back_button)
        header_layout.addStretch(1)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        layout.addWidget(header_widget)

        # Create a scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)

        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        theme_layout = QVBoxLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(self.current_theme)
        self.theme_combo.currentTextChanged.connect(self._update_theme)

        theme_layout.addWidget(QLabel("Theme Mode:"))
        theme_layout.addWidget(self.theme_combo)

        scroll_layout.addWidget(theme_group)

        # Font settings
        font_group = QGroupBox("Font")
        font_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        font_layout = QVBoxLayout(font_group)

        # Font size slider
        font_size_layout = QHBoxLayout()
        font_size_label = QLabel("Font Size:")
        self.font_size_slider = QSlider(Qt.Horizontal)
        self.font_size_slider.setMinimum(10)
        self.font_size_slider.setMaximum(18)
        self.font_size_slider.setValue(FONT_SIZES["body"])
        self.font_size_slider.setTickPosition(QSlider.TicksBelow)
        self.font_size_slider.setTickInterval(2)
        self.font_size_value = QLabel(f"{self.font_size_slider.value()}px")

        self.font_size_slider.valueChanged.connect(lambda v: self._update_font_size_label(v))

        font_size_layout.addWidget(font_size_label)
        font_size_layout.addWidget(self.font_size_slider)
        font_size_layout.addWidget(self.font_size_value)

        font_layout.addLayout(font_size_layout)

        # Font family dropdown
        font_family_layout = QHBoxLayout()
        font_family_label = QLabel("Font Family:")
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(list(FONT_CHOICES.keys()))
        current_font = next((name for name, value in FONT_CHOICES.items() 
                            if value == FONT_FAMILY), "Segoe UI")
        self.font_family_combo.setCurrentText(current_font)

        font_family_layout.addWidget(font_family_label)
        font_family_layout.addWidget(self.font_family_combo)

        font_layout.addLayout(font_family_layout)

        # Bold text option
        self.bold_text_checkbox = QCheckBox("Use Bold Text (High Contrast)")
        self.bold_text_checkbox.setChecked(False)
        font_layout.addWidget(self.bold_text_checkbox)

        scroll_layout.addWidget(font_group)

        # Status bar settings
        status_group = QGroupBox("Status Bar")
        status_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        status_layout = QVBoxLayout(status_group)

        self.show_api_status_checkbox = QCheckBox("Show API Status Indicators")
        self.show_api_status_checkbox.setChecked(True)
        self.show_api_status_checkbox.toggled.connect(self._toggle_api_status)

        status_layout.addWidget(self.show_api_status_checkbox)
        scroll_layout.addWidget(status_group)

        # Apply button
        self.apply_ui_settings_btn = QPushButton("Apply Settings")
        self.apply_ui_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #BB86FC;
                color: black;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #A370E0;
            }
        """)
        self.apply_ui_settings_btn.clicked.connect(self._apply_ui_settings)

        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_content)

        layout.addWidget(scroll)
        layout.addWidget(self.apply_ui_settings_btn)

        # Add page to settings stack
        self.settings_stack.addWidget(ui_settings_page)

    def _get_settings_button_style(self):
        """Helper for consistent settings button style"""
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 10px;
                text-align: left;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """

    def _update_font_size_label(self, value):
        """Update font size label when slider changes"""
        self.font_size_value.setText(f"{value}px")

    def _navigate_to_settings(self):
        """Navigate to settings page"""
        # Add settings page to main stacked widget if not already there
        if self.stacked_widget.indexOf(self.settings_stack) == -1:
            self.stacked_widget.addWidget(self.settings_stack)

        # Go to settings page
        self.settings_stack.setCurrentIndex(0)  # Main settings page
        self.stacked_widget.setCurrentWidget(self.settings_stack)
        self.btn_home.show()

    def _navigate_to_ui_settings(self):
        """Navigate to UI settings page"""
        self.settings_stack.setCurrentIndex(1)  # UI settings page

    def _return_to_settings(self):
        """Return to main settings page"""
        self.settings_stack.setCurrentIndex(0)  # Main settings page

    def _return_from_settings(self):
        """Return from settings to previous page"""
        if self.stacked_widget.currentWidget() == self.settings_stack:
            self._return_home()

    def _toggle_api_status(self, checked):
        """Toggle visibility of API status indicators"""
        if hasattr(self, 'finnhub_status'):
            self.finnhub_status.setVisible(checked)
        if hasattr(self, 'news_api_status'):
            self.news_api_status.setVisible(checked)
        if hasattr(self, 'ollama_status'):
            self.ollama_status.setVisible(checked)
        if hasattr(self, 'api_requests_label'):
            self.api_requests_label.setVisible(checked)

    def _update_theme(self, theme_name):
        """Update the application theme"""
        self.current_theme = theme_name
        self.settings.setValue("Theme", theme_name)
        # Theme will be fully applied on next restart, but update color references now

    def _apply_ui_settings(self):
        """Apply UI settings"""
        # Apply font size
        new_font_size = self.font_size_slider.value()
        app_font = QFont(FONT_FAMILY, new_font_size)
        if self.bold_text_checkbox.isChecked():
            app_font.setBold(True)
        QApplication.instance().setFont(app_font)

        # Apply font family
        selected_font = self.font_family_combo.currentText()
        font_family = FONT_CHOICES.get(selected_font, FONT_FAMILY)
        self.settings.setValue("FontFamily", font_family)

        # Save font size to settings
        self.settings.setValue("FontSize", new_font_size)
        self.settings.setValue("BoldText", self.bold_text_checkbox.isChecked())

        # Show confirmation
        self.statusBar().showMessage("UI settings applied", 2000)

        # Note: Some settings like theme will require app restart for full effect
        if self.theme_combo.currentText() != self.current_theme:
            QMessageBox.information(self, "Theme Changed",
                                    "The theme change will take full effect when you restart the application.")