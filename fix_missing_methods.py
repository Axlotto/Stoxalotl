"""
Utility to patch missing methods in the ModernStockApp class.
Import this file before creating the ModernStockApp instance.
"""
import sys
import logging
from types import MethodType

def patch_modern_stock_app():
    """
    Find the ModernStockApp class and add missing methods
    """
    # Find the module containing ModernStockApp
    app_module = None
    for name, module in sys.modules.items():
        if hasattr(module, 'ModernStockApp'):
            app_module = module
            break
    
    if not app_module:
        logging.error("Could not find ModernStockApp class in loaded modules")
        return False
    
    # Get the class
    ModernStockApp = app_module.ModernStockApp
    
    # Define the missing method
    def _get_stock_metrics(self, ticker):
        """Get financial metrics for a stock"""
        try:
            # Use the API client to fetch financial metrics
            return self.stock_api.get_financial_metrics(ticker)
        except Exception as e:
            logging.error(f"Error fetching stock metrics for {ticker}: {e}")
            
            # Return a minimal fallback structure
            return {
                "metric": {
                    "peNormalizedAnnual": None,
                    "peTTM": None,
                    "pbAnnual": None,
                    "psTTM": None,
                    "dividendYieldIndicatedAnnual": None,
                    "52WeekHigh": None,
                    "52WeekLow": None
                }
            }
    
    # Add the method to the class if it doesn't exist
    if not hasattr(ModernStockApp, '_get_stock_metrics'):
        setattr(ModernStockApp, '_get_stock_metrics', _get_stock_metrics)
        logging.info("Added missing _get_stock_metrics method to ModernStockApp")
    
    return True

# Apply the patch automatically when this module is imported
patch_applied = patch_modern_stock_app()
if patch_applied:
    print("Successfully patched ModernStockApp with missing methods")
else:
    print("Failed to patch ModernStockApp - make sure the application is properly imported")
