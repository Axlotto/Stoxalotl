import yfinance as yf
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_yfinance_data(ticker="AAPL", period="3mo", interval="1d"):
    """Test if we can successfully fetch data using yfinance"""
    try:
        logging.info(f"Testing yfinance data fetch for {ticker}, period={period}, interval={interval}")
        
        # Create ticker object
        stock = yf.Ticker(ticker)
        
        # Get history
        logging.info("Fetching history...")
        hist = stock.history(period=period, interval=interval)
        
        # Check if data is empty
        if hist.empty:
            logging.error(f"No data returned for {ticker}")
            return False
            
        # Check data shape and columns
        logging.info(f"Data shape: {hist.shape}")
        logging.info(f"Data columns: {hist.columns.tolist()}")
        
        # Check if required columns exist
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_columns = [col for col in required_columns if col not in hist.columns]
        if missing_columns:
            logging.error(f"Missing required columns: {missing_columns}")
            return False
            
        # Check for NaN values
        nan_counts = hist.isna().sum()
        if nan_counts.sum() > 0:
            logging.warning(f"Found NaN values: {nan_counts}")
            
        # Display first few rows
        logging.info("First 5 rows of data:")
        logging.info(hist.head())
        
        # Check data types
        logging.info("Data types:")
        logging.info(hist.dtypes)
        
        # Check index type (should be DatetimeIndex)
        logging.info(f"Index type: {type(hist.index)}")
        
        # Success message
        logging.info(f"Successfully fetched {len(hist)} data points for {ticker}")
        return True
        
    except Exception as e:
        logging.error(f"Error testing yfinance: {str(e)}")
        return False

if __name__ == "__main__":
    # Test with a few different tickers and timeframes
    tickers_to_test = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    periods_to_test = ["1d", "5d", "1mo", "3mo"]
    
    success_count = 0
    total_tests = 0
    
    for ticker in tickers_to_test:
        for period in periods_to_test:
            total_tests += 1
            if test_yfinance_data(ticker, period):
                success_count += 1
                
    logging.info(f"Test results: {success_count}/{total_tests} tests passed")
