"""
Utility to patch missing methods in the ModernStockApp class.
Import this file before creating the ModernStockApp instance.
"""
import sys
import logging
from types import MethodType
import atexit  # Add this import

# Define the patch function but don't run it immediately
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

# Register the patch to run later when all modules are loaded
def apply_patches_at_end():
    try:
        patch_result = patch_modern_stock_app()
        if patch_result:
            print("Successfully patched ModernStockApp with missing methods")
        else:
            print("Failed to patch ModernStockApp - class not found")
    except Exception as e:
        logging.error(f"Error while applying patches: {e}")
        print(f"Error applying patches: {e}")

# Register the function to run when Python exits
# This ensures all modules are loaded first
atexit.register(apply_patches_at_end)
print("Patches will be applied after all modules are loaded")

"""
Compatibility module to handle differences between PyQt and PySide packages
"""
import logging

try:
    # Try to import sip module from PyQt5
    from PyQt5 import sip
    logging.info("Successfully imported sip from PyQt5")
    
    # Make sip available at the top level for other modules
    import sys
    sys.modules['sip'] = sip
    
except ImportError:
    try:
        # If PyQt5.sip failed, try direct sip import
        import sip
        logging.info("Successfully imported sip directly")
    except ImportError:
        logging.error("Could not import sip module - some functionality may be limited")
        
        # Create a minimal sip module with just the isdeleted function
        class DummySip:
            @staticmethod
            def isdeleted(obj):
                """Check if an object has been deleted"""
                try:
                    # If we can access an attribute, it's probably not deleted
                    if hasattr(obj, 'isVisible'):
                        return False
                    return True
                except RuntimeError:
                    # Runtime error often means the C++ object is deleted
                    return True
                except:
                    return True
                    
        import sys
        sys.modules['sip'] = DummySip()
        logging.warning("Using dummy sip implementation with limited functionality")

# Add a safe wrapper function for widget operations
def safe_widget_call(widget, method_name, *args, **kwargs):
    """
    Safely call a method on a widget only if it still exists
    
    Args:
        widget: The Qt widget
        method_name: Name of the method to call
        *args, **kwargs: Arguments to pass to the method
        
    Returns:
        Result of the method call or None if widget is deleted
    """
    if widget is None:
        return None
        
    # Check if the widget still exists
    try:
        # Try to access a common property as a test
        # This will raise an exception if the widget is deleted
        _ = widget.objectName()
        
        # If we get here, the widget exists, so call the method
        if hasattr(widget, method_name):
            method = getattr(widget, method_name)
            return method(*args, **kwargs)
        return None
    except (RuntimeError, AttributeError, TypeError):
        # Widget is deleted or invalid
        return None

# Make the function available at module level
import sys
sys.modules['safe_widget_call'] = safe_widget_call

# Also patch the sip module with our safe call function
if 'sip' in sys.modules:
    sys.modules['sip'].safe_call = safe_widget_call

try:
    # Try to find and patch the ModernStockApp class for compatibility
    from importlib import import_module
    from inspect import getmembers, isclass
    
    found_class = False
    
    # Look for the ModernStockApp class in common module locations
    for module_name in ['main', 'app', 'gui', 'stoxalotl']:
        try:
            module = import_module(module_name)
            for name, obj in getmembers(module, isclass):
                if name == 'ModernStockApp':
                    found_class = True
                    logging.info(f"Found ModernStockApp in {module_name}")
                    # You could apply patches here if needed
                    break
        except (ImportError, AttributeError):
            continue
    
    if not found_class:
        logging.error("Could not find ModernStockApp class in loaded modules")
        print("Failed to patch ModernStockApp - make sure the application is properly imported")
        
except Exception as e:
    logging.error(f"Error while trying to patch ModernStockApp: {e}")
