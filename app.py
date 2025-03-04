# ...existing code...

def _get_stock_metrics(self, ticker):
    """
    Get financial metrics for a stock
    
    Args:
        ticker: Stock symbol
        
    Returns:
        Dict with financial metrics or None if unavailable
    """
    try:
        # Use the API client to fetch financial metrics
        return self.stock_api.get_financial_metrics(ticker)
    except Exception as e:
        logging.error(f"Error fetching stock metrics for {ticker}: {e}")
        
        # Try to use fallback data
        try:
            from fallback import get_fallback_stock_metrics
            logging.info(f"Using fallback metrics data for {ticker}")
            return get_fallback_stock_metrics(ticker)
        except ImportError:
            logging.warning("Fallback module not available")
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

# ...existing code...
