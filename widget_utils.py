"""
Utility functions for safer widget handling
"""
import logging

def safe_status_update(status_bar, message, timeout=0):
    """
    Safely update a status bar with error handling
    
    Args:
        status_bar: The status bar widget
        message: Message to display
        timeout: Time to display the message (0 = no timeout)
    """
    if status_bar is None:
        return
        
    try:
        status_bar.showMessage(message, timeout)
    except Exception as e:
        logging.debug(f"Could not update status bar: {e}")
        # Don't propagate the exception - failing to update status is not critical

def safe_set_text(widget, text):
    """
    Safely set text on a widget with error handling
    
    Args:
        widget: The widget to update
        text: Text to set
    """
    if widget is None:
        return
        
    try:
        widget.setText(text)
    except Exception as e:
        logging.debug(f"Could not set text: {e}")
        # Don't propagate the exception
