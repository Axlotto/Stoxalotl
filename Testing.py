import sys
import re
import yfinance as yf
import ollama
import requests
from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor, QPixmap, QIcon  # Added QIcon here
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
    QStyle,
    QTabWidget,
    QFrame,
    QScrollArea,
    QDialog,
    QDialogButtonBox,
    QStackedWidget,
    QSizePolicy
)
import pyqtgraph as pg
import time
from tradingview_ta import TA_Handler, Interval
import numpy as np
from pyqtgraph import GraphicsLayoutWidget, BarGraphItem, DateAxisItem, InfiniteLine, TextItem, SignalProxy


OLLAMA_MODEL = "deepseek-r1:1.5b"

# Configuration
NEWS_API_KEY = "c91f9673406647e280aa6faf87ef892a"
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Modern design constants
COLORS = {
    "background": "#1e1e1e",    # Dark grey
    "surface": "#474747",       # Soft grey
    "primary": "#6366F1",       # Indigo
    "secondary": "#1e1e1e",     # Medium slate
    "accent": "#818CF8",        # Light indigo
    "text": "#F8FAFC",          # Off-white
    "text-secondary": "#94A3B8",# Gray-blue
    "positive": "#34D399",      # Mint green
    "negative": "#F87171",      # Coral red
    "border": "#1e1e1e"         # Dark grey

}
# Yellow colour used for mid-range percentages
YELLOW = "#FFEB3B"

FONT_FAMILY = "Segoe UI"
FONT_SIZES = {
    "title": 20,
    "header": 16,
    "body": 13,
    "small": 11
}

