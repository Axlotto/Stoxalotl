import sys
import re
import yfinance as yf
import ollama
import requests
import numpy as np
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox,
    QGridLayout, QStyle, QTabWidget, QFrame, QScrollArea,
    QDialog, QDialogButtonBox, QStackedWidget, QSizePolicy,
    QComboBox, QToolBar, QMenuBar, QMenu, QFormLayout, QSlider
)
from PySide6.QtCore import Qt, QTimer, Signal, QSettings, QUrl
from PySide6.QtGui import QFont, QColor, QActionGroup, QAction
import pyqtgraph as pg
from PySide6.QtWebEngineWidgets import QWebEngineView
import pyqtgraph as pg
from pyqtgraph import PlotWidget, AxisItem

from Testing import KeyMetrics, RecommendationWidget

# Configuration
NEWS_API_KEY = "c91f9673406647e280aa6faf87ef892a"
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Modern design constants
THEMES = {
    "Dark": {
        "background": "#0a0a0a",
        "surface": "#1a1a1a",
        "primary": "#00bcd4",
        "secondary": "#2d2d2d",
        "text": "#ffffff",
        "text-secondary": "#858585",
        "positive": "#4caf50",
        "negative": "#f44336",
        "border": "#333333"
    },
    "Light": {
        "background": "#f5f5f5",
        "surface": "#ffffff",
        "primary": "#2196F3",
        "secondary": "#e3f2fd",
        "text": "#212121",
        "text-secondary": "#757575",
        "positive": "#388E3C",
        "negative": "#D32F2F",
        "border": "#BDBDBD"
    },
    "Blue": {
        "background": "#0F172A",
        "surface": "#1E293B",
        "primary": "#3B82F6",
        "secondary": "#334155",
        "text": "#F8FAFC",
        "text-secondary": "#94A3B8",
        "positive": "#22C55E",
        "negative": "#EF4444",
        "border": "#475569"
    }
}

FONT_FAMILY = "Segoe UI"
FONT_SIZES = {
    "title": 18,
    "header": 14,
    "body": 12,
    "small": 10
}

class DateAxis(AxisItem):
    def tickStrings(self, values, scale):
        return [datetime.fromtimestamp(value).strftime("%m/%d") for value in values]

class StockChart(PlotWidget):
    def __init__(self):
        super().__init__(axisItems={'bottom': DateAxis(orientation='bottom')})
        self.setBackground(THEMES["Dark"]["surface"])
        self.getAxis("left").setPen(pg.mkPen(THEMES["Dark"]["text"]))
        self.getAxis("bottom").setPen(pg.mkPen(THEMES["Dark"]["text"]))
        self.setAntialiasing(True)
        self.legend = self.addLegend()
        
    def update_chart(self, ticker, time_frame="3M", chart_type="Line"):
        stock = yf.Ticker(ticker)
        periods = {
            "1D": ("1d", "5m"),
            "1W": ("5d", "15m"),
            "1M": ("1mo", "1h"),
            "3M": ("3mo", "1d"),
            "1Y": ("1y", "1wk"),
            "5Y": ("5y", "1mo")
        }
        period, interval = periods.get(time_frame, ("3mo", "1d"))
        
        hist = stock.history(period=period, interval=interval)
        if (hist.empty):
            return
            
        dates = hist.index.view(np.int64) // 10**9
        opens = hist['Open'].values
        closes = hist['Close'].values
        highs = hist['High'].values
        lows = hist['Low'].values
        
        self.clear()
        if (chart_type == "Candlestick"):
            candlesticks = []
            for i in range(len(dates)):
                item = pg.CandleStickItem(
                    x=dates[i],
                    open=opens[i],
                    close=closes[i],
                    high=highs[i],
                    low=lows[i],
                    brush=pg.mkBrush(THEMES["Dark"]["positive"]) if closes[i] > opens[i] else pg.mkBrush(THEMES["Dark"]["negative"]),
                    pen=pg.mkPen(THEMES["Dark"]["border"]))
                candlesticks.append(item)
                self.addItem(item)
        else:
            self.plot(dates, closes, pen=pg.mkPen(THEMES["Dark"]["primary"], width=2))

