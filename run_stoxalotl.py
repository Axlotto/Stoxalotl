#!/usr/bin/env python
"""
Main entry point for Stoxalotl application with initialization checks
"""

import sys
import os
import logging
import traceback
from datetime import datetime

# Set up logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"stoxalotl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logging.info(f"Starting Stoxalotl - log file: {log_file}")

def show_error_dialog(message):
    """Show an error dialog using either Qt or Tkinter"""
    try:
        # Try Qt first
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        QMessageBox.critical(None, "Stoxalotl Error", message)
    except ImportError:
        # Fall back to Tkinter
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Stoxalotl Error", message)
            root.destroy()
        except ImportError:
            # If all GUI toolkits fail, just print to console
            print(f"ERROR: {message}")

def create_essential_directories():
    """Create any essential directories for the application"""
    dirs_to_create = ["logs", "assets"]
    app_dir = os.path.dirname(os.path.abspath(__file__))
    
    for dirname in dirs_to_create:
        dir_path = os.path.join(app_dir, dirname)
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
                logging.info(f"Created directory: {dir_path}")
            except Exception as e:
                logging.error(f"Error creating directory {dirname}: {e}")

if __name__ == "__main__":
    try:
        # Create essential directories first
        create_essential_directories()
        
        # Try to run system checks
        try:
            logging.info("Running system checks...")
            # First try direct import
            try:
                from system_check import run_all_checks
                if not run_all_checks():
                    logging.warning("Some system checks failed. Proceeding anyway...")
            except (ImportError, AttributeError) as e:
                logging.warning(f"Could not run system checks: {e}")
                logging.warning("Continuing without system checks...")
        except Exception as e:
            logging.warning(f"System checks module error: {e}")
            logging.warning("Continuing without system checks...")
        
        # Import and start the application
        try:
            logging.info("Starting main application...")
            try:
                # Try to import directly
                from main import ModernStockApp
                from PySide6.QtWidgets import QApplication
                
                app = QApplication(sys.argv)
                window = ModernStockApp()
                window.show()
                sys.exit(app.exec())
            except ImportError as e:
                error_msg = f"Failed to import application modules: {e}\n\n"
                error_msg += "Please ensure all dependencies are installed:\n"
                error_msg += "pip install PySide6 numpy pandas pyqtgraph requests"
                logging.critical(error_msg)
                show_error_dialog(error_msg)
                sys.exit(1)
        except Exception as e:
            error_msg = f"Error starting application: {e}"
            logging.critical(error_msg)
            logging.critical(traceback.format_exc())
            show_error_dialog(error_msg)
            sys.exit(1)
            
    except Exception as e:
        # Catch any unhandled exceptions during startup
        error_msg = f"Error during application startup: {e}\n\n"
        error_msg += traceback.format_exc()
        logging.critical(error_msg)
        show_error_dialog(f"Critical error during startup: {e}\n\nSee log file for details: {log_file}")
        sys.exit(1)
