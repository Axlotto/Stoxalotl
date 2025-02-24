# workers.py
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from tradingview_ta import TA_Handler, Interval
from typing import Dict, List, Tuple, Optional
import time
import logging
from config import COLORS
import yfinance as yf
class StockWorkerSignals(QObject):
    finished = Signal(dict)  # Processed stock data
    metrics_updated = Signal(list)  # Formatted metrics list
    error = Signal(str)  # Error messages
class StockWorker(QRunnable):
    def __init__(self, ticker: str):
        super().__init__()
        self.signals = StockWorkerSignals()
        self.ticker = ticker
        self._active = True
        self.exchange = "NASDAQ"
        self.screener = "america"
        self.interval = Interval.INTERVAL_1_DAY
        
        # Configure automatic signal connection
        self.setAutoDelete(True)
    def run(self):
        """Main worker execution loop"""
        while self._active:
            try:
                start_time = time.time()
                
                # Get technical analysis data
                analysis = self._get_technical_analysis()
                if not analysis:
                    continue
                
                # Process and emit data
                processed_data = self._process_analysis(analysis)
                self.signals.finished.emit(processed_data)
                self.signals.metrics_updated.emit(processed_data['metrics'])
                
                # Maintain 2-second interval
                elapsed = time.time() - start_time
                sleep_time = max(2.0 - elapsed, 0)
                time.sleep(sleep_time)
                
            except Exception as e:
                self.signals.error.emit(f"Worker error: {str(e)}")
                time.sleep(5)  # Backoff on errors
    def stop(self):
        """Gracefully stop the worker"""
        self._active = False
    def _get_technical_analysis(self) -> Optional[Dict]:
        """Fetch TA data from TradingView"""
        try:
            handler = TA_Handler(
                symbol=self.ticker,
                screener=self.screener,
                exchange=self.exchange,
                interval=self.interval
            )
            return handler.get_analysis()
        except Exception as e:
            self.signals.error.emit(f"TA fetch failed: {str(e)}")
            return None
    def _process_analysis(self, analysis: Dict) -> Dict:
        """Convert raw analysis to processed data"""
        indicators = analysis.indicators
        summary = analysis.summary
        oscillators = analysis.oscillators
        moving_avgs = analysis.moving_averages
        return {
            'current_price': indicators.get("close"),
            'metrics': self._get_metrics(analysis),  # Pass the analysis directly to _get_metrics
            'recommendation': {
                'text': summary.get('RECOMMENDATION', 'N/A'),
                'color': self._get_recommendation_color(summary)
            },
            'technical_indicators': {
                'rsi': self._format_rsi(indicators.get("RSI")),
                'macd': self._format_macd(indicators),
                'stochastic': self._format_stochastic(indicators),
                'moving_averages': {
                    'ema_20': self._format_price(moving_avgs.get("EMA20")),
                    'sma_50': self._format_price(moving_avgs.get("SMA50")),
                    'sma_200': self._format_price(moving_avgs.get("SMA200"))
                }
            }
        }
    def _get_metrics(self, analysis: Dict) -> List[Tuple[str, str, str]]:
        """Convert analysis to metrics format for UI"""
        indicators = analysis.indicators
        summary = analysis.summary
        
        return [
            ("Price", self._format_price(indicators.get("close")), COLORS['text']),
            ("Change", self._get_price_change(indicators), 
             self._get_change_color(indicators)),
            ("Recommendation", summary.get('RECOMMENDATION', 'N/A'), 
             self._get_recommendation_color(summary)),
            ("RSI (14)", self._format_rsi(indicators.get("RSI")), 
             self._get_rsi_color(indicators.get("RSI"))),
            ("Volume", f"{indicators.get('volume', 0):,}", COLORS['text']),
            ("MACD", self._format_macd(indicators), COLORS['text']),
            ("Stochastic", self._format_stochastic(indicators), COLORS['text'])
        ]
    # Formatting helper methods
    def _format_price(self, value: Optional[float]) -> str:
        return f"${value:.2f}" if value is not None else "N/A"
    def _get_price_change(self, indicators: Dict) -> str:
        close = indicators.get("close")
        open_price = indicators.get("open")
        if close and open_price:
            change = close - open_price
            pct_change = (change / open_price) * 100
            return f"{change:+.2f} ({pct_change:+.2f}%)"
        return "N/A"
    def _get_change_color(self, indicators: Dict) -> str:
        close = indicators.get("close")
        open_price = indicators.get("open")
        if close and open_price:
            return COLORS['positive'] if close >= open_price else COLORS['negative']
        return COLORS['text']
    def _get_recommendation_color(self, summary: Dict) -> str:
        rec = summary.get('RECOMMENDATION', '').upper()
        if 'STRONG_BUY' in rec:
            return COLORS['positive']
        if 'STRONG_SELL' in rec:
            return COLORS['negative']
        if 'BUY' in rec:
            return "#90EE90"  # Light green
        if 'SELL' in rec:
            return "#FF6961"  # Light red
        return COLORS['text']
    def _format_rsi(self, rsi: Optional[float]) -> str:
        if rsi is not None:
            strength = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            return f"{rsi:.2f} ({strength})"
        return "N/A"
    def _get_rsi_color(self, rsi: Optional[float]) -> str:
        if rsi is None:
            return COLORS['text']
        return COLORS['negative'] if rsi > 70 else COLORS['positive'] if rsi < 30 else COLORS['text']
    def _format_macd(self, indicators: Dict) -> str:
        macd = indicators.get("MACD.macd")
        signal = indicators.get("MACD.signal")
        hist = indicators.get("MACD.hist")
        if all(v is not None for v in [macd, signal, hist]):
            return f"{macd:.2f}/{signal:.2f} ({hist:+.2f})"
        return "N/A"
    def _format_stochastic(self, indicators: Dict) -> str:
        k = indicators.get("Stoch.K")
        d = indicators.get("Stoch.D")
        if k and d:
            return f"{k:.2f}/{d:.2f}"
        return "N/A"
class WorkerManager:
    def __init__(self):
        self.thread_pool = QThreadPool.globalInstance()
        self.active_workers = {}
    def start_worker(self, ticker: str):
        """Start a new worker for a ticker"""
        if ticker in self.active_workers:
            return
            
        worker = StockWorker(ticker)
        self.active_workers[ticker] = worker
        self.thread_pool.start(worker)
    def stop_worker(self, ticker: str):
        """Stop a running worker"""
        if ticker in self.active_workers:
            worker = self.active_workers.pop(ticker)
            worker.stop()