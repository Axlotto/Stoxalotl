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
    QComboBox, QToolBar, QMenuBar, QMenu, QFormLayout, QSlider,
    QGraphicsProxyWidget, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Signal, QSettings, QUrl
from PySide6.QtGui import QFont, QColor, QActionGroup, QAction
import pyqtgraph as pg
from PySide6.QtWebEngineWidgets import QWebEngineView
import pyqtgraph as pg
from pyqtgraph import PlotWidget, AxisItem

# Configuration
NEWS_API_KEY = "c91f9673406647e280aa6faf87ef892a"
NEWS_API_URL = "https://newsapi.org/v2/everything"

DEFAULTS = {
    "profit_target": 0.10  # 10% profit target by default
}

def format_percentage(value):
    """Format a decimal value as a percentage string."""
    return f"{value * 100:.1f}%"

def format_price(value):
    """Format a value as a price string."""
    return f"${value:.2f}"

# Modern design constants
THEMES = {
    "Dark": {
        "background": "#0a0a0a",
        "surface": "#1a1a0a",
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
        for row, (key, value) in enumerate(metrics.items()):
            lbl = QLabel(key)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
            lbl.setStyleSheet(f"color: {THEMES['Dark']['text-secondary']}")

            # Format the value appropriately
            if isinstance(value, (int, float)):
                if key == 'market_cap':
                    formatted_value = f"${value/1e9:.2f}B"
                elif key == 'volume':
                    formatted_value = f"{value:,.0f}"
                elif key == 'dividend_yield':
                    formatted_value = f"{value:.2f}%"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)

            val = QLabel(formatted_value)
            val.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"], QFont.Medium))
            val.setStyleSheet(f"color: {THEMES['Dark']['text']}")

            self.grid.addWidget(lbl, row, 0)
            self.grid.addWidget(val, row, 1)

class DateAxis(AxisItem):
    def tickStrings(self, values, scale, spacing):
        """Convert timestamps to UK date format"""
        return [datetime.fromtimestamp(value).strftime("%d/%m") for value in values]  # Changed to UK format

class CandleStickItem(pg.GraphicsObject):
    def __init__(self, x, open, close, high, low, brush=None, pen=None):
        super().__init__()
        self.x = x
        self.open = open
        self.close = close
        self.high = high
        self.low = low
        self.brush = brush or pg.mkBrush('w')
        self.pen = pen or pg.mkPen('w')
        self.picture = None
        self.generatePicture()

    def generatePicture(self):
        self.picture = pg.QtGui.QPicture()
        p = pg.QtGui.QPainter(self.picture)
        p.setPen(self.pen)
        p.setBrush(self.brush)
        
        # Draw candlestick body
        if self.open > self.close:
            p.drawRect(pg.QtCore.QRectF(self.x - 0.25, self.close, 0.5, self.open - self.close))
        else:
            p.drawRect(pg.QtCore.QRectF(self.x - 0.25, self.open, 0.5, self.close - self.open))
        
        # Draw wicks
        p.drawLine(pg.QtCore.QPointF(self.x, self.low), pg.QtCore.QPointF(self.x, self.high))
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())

