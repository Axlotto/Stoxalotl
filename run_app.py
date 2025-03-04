"""
Alternative entry point that handles patching properly
"""
import sys
import logging
from types import MethodType

# Configure logging
logging.basicConfig(level=logging.INFO)

# First, import the main module (don't run it yet)
import main

# Now define our patch method
def patch_missing_methods():
    """Add missing methods to ModernStockApp class"""
    if hasattr(main, 'ModernStockApp'):
        # Define the missing method
        def _get_stock_metrics(self, ticker):
            """Get financial metrics for a stock"""
            try:
                if hasattr(self, 'stock_api'):
                    return self.stock_api.get_financial_metrics(ticker)
                logging.error("Stock API not available")
                raise ValueError("Stock API not available")
            except Exception as e:
                logging.error(f"Error getting metrics for {ticker}: {e}")
                return {
                    "metric": {
                        "peNormalizedAnnual": 0,
                        "peTTM": 0,
                        "pbAnnual": 0,
                        "psTTM": 0,
                        "dividendYieldIndicatedAnnual": 0,
                        "52WeekHigh": 0,
                        "52WeekLow": 0
                    }
                }
        
        # Only add the method if it doesn't exist
        if not hasattr(main.ModernStockApp, '_get_stock_metrics'):
            main.ModernStockApp._get_stock_metrics = _get_stock_metrics
            logging.info("Successfully added missing _get_stock_metrics method")
            return True
    else:
        logging.error("ModernStockApp class not found in main module")
    return False

# Run the patching
if patch_missing_methods():
    # Run the application
    from main import QApplication, ModernStockApp
    
    app = QApplication(sys.argv)
    window = ModernStockApp()
    window.show()
    sys.exit(app.exec())
else:
    print("Failed to patch ModernStockApp, cannot continue")
    sys.exit(1)
