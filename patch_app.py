"""
Emergency patch for ModernStockApp
Run this before importing your main application modules
"""
import sys
import logging
from types import MethodType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_missing_methods(app_instance):
    """Add missing methods directly to a ModernStockApp instance"""
    def _get_stock_metrics(self, ticker):
        """Emergency patched method to get stock metrics"""
        try:
            if hasattr(self, 'stock_api') and hasattr(self.stock_api, 'get_financial_metrics'):
                return self.stock_api.get_financial_metrics(ticker)
            logging.warning(f"stock_api.get_financial_metrics not available for {ticker}")
        except Exception as e:
            logging.error(f"Error in patched _get_stock_metrics for {ticker}: {e}")
        
        # Return default structure
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
    
    # Add the method directly to the instance
    app_instance._get_stock_metrics = MethodType(_get_stock_metrics, app_instance)
    logging.info(f"Added missing _get_stock_metrics method to {app_instance}")
    return app_instance

# Export a function that can be called from anywhere
def patch_running_app():
    """Find and patch any running ModernStockApp instances"""
    patched = 0
    for obj_id, obj in list(globals().items()):
        if obj_id != "app" and obj_id[0] != "_" and hasattr(obj, "__class__") and "ModernStockApp" in str(obj.__class__):
            add_missing_methods(obj)
            patched += 1
    
    # Also look in modules
    for name, module in list(sys.modules.items()):
        if hasattr(module, "app") and hasattr(module.app, "__class__") and "ModernStockApp" in str(module.app.__class__):
            add_missing_methods(module.app)
            patched += 1
    
    logging.info(f"Patched {patched} ModernStockApp instances")
    return patched > 0
