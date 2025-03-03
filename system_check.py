"""
System check module to verify proper setup before application starts
"""

import os
import sys
import logging
import importlib
import platform
import traceback

# Configure logging
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_check.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    logging.info(f"Python version: {platform.python_version()}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        logging.error("Python version 3.8+ is required")
        return False
    
    return True

def check_dependencies():
    """Check if all required Python packages are installed"""
    required_packages = [
        "PySide6",
        "numpy",
        "pandas",
        "pyqtgraph",
        "requests",
        "ollama",
        "tradingview_ta"
    ]
    
    missing = []
    version_issues = []
    
    for package in required_packages:
        try:
            module = importlib.import_module(package)
            version = getattr(module, "__version__", "unknown")
            logging.info(f"Found {package} (version: {version})")
            
            # Check specific version requirements
            if package == "numpy" and version.startswith("1.24"):
                version_issues.append(f"numpy {version} may have compatibility issues with pyqtgraph")
                
        except ImportError:
            missing.append(package)
            logging.error(f"Missing required package: {package}")
    
    if missing:
        logging.error(f"Missing required packages: {', '.join(missing)}")
        return False
        
    for issue in version_issues:
        logging.warning(issue)
        
    return True

def check_api_keys():
    """Check if API keys are configured properly"""
    try:
        from config import FINNHUB_API_KEY, NEWS_API_KEY
        
        issues = []
        
        if not FINNHUB_API_KEY or FINNHUB_API_KEY == "demo_key" or FINNHUB_API_KEY == "YOUR_KEY_HERE":
            issues.append("Finnhub API key is not configured properly")
            
        if not NEWS_API_KEY or NEWS_API_KEY == "YOUR_KEY_HERE":
            issues.append("News API key is not configured properly")
        
        for issue in issues:
            logging.warning(issue)
            
        if issues:
            logging.warning("API keys are missing or using placeholders. Some features may not work.")
            
    except ImportError as e:
        logging.error(f"Could not import config file to check API keys: {e}")
        return False
        
    return True

def check_directories():
    """Check if required directories exist"""
    required_dirs = [
        "assets",
        "logs"
    ]
    
    app_dir = os.path.dirname(os.path.abspath(__file__))
    missing = []
    
    for dirname in required_dirs:
        path = os.path.join(app_dir, dirname)
        if not os.path.exists(path):
            missing.append(dirname)
            logging.warning(f"Required directory is missing: {dirname}")
            # Create the directory
            try:
                os.makedirs(path)
                logging.info(f"Created directory: {path}")
            except Exception as e:
                logging.error(f"Could not create directory {dirname}: {e}")
    
    return not missing

def create_dummy_files():
    """Create necessary placeholder files"""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(app_dir, "assets")
    
    # Create a dummy icon if it doesn't exist
    icon_path = os.path.join(assets_dir, "Axlotto transparent.ico")
    if not os.path.exists(icon_path):
        try:
            # Create an empty file as placeholder
            with open(icon_path, 'wb') as f:
                f.write(b'')
            logging.info(f"Created placeholder icon at {icon_path}")
        except Exception as e:
            logging.error(f"Could not create placeholder icon: {e}")

def run_all_checks():
    """Run all system checks"""
    logging.info("Starting system checks")
    
    all_passed = True
    
    checks = [
        ("Python version", check_python_version),
        ("Dependencies", check_dependencies),
        ("API keys", check_api_keys),
        ("Directories", check_directories),
    ]
    
    for name, check_func in checks:
        try:
            result = check_func()
            if not result:
                all_passed = False
                logging.warning(f"Check failed: {name}")
            else:
                logging.info(f"Check passed: {name}")
        except Exception as e:
            all_passed = False
            logging.error(f"Error during check {name}: {e}")
            logging.error(traceback.format_exc())
    
    # Create dummy files even if some checks fail
    try:
        create_dummy_files()
    except Exception as e:
        logging.error(f"Error creating dummy files: {e}")
    
    if all_passed:
        logging.info("All system checks passed!")
        return True
    else:
        logging.warning("Some system checks failed. See log for details.")
        return False

# Ensure the function gets executed if run directly
if __name__ == "__main__":
    run_all_checks()