# Update StockOverview with better typography
class StockOverview(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("overview")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.ticker = QLabel("")
        self.ticker.setFont(QFont(FONT_FAMILY, 28, QFont.Bold))
        self.ticker.setStyleSheet(f"color: {COLORS['primary']}; margin-bottom: 8px;")

        price_layout = QHBoxLayout()
        self.price = QLabel("")
        self.price.setFont(QFont(FONT_FAMILY, 32, QFont.Bold))
        self.change = QLabel("")
        self.change.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"]))
        price_layout.addWidget(self.price)
        price_layout.addWidget(self.change)
        price_layout.addStretch()

        layout.addWidget(self.ticker)
        layout.addLayout(price_layout)
        layout.addStretch()

# Updated metrics display
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

        # Add new metrics
        for row, (label, value, color) in enumerate(metrics):
            lbl = QLabel(label)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
            lbl.setStyleSheet(f"color: {COLORS['text-secondary']}")

            val = QLabel(value)
            val.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"], QFont.Medium))
            val.setStyleSheet(f"color: {color}")

            self.grid.addWidget(lbl, row, 0)
            self.grid.addWidget(val, row, 1)

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

# Enhanced AnalysisCard
class AnalysisCard(QFrame):
    clicked = Signal(str, str, str)

    def __init__(self, title):
        super().__init__()
        self.setObjectName("analysisCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.header_label = QLabel(title)
        self.header_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        self.header_label.setStyleSheet(f"color: {COLORS['accent']};")

        self.btn_maximize = QPushButton()
        self.btn_maximize.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.btn_maximize.setFlat(True)
        self.btn_maximize.setFixedSize(28, 28)
        self.btn_maximize.clicked.connect(self._on_maximize_clicked)

        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_maximize)

        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
        self.content.setStyleSheet(f"""
            background-color: {COLORS['secondary']};
            border-radius: 8px;
            padding: 16px;
        """)

        layout.addWidget(header)
        layout.addWidget(self.content)

    def _on_maximize_clicked(self):
        self.clicked.emit(self.header_label.text(), self.content.toPlainText(), self.content.textColor().name())

# Basic StockChart implementation using pyqtgraph
class StockChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create graphics layout widget
        self.grid = GraphicsLayoutWidget()
        layout.addWidget(self.grid)
        
        # Add plots
        self.price_plot = self.grid.addPlot(row=0, col=0)
        self.volume_plot = self.grid.addPlot(row=1, col=0)

        # Set row heights using GraphicsLayoutWidget's native methods
        self.grid.ci.layout.setRowPreferredHeight(0, 300)  # Price plot
        self.grid.ci.layout.setRowPreferredHeight(1, 100)  # Volume plot
        self.grid.ci.layout.setSpacing(40)  # Space between plots

        # Configure price plot
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setLabel('left', 'Price', units='$')
        
        # Configure volume plot
        self.volume_plot.showGrid(x=True, y=True, alpha=0.3)
        self.volume_plot.setLabel('left', 'Volume')
        
        # Link X axes
        self.volume_plot.setXLink(self.price_plot)
        
        # Style axes
        for plot in [self.price_plot, self.volume_plot]:
            plot.getAxis('left').setPen(pg.mkPen(COLORS["text"]))
            plot.getAxis('bottom').setPen(pg.mkPen(COLORS["text"]))
            plot.getAxis('bottom').setTextPen(pg.mkPen(COLORS["text"]))
            plot.getAxis('left').setTextPen(pg.mkPen(COLORS["text"]))

        # Add crosshair
        self.crosshair_v = InfiniteLine(angle=90, movable=False, 
                                      pen=pg.mkPen(COLORS["text"], style=Qt.DashLine))
        self.crosshair_h = InfiniteLine(angle=0, movable=False, 
                                      pen=pg.mkPen(COLORS["text"], style=Qt.DashLine))
        self.price_plot.addItem(self.crosshair_v, ignoreBounds=True)
        self.price_plot.addItem(self.crosshair_h, ignoreBounds=True)
        
        # Add tracking label
        self.tracking_text = TextItem(anchor=(0, 1), color=COLORS["text"], 
                                    fill=pg.mkColor(COLORS["surface"]))
        self.price_plot.addItem(self.tracking_text)
        
        # Connect mouse events
        self.proxy = SignalProxy(self.price_plot.scene().sigMouseMoved, 
                               rateLimit=60, slot=self.mouse_moved)

    def mouse_moved(self, evt):
        pos = evt[0]
        if self.price_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.price_plot.vb.mapSceneToView(pos)
            self.crosshair_v.setPos(mouse_point.x())
            self.crosshair_h.setPos(mouse_point.y())
            
            # Convert timestamp to date
            date = datetime.fromtimestamp(mouse_point.x()).strftime('%Y-%m-%d')
            
            # Update tracking text
            if hasattr(self, 'candlesticks') and self.candlesticks.data is not None:
                data = self.candlesticks.data
                idx = np.abs(data['time'] - mouse_point.x()).argmin()
                self.tracking_text.setText(
                    f"{date}\n"
                    f"Open: ${data['open'][idx]:.2f}\n"
                    f"Close: ${data['close'][idx]:.2f}\n"
                    f"High: ${data['high'][idx]:.2f}\n"
                    f"Low: ${data['low'][idx]:.2f}"
                )
                self.tracking_text.setPos(mouse_point.x(), mouse_point.y())

    def update_chart(self, ticker):
        try:
            # Get historical data
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")
            
            if hist.empty:
                return

            # Convert index to timestamps
            dates = hist.index.view(np.int64) // 10**9
            
            # Create candlestick data
            candlestick_data = np.zeros(len(hist), dtype=[
                ('time', np.int64),
                ('open', float),
                ('close', float),
                ('low', float),
                ('high', float)
            ])
            
            candlestick_data['time'] = dates
            candlestick_data['open'] = hist['Open']
            candlestick_data['close'] = hist['Close']
            candlestick_data['low'] = hist['Low']
            candlestick_data['high'] = hist['High']

            # Clear previous items
            self.price_plot.clear()
            self.volume_plot.clear()

            # Create candlesticks
            self.candlesticks = pg.CandlestickItem(candlestick_data)
            self.price_plot.addItem(self.candlesticks)

            # Add volume bars
            colors = [COLORS["positive"] if close >= open_ else COLORS["negative"] 
                     for close, open_ in zip(hist['Close'], hist['Open'])]
            
            volume_bars = BarGraphItem(
                x=dates,
                height=hist['Volume'],
                width=86400 * 0.8,  # 80% of one day in seconds
                brushes=colors
            )
            self.volume_plot.addItem(volume_bars)
            
            # Add moving averages
            sma20 = hist['Close'].rolling(window=20).mean()
            sma50 = hist['Close'].rolling(window=50).mean()
            
            self.price_plot.plot(dates, sma20, pen=pg.mkPen(COLORS["accent"], width=1.5))
            self.price_plot.plot(dates, sma50, pen=pg.mkPen(COLORS["primary"], width=1.5))
            
            # Auto-range the view
            self.price_plot.autoRange()
            self.volume_plot.setXLink(self.price_plot)

        except Exception as e:
            print(f"Chart error: {e}")

    def _add_moving_averages(self, hist):
        # Calculate moving averages
        hist['SMA20'] = hist['Close'].rolling(window=20).mean()
        hist['SMA50'] = hist['Close'].rolling(window=50).mean()
        
        # Plot SMAs
        dates = hist.index.view(np.int64) // 10**9
        self.price_plot.plot(dates, hist['SMA20'], 
                           pen=pg.mkPen(COLORS["accent"], width=1.5), 
                           name="20 SMA")
        self.price_plot.plot(dates, hist['SMA50'], 
                           pen=pg.mkPen(COLORS["secondary"], width=1.5), 
                           name="50 SMA")

    def _add_volume_bars(self, hist, dates):
        # Create volume bars
        colors = [COLORS["positive"] if close >= open_ else COLORS["negative"] 
                for close, open_ in zip(hist['Close'], hist['Open'])]
        
        v_bars = pg.BarGraphItem(
            x=dates,
            height=hist['Volume'],
            width=86400 * 0.8,  # 80% of daily interval (in seconds)
            brushes=colors
        )
        self.volume_plot.addItem(v_bars)

    def mouse_moved(self, evt):
        pos = evt[0]
        if self.price_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.price_plot.vb.mapSceneToView(pos)
            self.crosshair_v.setPos(mouse_point.x())
            self.crosshair_h.setPos(mouse_point.y())
            
            # Convert timestamp to date
            date = datetime.fromtimestamp(mouse_point.x()).strftime('%Y-%m-%d')
            
            # Find nearest data point
            if hasattr(self, 'candlesticks') and self.candlesticks.data is not None:
                data = self.candlesticks.data
                idx = np.abs(data['time'] - mouse_point.x()).argmin()
                self.tracking_text.setText(
                    f"{date}\n"
                    f"Open: ${data['open'][idx]:.2f}\n"
                    f"Close: ${data['close'][idx]:.2f}\n"
                    f"High: ${data['high'][idx]:.2f}\n"
                    f"Low: ${data['low'][idx]:.2f}"
                )
                self.tracking_text.setPos(mouse_point.x(), mouse_point.y())

    def update_chart(self, ticker):
        try:
            # Get historical data
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo", interval="1d")

            if hist.empty:
                return

            # Clear previous items
            self.plot_widget.clear()

            # Create candlesticks
            for i in range(len(hist)):
                # Determine if it's a bullish or bearish candle
                is_bullish = hist['Close'].iloc[i] >= hist['Open'].iloc[i]
                color = COLORS['positive'] if is_bullish else COLORS['negative']

                # Draw candlestick body
                body = pg.PlotDataItem(
                    x=[i, i],
                    y=[hist['Open'].iloc[i], hist['Close'].iloc[i]],
                    pen=pg.mkPen(color, width=3)
                )

                # Draw wicks
                wick = pg.PlotDataItem(
                    x=[i, i],
                    y=[hist['Low'].iloc[i], hist['High'].iloc[i]],
                    pen=pg.mkPen(color, width=1)
                )

                self.plot_widget.addItem(body)
                self.plot_widget.addItem(wick)

            # Set axis labels
            dates = [d.strftime('%Y-%m-%d') for d in hist.index]
            ax = self.plot_widget.getAxis('bottom')
            ax.setTicks([[(i, date) for i, date in enumerate(dates)]])

            # Auto-range the view
            self.plot_widget.autoRange()

        except Exception as e:
            print(f"Chart error: {e}")

class ModernStockApp(QMainWindow):

    def _setup_styles(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
            }}

            /* Unified card style */
            #overview, #metrics, #analysisCard, #recommendation, #chatBox {{
                background-color: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
                padding: 16px;
            }}

            /* Modern button styling */
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['text']};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: medium;
            }}

            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}

            QPushButton:pressed {{
                background-color: {COLORS['primary']};
            }}

            /* Enhanced input fields */
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
                font-size: {FONT_SIZES['body']}pt;
                color: {COLORS['text']};
                selection-background-color: {COLORS['primary']};
            }}

            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}

            /* Modern tab widget */
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}

            QTabBar::tab {{
                background-color: transparent;
                color: {COLORS['text-secondary']};
                padding: 12px 24px;
                font-weight: medium;
                border-bottom: 3px solid transparent;
            }}

            QTabBar::tab:selected {{
                color: {COLORS['primary']};
                border-bottom: 3px solid {COLORS['primary']};
            }}

            QTabBar::tab:hover {{
                color: {COLORS['accent']};
            }}

            /* Improved chat interface */
            #chatBox {{
                background-color: {COLORS['surface']};
                border-radius: 12px;
                padding: 12px;
            }}

            QScrollArea {{
                border: none;
                background-color: transparent;
            }}

            /* Message bubbles */
            .user-message {{
                background-color: {COLORS['primary']};
                color: white;
                border-radius: 12px;
                padding: 12px;
                margin: 8px;
            }}

            .ai-message {{
                background-color: {COLORS['secondary']};
                color: {COLORS['text']};
                border-radius: 12px;
                padding: 12px;
                margin: 8px;
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

        # Set window icon
        self.setWindowIcon(QIcon(r"C:\Users\taylo\OneDrive\Desktop\Code\Axlotto transparent.ico"))
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

        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(8)

        logo_img = QLabel()
        try:
            pixmap = QPixmap(r"C:\Users\taylo\OneDrive\Desktop\Code\Axlotto transparent.png")
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_img.setPixmap(scaled_pixmap)
            else:
                print("Warning: Could not load logo image")
        except Exception as e:
            print(f"Error loading logo: {e}")

        self.logo = QLabel("Stoxalotl")
        self.logo.setFont(QFont(FONT_FAMILY, FONT_SIZES["title"], QFont.DemiBold))

        logo_layout.addWidget(logo_img)
        logo_layout.addWidget(self.logo)

        self.btn_home = QPushButton("Return Home")
        self.btn_home.setObjectName("homeButton")
        self.btn_home.setFixedSize(120, 36)
        self.btn_home.hide()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Enter stock ticker...")
        self.search.setFixedWidth(200)
        self.search.setClearButtonEnabled(True)

        self.investment_amount = QLineEdit()
        self.investment_amount.setPlaceholderText("Investment amount ($)")
        self.investment_amount.setFixedWidth(150)

        self.investment_timeframe = QLineEdit()
        self.investment_timeframe.setPlaceholderText("Days to invest")
        self.investment_timeframe.setFixedWidth(120)

        self.btn_analyze = QPushButton("Analyze")
        self.btn_analyze.setFixedSize(100, 36)

        header_layout.addWidget(logo_container)
        header_layout.addStretch()

        # Add home button to main layout at the bottom
        main_layout.addWidget(self.btn_home)
        self.btn_home.setObjectName("homeButton")
        header_layout.addWidget(self.search)
        header_layout.addWidget(self.investment_amount)
        header_layout.addWidget(self.investment_timeframe)
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

        # Initialize AI recommendation widget
        self.ai_recommendation = RecommendationWidget()

        # Right side container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        # Left sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(16)

        self.overview = StockOverview()
        self.metrics = KeyMetrics()

        # Add to favorites button
        self.btn_add_favorite = QPushButton("Add to Favorites")
        self.btn_add_favorite.clicked.connect(self._add_to_favorites)
        self.btn_add_favorite.hide()  # Initially hidden

        sidebar_layout.addWidget(self.overview)
        sidebar_layout.addWidget(self.metrics)
        sidebar_layout.addWidget(self.ai_recommendation)
        sidebar_layout.addWidget(self.btn_add_favorite)
        sidebar_layout.addStretch()

        # Main tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")

         # Add chat widget
        right_layout.addWidget(self.tabs)
        right_layout.addWidget(self._create_chat_widget())

        content_layout.addWidget(sidebar)
        content_layout.addWidget(right_container)

        self.main_app_page.setLayout(content_layout)


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
        self.long_term_card = AnalysisCard("Buy/Sell Analysis")
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

    # Modern chat widget
    def _create_chat_widget(self):
        chat_widget = QFrame()
        chat_widget.setObjectName("chatBox")
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        chat_layout.setSpacing(12)

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
        self.chat_history.setStyleSheet(f"""
            background-color: {COLORS['secondary']};
            border-radius: 12px;
            padding: 16px;
        """)

        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask about this stock...")
        self.chat_input.setStyleSheet(f"""
            background-color: {COLORS['surface']};
            border-radius: 8px;
            padding: 14px;
        """)

        self.chat_send = QPushButton("➤")
        self.chat_send.setFixedSize(48, 48)
        self.chat_send.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border-radius: 24px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
            }}
        """)

        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.chat_send)

        chat_layout.addWidget(QLabel("<b>Stock Assistant</b>"))
        chat_layout.addWidget(self.chat_history)
        chat_layout.addWidget(input_widget)

        return chat_widget

    def _send_chat_message(self):
        if not self.current_ticker:
            return

        user_input = self.chat_input.text().strip()
        if not user_input:
            return

        # Append user message
        self._append_chat_message("user", user_input)
        self.chat_input.clear()

        try:
            # Get current stock info
            stock = yf.Ticker(self.current_ticker)
            info = stock.info
            hist = stock.history(period="1d")

            # Prepare context
            context = f"""
            Current stock: {self.current_ticker}
            Price: ${info.get('currentPrice', 'N/A')}
            Previous Close: ${info.get('previousClose', 'N/A')}
            Market Cap: ${info.get('marketCap', 'N/A'):,}
            PE Ratio: {info.get('trailingPE', 'N/A')}
            Volume: {hist['Volume'].iloc[-1] if not hist.empty else 'N/A'}
            """

            # Generate AI response
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{
                    "role": "system",
                    "content": f"You are a stock analyst assistant. Use this context: {context}"
                }, {
                    "role": "user", 
                    "content": user_input
                }]
            )

            self._append_chat_message("ai", response['message']['content'])

        except Exception as e:
            self._append_chat_message("ai", f"Error: {str(e)}")

    def _append_chat_message(self, sender, message):
        color = COLORS['text']
        bg_color = COLORS['secondary'] if sender == "user" else COLORS['surface']
        alignment = "right" if sender == "user" else "left"

        self.chat_history.append(f"""
            <div style='
                margin: 4px;
                padding: 8px;
                border-radius: 8px;
                background-color: {bg_color};
                color: {color};
                text-align: {alignment};
            '>
                <b>{'You' if sender == 'user' else 'AI'}:</b> {message}
            </div>
        """)
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )

    def _load_favorites(self, tickers=None):
        # Clear existing favorites
        for i in reversed(range(self.favorites_layout.count())):
            widget = self.favorites_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Load favorites from memory
        if not hasattr(self, 'favorite_tickers'):
            self.favorite_tickers = []

        for ticker in self.favorite_tickers:
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

    def _add_to_favorites(self):
        if self.current_ticker and self.current_ticker not in self.favorite_tickers:
            self.favorite_tickers.append(self.current_ticker)
            self._load_favorites()

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
            container = QPushButton()
            container.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: 12px;
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['primary']};
            }}
            """)

            text = f"{ticker}\nPrice: ${price:.2f}\nChange: {change_pct:+.2f}%"
            container.setText(text)
            container.clicked.connect(lambda _, t=ticker: self._load_stock(t))
            self.rec_layout.addWidget(container)

    def _load_stock(self, ticker):
        self.search.setText(ticker)
        self._analyze()
        self.stacked_widget.setCurrentIndex(1)
        self.btn_home.show()
        self.btn_add_favorite.show()

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

            # Switch to main app page first
            self.stacked_widget.setCurrentIndex(1)
            self.btn_home.show()
            self.btn_add_favorite.show()

            # Initial data load
            self._update_ui()

            # Generate analysis and news
            self.news_card.content.setPlainText(self._get_stock_news(ticker))
            self._generate_analysis(stock, "long_term", self.long_term_card)
            self._generate_analysis(stock, "day_trade", self.day_trade_card)
            # Generate AI recommendation percentages for Buy, Hold, Sell
            self._generate_buy_hold_sell(stock)
            # Update chart
            self.chart.update_chart(ticker)

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
                f"{article['title']}\n{article['description'] or 'No description'}"
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

            messages = [
                    {
                        "role": "system",
                        "content": "You are a seasoned financial analyst with expertise in stock market forecasting and technical analysis. Provide clear, concise, and actionable recommendations based on the data provided."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
                stream=False
            )

            analysis = response['message']['content']
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
        investment = self.investment_amount.text() if hasattr(self, 'investment_amount') else "N/A"
        timeframe = self.investment_timeframe.text() if hasattr(self, 'investment_timeframe') else "N/A"

        return f"""As an AI focused on maximizing profit for professional investors, analyze {self.current_ticker} with:
- Current price: ${info.get('currentPrice', 'N/A')}
- Market cap: {info.get('marketCap', 'N/A')}
- P/E ratio: {info.get('trailingPE', 'N/A')}
- Investment amount: ${investment}
- Investment timeframe: {timeframe} months

Provide a profit-focused analysis with:
1. Clear BUY/SELL recommendation
2. Projected price targets: 3-month, 6-month, 1-year
3. Expected ROI percentage
4. Profit potential analysis
5. Key catalysts for price movement

Format with bullet points and end with:
VERDICT: [BUY/SELL]
PROJECTED PROFIT: $X (X%)"""

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
        try:
            handler = TA_Handler(
                symbol=self.current_ticker,
                screener="america",
                exchange="NASDAQ",
                interval=Interval.INTERVAL_1_DAY
            )
            analysis = handler.get_analysis()
            recs = self._parse_recommendations_from_text(str(analysis))
            self.ai_recommendation.update_recommendations(recs)
        except Exception as e:
            print(f"Recommendation error: {e}")


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
        if "VERDICT: BUY" in text:
            return COLORS['positive']
        elif "VERDICT: SELL" in text:
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
        self.news_card.clicked.connect(lambda title, text, color: self.show_maximized_card(title, text, color))
        self.long_term_card.clicked.connect(lambda title, text, color: self.show_maximized_card(title, text, color))
        self.day_trade_card.clicked.connect(lambda title, text, color: self.show_maximized_card(title, text, color))
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

    # Set application icon for taskbar/system tray
    app_icon = QIcon(r"C:\Users\taylo\OneDrive\Desktop\Code\Axlotto transparent.ico")
    app.setWindowIcon(app_icon)

    window = ModernStockApp()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())