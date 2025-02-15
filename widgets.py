# widgets.py
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QLabel, QStyle, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QTextEdit, QWidget, QSizePolicy
)
from PySide6.QtGui import QFont, QColor, QPainter, QPen
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget, BarGraphItem, DateAxisItem, InfiniteLine, TextItem
import yfinance as yf
import numpy as np
from config import COLORS, FONT_FAMILY, FONT_SIZES

# Custom color for mid-range values
YELLOW = "#FFEB3B"

class StockOverview(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("overview")
        self.setFixedHeight(150)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Ticker Symbol
        self.ticker = QLabel("")
        self.ticker.setFont(QFont(FONT_FAMILY, 28, QFont.Bold))
        self.ticker.setStyleSheet(f"color: {COLORS['primary']};")
        
        # Price and Change
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

class KeyMetrics(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("metrics")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title = QLabel("Key Metrics")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        
        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(8)
        self.grid.setHorizontalSpacing(16)
        
        layout.addWidget(title)
        layout.addLayout(self.grid)
        layout.addStretch()

    def update_metrics(self, metrics):
        # Clear existing metrics
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().deleteLater()
            
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
    def __init__(self):
        super().__init__()
        self.setObjectName("recommendation")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title = QLabel("AI Recommendations")
        title.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        
        self.grid = QGridLayout()
        self.grid.setVerticalSpacing(8)
        self.grid.setHorizontalSpacing(16)
        
        layout.addWidget(title)
        layout.addLayout(self.grid)
        layout.addStretch()

    def update_recommendations(self, recs):
        # Clear previous entries
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().deleteLater()
            
        row = 0
        for option in ["Buy", "Hold", "Sell"]:
            lbl = QLabel(option)
            lbl.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"]))
            lbl.setStyleSheet(f"color: {COLORS['text-secondary']}")
            
            percentage = recs.get(option, "N/A")
            if isinstance(percentage, int):
                text = f"{percentage}%"
                if percentage <= 35:
                    color = COLORS['negative']
                elif percentage <= 65:
                    color = YELLOW
                else:
                    color = COLORS['positive']
            else:
                text = str(percentage)
                color = COLORS['text']
                
            val = QLabel(text)
            val.setFont(QFont(FONT_FAMILY, FONT_SIZES["body"], QFont.Medium))
            val.setStyleSheet(f"color: {color}")
            
            self.grid.addWidget(lbl, row, 0)
            self.grid.addWidget(val, row, 1)
            row += 1

class AnalysisCard(QFrame):
    clicked = Signal(str, str, str)  # title, content, color

    def __init__(self, title):
        super().__init__()
        self.setObjectName("analysisCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont(FONT_FAMILY, FONT_SIZES["header"], QFont.DemiBold))
        
        self.btn_maximize = QPushButton()
        self.btn_maximize.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.btn_maximize.setFlat(True)
        self.btn_maximize.clicked.connect(self._on_maximize)
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_maximize)
        
        # Content
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

    def _on_maximize(self):
        self.clicked.emit(
            self.title_label.text(),
            self.content.toPlainText(),
            self.content.textColor().name()
        )

class StockChart(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        
        # Create graphics layout
        self.grid = GraphicsLayoutWidget()
        layout.addWidget(self.grid)
        
        # Price plot
        self.price_plot = self.grid.addPlot(row=0, col=0, axisItems={'bottom': DateAxisItem()})
        self.price_plot.showGrid(x=True, y=True, alpha=0.3)
        self.price_plot.setLabel('left', 'Price', units='$')
        
        # Volume plot
        self.volume_plot = self.grid.addPlot(row=1, col=0)
        self.volume_plot.showGrid(x=True, y=True, alpha=0.3)
        self.volume_plot.setLabel('left', 'Volume')
        
        # Crosshair
        self.crosshair_v = InfiniteLine(angle=90, pen=pg.mkPen(COLORS['text'], style=Qt.DashLine))
        self.crosshair_h = InfiniteLine(angle=0, pen=pg.mkPen(COLORS['text'], style=Qt.DashLine))
        self.price_plot.addItem(self.crosshair_v)
        self.price_plot.addItem(self.crosshair_h)
        
        # Tracking text
        self.tracking_text = TextItem(anchor=(0, 1), fill=pg.mkColor(COLORS['surface']))
        self.price_plot.addItem(self.tracking_text)
        
        # Link axes
        self.volume_plot.setXLink(self.price_plot)
        self.grid.ci.layout.setRowPreferredHeight(0, 300)
        self.grid.ci.layout.setRowPreferredHeight(1, 100)
        self.grid.ci.layout.setSpacing(40)

    def update_chart(self, ticker):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")
            
            if hist.empty:
                return
                
            # Prepare candlestick data
            dates = hist.index.view(np.int64) // 10**9
            candlestick_data = np.zeros(len(hist), dtype=[
                ('time', np.int64), ('open', float), 
                ('close', float), ('low', float), ('high', float)
            ])
            candlestick_data['time'] = dates
            for col in ['Open', 'Close', 'Low', 'High']:
                candlestick_data[col.lower()] = hist[col].values
                
            # Clear previous items
            self.price_plot.clear()
            self.volume_plot.clear()
            
            # Plot candlesticks
            candles = pg.CandlestickItem(candlestick_data)
            self.price_plot.addItem(candles)
            
            # Plot volume
            colors = [COLORS['positive'] if c >= o else COLORS['negative'] 
                     for c, o in zip(hist['Close'], hist['Open'])]
            volume_bars = BarGraphItem(
                x=dates, height=hist['Volume'], width=86400*0.8,
                brushes=colors
            )
            self.volume_plot.addItem(volume_bars)
            
            # Add moving averages
            for period, color in [(20, COLORS['accent']), (50, COLORS['primary'])]:
                ma = hist['Close'].rolling(period).mean()
                self.price_plot.plot(dates, ma, pen=pg.mkPen(color, width=1.5))
                
            self.price_plot.autoRange()
            
        except Exception as e:
            print(f"Chart error: {e}")

    def mouseMoveEvent(self, event):
        pos = self.price_plot.vb.mapSceneToView(event.pos())
        self.crosshair_v.setPos(pos.x())
        self.crosshair_h.setPos(pos.y())
        
        # Update tracking text
        if hasattr(self, 'candles') and self.candles.data is not None:
            # ... (remaining crosshair tracking code)