class StockOverview(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(160)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        header = QHBoxLayout()
        self.ticker = QLabel()
        self.ticker.setFont(QFont(FONT_FAMILY, 24, QFont.Bold))
        
        self.watchlist_btn = QPushButton("☆")
        self.watchlist_btn.setCheckable(True)
        self.watchlist_btn.setFixedSize(32, 32)
        self.watchlist_btn.setStyleSheet("QPushButton { font-size: 20px; }")
        
        header.addWidget(self.ticker)
        header.addStretch()
        header.addWidget(self.watchlist_btn)
        
        self.price = QLabel()
        self.price.setFont(QFont(FONT_FAMILY, 28, QFont.Medium))
        
        self.change = QLabel()
        self.change.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
        
        layout.addLayout(header)
        layout.addWidget(self.price)
        layout.addWidget(self.change)
        layout.addStretch()

    def update_overview(self, ticker, price, change):
        self.ticker.setText(ticker)
        self.price.setText(f"${price:.2f}")
        self.change.setText(change)

class AnalysisCard(QFrame):
    clicked = Signal(str, str, str)

    def __init__(self, title):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Make the card resizable
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        header = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setFlat(True)
        
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.toggle_btn)
        
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setVisible(True)
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Allow horizontal expansion
        self.content.setMinimumWidth(200) # Set a minimum width
        
        layout.addLayout(header)
        layout.addWidget(self.content)
        
        self.toggle_btn.clicked.connect(self.toggle_content)
        
    def toggle_content(self):
        self.content.setVisible(not self.content.isVisible())
        self.toggle_btn.setText("▲" if self.content.isVisible() else "▼")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        layout = QVBoxLayout()
        
        form = QFormLayout()
        self.model_selector = QComboBox()
        self.model_selector.addItems(["deepseek-r1:1.5b", "llama2", "mistral"])
        
        self.interval_slider = QSlider(Qt.Horizontal)
        self.interval_slider.setRange(5, 60)
        self.interval_slider.setTickInterval(5)
        
        form.addRow("AI Model:", self.model_selector)
        form.addRow("Update Interval (sec):", self.interval_slider)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

class ModernStockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("StockApp", "StockPro")
        self.current_theme = self.settings.value("Theme", "Dark")
        self.current_ticker = None
        self.watchlist = self.settings.value("Watchlist", [])
        
        self.setWindowTitle("Stock Analysis Pro")
        self.setGeometry(100, 100, 1280, 800)
        self._setup_ui()
        self._apply_theme()
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_data)
        self.load_settings()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Menu Bar
        menu_bar = QMenuBar()
        settings_menu = QMenu("&Settings", self)
        
        # Theme Menu
        theme_menu = QMenu("&Theme", self)
        self.theme_group = QActionGroup(self)
        for theme in THEMES:
            action = QAction(theme, self, checkable=True)
            action.triggered.connect(lambda _, t=theme: self._change_theme(t))
            self.theme_group.addAction(action)
            theme_menu.addAction(action)
            if theme == self.current_theme:
                action.setChecked(True)
        
        # Preferences Action
        pref_action = QAction("Preferences", self)
        pref_action.triggered.connect(self._show_settings)
        
        settings_menu.addMenu(theme_menu)
        settings_menu.addAction(pref_action)
        menu_bar.addMenu(settings_menu)
        self.setMenuBar(menu_bar)
        
        # Toolbar
        toolbar = QToolBar()
        self.time_frame = QComboBox()
        self.time_frame.addItems(["1D", "1W", "1M", "3M", "1Y", "5Y"])
        self.chart_type = QComboBox()
        self.chart_type.addItems(["Line", "Candlestick"])
        
        toolbar.addWidget(QLabel("Time Frame:"))
        toolbar.addWidget(self.time_frame)
        toolbar.addWidget(QLabel("Chart Type:"))
        toolbar.addWidget(self.chart_type)
        self.addToolBar(toolbar)
        
        # Main Content
        self.stacked_widget = QStackedWidget()
        self._setup_home_page()
        self._setup_analysis_page()
        
        main_layout.addWidget(self.stacked_widget)
        
    def _setup_home_page(self):
        # Home page implementation similar to previous version
        pass
        
    def _setup_analysis_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        
        # Left Panel
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        self.overview = StockOverview()
        self.metrics = KeyMetrics()
        self.recommendation = RecommendationWidget()
        
        left_layout.addWidget(self.overview)
        left_layout.addWidget(self.metrics)
        left_layout.addWidget(self.recommendation)
        
        # Right Panel
        right_panel = QTabWidget()
        self.chart = StockChart()
        self.news_card = AnalysisCard("Latest News")
        self.analysis_card = AnalysisCard("AI Analysis")
        
        right_panel.addTab(self.chart, "Chart")
        right_panel.addTab(self.news_card, "News")
        right_panel.addTab(self.analysis_card, "Analysis")
        
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        self.stacked_widget.addWidget(page)
        
    def _apply_theme(self):
        theme = THEMES[self.current_theme]
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['background']};
                color: {theme['text']};
            }}
            QFrame {{
                background-color: {theme['surface']};
                border-radius: 8px;
                padding: 8px;
            }}
            QTextEdit {{
                background-color: {theme['secondary']};
                border: 1px solid {theme['border']};
            }}
        """)
        
    def _change_theme(self, theme_name):
        self.current_theme = theme_name
        self.settings.setValue("Theme", theme_name)
        self._apply_theme()
        
    def load_settings(self):
        self.model = self.settings.value("Model", "deepseek-r1:1.5b")
        interval = int(self.settings.value("Interval", 15))
        self.update_timer.setInterval(interval * 1000)
        
    def _show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.settings.setValue("Model", dialog.model_selector.currentText())
            self.settings.setValue("Interval", dialog.interval_slider.value())
            self.load_settings()
            
    def _show_news_detail(self, url):
        dialog = QDialog(self)
        web_view = QWebEngineView()
        web_view.load(QUrl(url))
        layout = QVBoxLayout(dialog)
        layout.addWidget(web_view)
        dialog.resize(800, 600)
        dialog.exec()

# Run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernStockApp()
    window.show()
    sys.exit(app.exec())