class StockChart(PlotWidget):
    def __init__(self):
        super().__init__(axisItems={'bottom': DateAxis(orientation='bottom')})
        self.setBackground(THEMES["Dark"]["surface"])
        self.getAxis("left").setPen(pg.mkPen(THEMES["Dark"]["text"]))
        self.getAxis("bottom").setPen(pg.mkPen(THEMES["Dark"]["text"]))
        self.setAntialiasing(True)
        self.legend = self.addLegend()
        
        # Setup view box for proper mouse interaction
        view_box = self.getViewBox()
        view_box.setMouseMode(pg.ViewBox.PanMode)  # Change to PanMode
        view_box.enableAutoRange(enable=True)
        view_box.setAutoVisible(y=True)
        view_box.setLimits(xMin=None, xMax=None, yMin=None, yMax=None)  # Remove limits
        
        # Enable all mouse interactions
        view_box.setMouseEnabled(x=True, y=True)
        view_box.mouseDragEvent = self._mouseDragEvent  # Custom drag handler
        self.setMouseEnabled(x=True, y=True)
        
        # Add mouse interactions hint
        self.hint_text = pg.TextItem(
            text="Mouse Controls:\n" + 
                 "- Left click drag to pan\n" +
                 "- Mouse wheel to zoom\n" + 
                 "- Double-click to reset view",
            color=THEMES["Dark"]["text-secondary"],
            anchor=(0, 0)
        )
        
        # Store view state and ranges
        self.last_view_state = None
        self.original_range = {'x': None, 'y': None}
        
        # Add storage for technical indicators
        self.support_lines = []
        self.resistance_lines = []
        self.peak_labels = []
        self.period_peaks = {}
        
        # Add control buttons
        self._add_control_buttons()

        # Add visibility flags
        self.show_peaks = True
        self.show_support_resistance = True
        self.show_markers = True
        
        # Add visibility controls
        self._add_visibility_controls()
        
        # Initialize drag state
        self._is_dragging = False
        self._last_pos = None

    def _add_control_buttons(self):
        """Add control buttons to the chart"""
        # Create container widget for buttons
        proxy = QGraphicsProxyWidget()  # Using PySide6 QGraphicsProxyWidget
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create buttons
        buttons = [
            ('+', self.zoomIn),
            ('-', self.zoomOut),
            ('⟲', self.resetZoom)
        ]

        for text, callback in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(25, 25)
            btn.clicked.connect(callback)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
                QPushButton:pressed {
                    background-color: #1d1d1d;
                }
            """)
            layout.addWidget(btn)

        # Add the buttons to the chart
        proxy.setWidget(widget)
        self.scene().addItem(proxy)
        proxy.setPos(60, 20)
        proxy.setZValue(100)  # Ensure buttons are above chart

    def _add_visibility_controls(self):
        """Add buttons to toggle visibility of different markers"""
        control_proxy = QGraphicsProxyWidget()
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setSpacing(4)
        control_layout.setContentsMargins(0, 0, 0, 0)

        # Create toggle buttons with style
        button_style = """
            QPushButton {
                background-color: transparent;
                color: #858585;
                border: none;
            }
            QPushButton:checked {
                color: white;
                font-weight: bold;
            }
        """

        toggles = [
            ('📊', 'Peak Markers', lambda: self._toggle_visibility('peaks')),
            ('📈', 'Support/Resistance', lambda: self._toggle_visibility('levels')),
            ('🏷️', 'Labels', lambda: self._toggle_visibility('markers'))
        ]

        for icon, tooltip, callback in toggles:
            btn = QPushButton(icon)
            btn.setFixedSize(25, 25)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)  # Make button toggleable
            btn.setChecked(True)    # Start checked
            btn.setStyleSheet(button_style)
            btn.clicked.connect(callback)
            control_layout.addWidget(btn)

        # Position controls in top-right corner
        control_proxy.setWidget(control_widget)
        self.scene().addItem(control_proxy)
        control_proxy.setPos(self.width() - 120, 20)

    def _toggle_visibility(self, marker_type):
        """Toggle visibility of different marker types"""
        if marker_type == 'peaks':
            self.show_peaks = not self.show_peaks
            for label in self.peak_labels:
                label.setVisible(self.show_peaks)
                
        elif marker_type == 'levels':
            self.show_support_resistance = not self.show_support_resistance
            for line in self.support_lines + self.resistance_lines:
                line.setVisible(self.show_support_resistance)
                
        elif marker_type == 'markers':
            self.show_markers = not self.show_markers
            # Toggle all markers
            for item in self.peak_labels + self.support_lines + self.resistance_lines:
                item.setVisible(self.show_markers)

    def zoomIn(self):
        """Zoom in by 25%"""
        self.getViewBox().scaleBy((0.75, 0.75))

    def zoomOut(self):
        """Zoom out by 25%"""
        self.getViewBox().scaleBy((1.25, 1.25))

    def resetZoom(self):
        """Reset to original view"""
        if self.original_range['x'] is not None and self.original_range['y'] is not None:
            self.getViewBox().setRange(xRange=self.original_range['x'], yRange=self.original_range['y'])

    def wheelEvent(self, event):
        """Handle mouse wheel events for zooming"""
        # Get the position of the mouse in view coordinates
        pos = self.getViewBox().mapSceneToView(event.position())
        
        # Calculate zoom factor
        factor = 0.9 if event.angleDelta().y() > 0 else 1.1
        
        # Apply zoom centered on mouse position
        self.getViewBox().scaleBy((factor, factor), pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self._last_pos = None
            self.setCursor(Qt.ArrowCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._last_pos is not None:
            delta = event.pos() - self._last_pos
            self._last_pos = event.pos()
            
            # Convert screen pixels to view coordinates
            view_box = self.getViewBox()
            x_scale = view_box.viewRect().width() / self.width()
            y_scale = view_box.viewRect().height() / self.height()
            
            # Apply the pan
            view_box.translateBy(x=delta.x() * x_scale, y=delta.y() * y_scale)
        event.accept()

    def _mouseDragEvent(self, ev):
        """Custom drag event handler"""
        if ev.button() == Qt.LeftButton:
            ev.accept()
            pos = ev.pos()
            lastPos = ev.lastPos()
            dif = pos - lastPos
            self.getViewBox().translateBy(dif)
        else:
            ev.ignore()

    def _calculate_support_resistance(self, closes, window=20):
        """Calculate support and resistance levels"""
        levels = []
        for i in range(window, len(closes)):
            window_slice = closes[i-window:i]
            max_val = max(window_slice)
            min_val = min(window_slice)
            
            if closes[i] > max_val:  # New resistance level
                levels.append((i, closes[i], 'resistance'))
            elif closes[i] < min_val:  # New support level
                levels.append((i, closes[i], 'support'))
        
        return levels

    def _find_period_peaks(self, hist, dates):
        """Find peaks for different time periods"""
        peaks = {}
        periods = {
            '1D': 1,
            '1W': 7,
            '1M': 30,
            '3M': 90,
            '6M': 180,
            '1Y': 365
        }
        
        for period_name, days in periods.items():
            # Calculate period start index
            cutoff_date = dates[-1] - (days * 24 * 60 * 60)
            period_data = [(d, p) for d, p in zip(dates, hist['Close']) if d >= cutoff_date]
            
            if period_data:
                period_dates, period_prices = zip(*period_data)
                period_high = max(period_prices)
                period_low = min(period_prices)
                peaks[period_name] = {
                    'high': period_high,
                    'low': period_low,
                    'high_date': period_dates[period_prices.index(period_high)],
                    'low_date': period_dates[period_prices.index(period_low)]
                }
        
        return peaks

    def update_chart(self, ticker, time_frame="3M", chart_type="Both"):
        stock = yf.Ticker(ticker)
        periods = {
            "1D": ("1d", "5m"),
            "1W": ("5d", "15m"),
            "1M": ("1mo", "1h"),
            "3M": ("3mo", "1d"),
            "6M": ("6mo", "1d"),
            "1Y": ("1y", "1wk"),
            "5Y": ("5y", "1mo")
        }
        period, interval = periods.get(time_frame, ("3mo", "1d"))
        
        hist = stock.history(period=period, interval=interval)
        if hist.empty:
            return
            
        # Clear previous items
        self.clear()
        for label in self.peak_labels:
            self.removeItem(label)
        self.peak_labels.clear()
            
        dates = hist.index.view(np.int64) // 10**9
        opens = hist['Open'].values
        closes = hist['Close'].values
        highs = hist['High'].values
        lows = hist['Low'].values
        
        # Find peaks
        from scipy.signal import find_peaks
        peaks, _ = find_peaks(closes, distance=20)  # Adjust distance as needed
        
        # Plot line chart
        if chart_type in ["Line", "Both"]:
            line = self.plot(dates, closes, pen=pg.mkPen(THEMES["Dark"]["primary"], width=2), name="Price")
            
            # Add peak labels
            for peak_idx in peaks:
                peak_price = closes[peak_idx]
                peak_date = dates[peak_idx]
                label = pg.TextItem(
                    text=f"£{peak_price:.2f}",
                    color=THEMES["Dark"]["text"],
                    anchor=(0, 1)
                )
                self.addItem(label)
                label.setPos(peak_date, peak_price)
                self.peak_labels.append(label)
        
        # Plot candlesticks
        if chart_type in ["Candlestick", "Both"]:
            for i in range(len(dates)):
                candlestick = CandleStickItem(
                    x=dates[i],
                    open=opens[i],
                    close=closes[i],
                    high=highs[i],
                    low=lows[i],
                    brush=pg.mkBrush(THEMES["Dark"]["positive"]) if closes[i] > opens[i] 
                          else pg.mkBrush(THEMES["Dark"]["negative"]),
                    pen=pg.mkPen(THEMES["Dark"]["border"])
                )
                self.addItem(candlestick)

        # Set fixed range for y-axis
        y_min = min(lows) * 0.95
        y_max = max(highs) * 1.05
        self.setYRange(y_min, y_max)

        # Clear previous items
        self.clear()
        for line in self.support_lines + self.resistance_lines:
            self.removeItem(line)
        for label in self.peak_labels:
            self.removeItem(label)
        self.support_lines.clear()
        self.resistance_lines.clear()
        self.peak_labels.clear()

        stock = yf.Ticker(ticker)
        periods = {
            "1D": ("1d", "5m"),
            "1W": ("5d", "15m"),
            "1M": ("1mo", "1h"),
            "3M": ("3mo", "1d"),
            "6M": ("6mo", "1d"),
            "1Y": ("1y", "1wk"),
            "5Y": ("5y", "1mo")
        }
        period, interval = periods.get(time_frame, ("3mo", "1d"))
        
        hist = stock.history(period=period, interval=interval)
        if hist.empty:
            return
            
        dates = hist.index.view(np.int64) // 10**9
        closes = hist['Close'].values
        
        # Find peaks for different time periods
        self.period_peaks = self._find_period_peaks(hist, dates)
        
        # Calculate support and resistance levels
        levels = self._calculate_support_resistance(closes)
        
        # Plot base chart (line or candlesticks)
        if chart_type in ["Line", "Both"]:
            self.plot(dates, closes, pen=pg.mkPen(THEMES["Dark"]["primary"], width=2), name="Price")
        
        if chart_type in ["Candlestick", "Both"]:
            # ... existing candlestick plotting code ...
            pass

        # Add support and resistance lines
        for date_idx, price, level_type in levels:
            if level_type == 'support':
                line = self.addLine(y=price, pen=pg.mkPen('g', width=1, style=Qt.DashLine))
                self.support_lines.append(line)
            else:  # resistance
                line = self.addLine(y=price, pen=pg.mkPen('r', width=1, style=Qt.DashLine))
                self.resistance_lines.append(line)

        # Add period peak labels
        y_range = max(closes) - min(closes)
        for i, (period, data) in enumerate(self.period_peaks.items()):
            # Create high label
            high_label = pg.TextItem(
                text=f"{period} High: ${data['high']:.2f}",
                color=THEMES["Dark"]["positive"],
                anchor=(0, -1.5)
            )
            self.addItem(high_label)
            high_label.setPos(dates[-1], data['high'])
            self.peak_labels.append(high_label)
            
            # Create low label
            low_label = pg.TextItem(
                text=f"{period} Low: ${data['low']:.2f}",
                color=THEMES["Dark"]["negative"],
                anchor=(0, 1.5)
            )
            self.addItem(low_label)
            low_label.setPos(dates[-1], data['low'])
            self.peak_labels.append(low_label)

        # Store the initial range for reset functionality
        self.original_range = {
            'x': (min(dates), max(dates)),
            'y': (y_min, y_max)
        }
        
        # Set initial view without locking it
        self.getViewBox().setRange(
            xRange=(min(dates), max(dates)),
            yRange=(y_min, y_max),
            padding=0.1
        )
        
        # Add control hint
        self.addItem(self.hint_text)
        self.hint_text.setPos(dates[0], y_max)

        # Store initial view state
        self.last_view_state = self.getViewBox().getState()
        
        # Set initial range but don't lock it
        self.setXRange(min(dates), max(dates), padding=0.1)
        self.setYRange(y_min, y_max, padding=0.1)

        # Add items with visibility respect
        if self.show_peaks:
            for label in self.peak_labels:
                label.setVisible(True)
        else:
            for label in self.peak_labels:
                label.setVisible(False)

        if self.show_support_resistance:
            for line in self.support_lines + self.resistance_lines:
                line.setVisible(True)
        else:
            for line in self.support_lines + self.resistance_lines:
                line.setVisible(False)

class StockOverview(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(160)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header with ticker and star button
        header = QHBoxLayout()
        
        # Ticker label
        self.ticker = QLabel()
        self.ticker.setFont(QFont(FONT_FAMILY, 24, QFont.Bold))
        
        # Star button for watchlist with improved styling
        self.watchlist_btn = QPushButton("☆")
        self.watchlist_btn.setCheckable(True)
        self.watchlist_btn.setFixedSize(32, 32)
        self.watchlist_btn.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                color: #858585;
                background: transparent;
                border: none;
            }
            QPushButton:checked {
                color: #FFD700;  /* Gold color for active state */
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        
        header.addWidget(self.ticker)
        header.addWidget(self.watchlist_btn)
        header.addStretch()
        
        self.price = QLabel()
        self.price.setFont(QFont(FONT_FAMILY, 28, QFont.Medium))
        
        self.change = QLabel()
        self.change.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
        
        layout.addLayout(header)
        layout.addWidget(self.price)
        layout.addWidget(self.change)
        layout.addStretch()

    def update_overview(self, ticker, price, change, is_favorite=False):
        self.ticker.setText(ticker)
        self.price.setText(f"${price:.2f}")
        self.change.setText(change)
        # Update button state and text based on favorite status
        self.watchlist_btn.setChecked(is_favorite)
        self.watchlist_btn.setText("★" if is_favorite else "☆")

class AnalysisCard(QFrame):
    maximize_signal = Signal(dict)  # Add this signal definition

    def __init__(self, title):
        super().__init__()
        self.title = title
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setLineWidth(2)
        
        layout = QVBoxLayout(self)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        # Content text edit
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setMinimumHeight(100)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.content)
        
        # Make the card clickable
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        """Handle mouse click events"""
        if event.button() == Qt.LeftButton:
            # Emit signal with card data
            self.maximize_signal.emit({
                'title': self.title,
                'content': self.content.toPlainText()
            })
        super().mousePressEvent(event)

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


class RecommendationWidget(QFrame):
    """Widget to display peak prices and support/resistance levels"""
    def __init__(self):
        super().__init__()
        self.setObjectName("technical_levels")
        self.current_theme = "Dark"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("Technical Levels")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        layout.addWidget(title)

        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(8)
        self.grid.setHorizontalSpacing(16)
        layout.addLayout(self.grid)
        layout.addStretch()

    def update_levels(self, data):
        """
        Update the grid with price levels and technical indicators
        data: dictionary containing peak prices and support/resistance levels
        """
        # Clear previous entries
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        row = 0
        
        # Add period highs and lows
        for period in ['1D', '1W', '1M', '3M', '6M', '1Y']:
            if period in data.get('peaks', {}):
                # Period label
                period_label = QLabel(period)
                period_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"], QFont.Bold))
                period_label.setStyleSheet(f"color: {THEMES[self.current_theme]['text']}")
                self.grid.addWidget(period_label, row, 0, 1, 2)
                row += 1

                # High value
                high_label = QLabel("High:")
                high_label.setStyleSheet(f"color: {THEMES[self.current_theme]['text-secondary']}")
                high_value = QLabel(f"${data['peaks'][period]['high']:.2f}")
                high_value.setStyleSheet(f"color: {THEMES[self.current_theme]['positive']}")
                self.grid.addWidget(high_label, row, 0)
                self.grid.addWidget(high_value, row, 1)
                row += 1

                # Low value
                low_label = QLabel("Low:")
                low_label.setStyleSheet(f"color: {THEMES[self.current_theme]['text-secondary']}")
                low_value = QLabel(f"${data['peaks'][period]['low']:.2f}")
                low_value.setStyleSheet(f"color: {THEMES[self.current_theme]['negative']}")
                self.grid.addWidget(low_label, row, 0)
                self.grid.addWidget(low_value, row, 1)
                row += 1

        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {THEMES[self.current_theme]['border']}")
        self.grid.addWidget(separator, row, 0, 1, 2)
        row += 1

        # Add support/resistance levels
        if 'levels' in data:
            support_label = QLabel("Support:")
            support_label.setStyleSheet(f"color: {THEMES[self.current_theme]['text-secondary']}")
            support_value = QLabel(f"${data['levels']['support']:.2f}")
            support_value.setStyleSheet(f"color: {THEMES[self.current_theme]['positive']}")
            self.grid.addWidget(support_label, row, 0)
            self.grid.addWidget(support_value, row, 1)
            row += 1

            resistance_label = QLabel("Resistance:")
            resistance_label.setStyleSheet(f"color: {THEMES[self.current_theme]['text-secondary']}")
            resistance_value = QLabel(f"${data['levels']['resistance']:.2f}")
            resistance_value.setStyleSheet(f"color: {THEMES[self.current_theme]['negative']}")
            self.grid.addWidget(resistance_label, row, 0)
            self.grid.addWidget(resistance_value, row, 1)

    def update_recommendations(self, recommendations):
        """
        Update the widget with new recommendations.
        """
        # Clear previous entries
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        row = 0
        for rec in recommendations:
            label = QLabel(rec)
            label.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
            label.setStyleSheet(f"color: {THEMES[self.current_theme]['text']}")
            self.grid.addWidget(label, row, 0, 1, 2)
            row += 1

class ProfitTarget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Profit Target Analysis")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.Bold))
        layout.addWidget(title)
        
        # Current Price
        self.current_price_label = QLabel("Current Price: N/A")
        self.current_price_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(self.current_price_label)
        
        # Profit Target
        self.profit_target_label = QLabel(f"Target Profit: {format_percentage(DEFAULTS['profit_target'])}")
        self.profit_target_label.setStyleSheet("color: #4CAF50;")  # Green color
        layout.addWidget(self.profit_target_label)
        
        # Target Price
        self.target_price_label = QLabel("Target Price: N/A")
        self.target_price_label.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(self.target_price_label)
        
        # Progress Bar with modern style
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #2d2d2d;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Set border and background for the widget
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 8px;
            }
        """)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setMinimumHeight(150)

    def update_profit_target(self, current_price):
        """
        Update profit target analysis with current price.
        
        Args:
            current_price (float): Current stock price
        """
        try:
            current_price = float(current_price)
            profit_target = DEFAULTS['profit_target']
            target_price = current_price * (1 + profit_target)
            progress = min(100, (current_price / target_price) * 100)
            
            self.current_price_label.setText(f"Current Price: {format_price(current_price)}")
            self.target_price_label.setText(f"Target Price: {format_price(target_price)}")
            self.progress_bar.setValue(int(progress))
            
            # Update colors based on progress
            if progress >= 100:
                self.progress_bar.setStyleSheet("""
                    QProgressBar { border: none; border-radius: 5px; background-color: #2d2d2d; }
                    QProgressBar::chunk { border-radius: 5px; background-color: #4CAF50; }
                """)
                self.target_price_label.setStyleSheet("color: #4CAF50;")  # Green when target reached
            else:
                self.progress_bar.setStyleSheet("""
                    QProgressBar { border: none; border-radius: 5px; background-color: #2d2d2d; }
                    QProgressBar::chunk { border-radius: 5px; background-color: #00bcd4; }
                """)
                self.target_price_label.setStyleSheet("color: #e0e0e0;")
            
        except (ValueError, TypeError) as e:
            print(f"Error updating profit target: {e}")
            self.current_price_label.setText("Current Price: N/A")
            self.target_price_label.setText("Target Price: N/A")
            self.progress_bar.setValue(0)

class ModernStockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("StockApp", "StockPro")
        self.current_theme = self.settings.value("Theme", "Dark")
        self.current_ticker = None
        self.watchlist = self.settings.value("Watchlist", [])
        
        self.setWindowTitle("Stoxalotl")
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