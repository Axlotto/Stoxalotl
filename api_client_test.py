"""
Test script to verify Finnhub API integration
Run this script to test the financial data features
"""

import logging
import time
from datetime import datetime
import pandas as pd
from tabulate import tabulate  # Install with: pip install tabulate

# Import fetch_data module
import fetch_data

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_stock_quote():
    """Test getting a stock quote from Finnhub"""
    logging.info("Testing stock quote...")
    try:
        ticker = "AAPL"
        data = fetch_data.get_stock_quote(ticker)
        
        print("\nStock Quote Test:")
        print(f"Ticker: {ticker}")
        print(f"Current Price: ${data.get('c', 'N/A')}")
        print(f"Previous Close: ${data.get('pc', 'N/A')}")
        print(f"Open Price: ${data.get('o', 'N/A')}")
        print(f"High: ${data.get('h', 'N/A')}")
        print(f"Low: ${data.get('l', 'N/A')}")
        
        # Test success if we get current price
        return 'c' in data and data['c'] > 0
    except Exception as e:
        logging.error(f"Stock quote test failed: {e}")
        return False

def test_company_profile():
    """Test getting company profile from Finnhub"""
    logging.info("Testing company profile...")
    try:
        ticker = "MSFT"
        data = fetch_data.get_company_profile(ticker)
        
        print("\nCompany Profile Test:")
        print(f"Ticker: {ticker}")
        print(f"Name: {data.get('name', 'N/A')}")
        print(f"Industry: {data.get('finnhubIndustry', 'N/A')}")
        print(f"Market Cap: ${data.get('marketCapitalization', 'N/A'):,}M")
        print(f"URL: {data.get('weburl', 'N/A')}")
        
        # Test success if we get company name
        return 'name' in data and data['name']
    except Exception as e:
        logging.error(f"Company profile test failed: {e}")
        return False

def test_historical_data():
    """Test getting historical data from Finnhub"""
    logging.info("Testing historical data...")
    try:
        ticker = "GOOG"
        timeframe = "1M"
        
        df = fetch_data.get_historical_dataframe(ticker, timeframe)
        
        print("\nHistorical Data Test:")
        print(f"Ticker: {ticker}")
        print(f"Timeframe: {timeframe}")
        print(f"Data points: {len(df)}")
        print("Recent data:")
        
        # Show the last 5 rows
        if not df.empty:
            print(tabulate(df.tail(5), headers='keys', tablefmt='pretty', floatfmt=".2f"))
        
        # Test success if we get some data
        return not df.empty and len(df) > 0
    except Exception as e:
        logging.error(f"Historical data test failed: {e}")
        return False

def test_stock_metrics():
    """Test getting financial metrics from Finnhub"""
    logging.info("Testing stock metrics...")
    try:
        ticker = "NVDA"
        data = fetch_data.get_stock_metrics(ticker)
        
        print("\nStock Metrics Test:")
        print(f"Ticker: {ticker}")
        
        # Extract some key metrics
        metrics = data.get('metric', {})
        pe_ratio = metrics.get('peBasicExclExtraTTM', 'N/A')
        eps = metrics.get('epsBasicExclExtraItemsTTM', 'N/A')
        dividend_yield = metrics.get('dividendYieldIndicatedAnnual', 'N/A')
        
        print(f"P/E Ratio (TTM): {pe_ratio}")
        print(f"EPS (TTM): ${eps}")
        print(f"Dividend Yield: {dividend_yield}%")
        
        # Test success if we get metrics
        return 'metric' in data
    except Exception as e:
        logging.error(f"Stock metrics test failed: {e}")
        return False

def test_stock_news():
    """Test getting stock news from Finnhub"""
    logging.info("Testing stock news...")
    try:
        ticker = "TSLA"
        from_date = (datetime.now().date() - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
        
        news = fetch_data.get_ticker_news(ticker, from_date, limit=3)
        
        print("\nStock News Test:")
        print(f"Ticker: {ticker}")
        print(f"From date: {from_date}")
        print(f"Articles found: {len(news)}")
        
        for i, article in enumerate(news[:3], 1):
            print(f"\nArticle {i}:")
            print(f"Headline: {article.get('headline', 'N/A')}")
            print(f"Source: {article.get('source', 'N/A')}")
            print(f"Date: {article.get('datetime', 'N/A')}")
        
        # Test success if we get some news
        return len(news) > 0
    except Exception as e:
        logging.error(f"Stock news test failed: {e}")
        return False

def run_tests():
    """Run all tests and report results"""
    print("===== FINNHUB API INTEGRATION TESTS =====")
    
    tests = [
        test_stock_quote,
        test_company_profile,
        test_historical_data,
        test_stock_metrics,
        test_stock_news
    ]
    
    results = []
    all_passed = True
    
    for test in tests:
        try:
            # Add delay between tests to avoid rate limiting
            time.sleep(1)
            
            result = test()
            results.append((test.__name__, "✅ PASS" if result else "❌ FAIL"))
            if not result:
                all_passed = False
        except Exception as e:
            results.append((test.__name__, f"❌ ERROR: {str(e)}"))
            all_passed = False
    
    print("\n===== TEST RESULTS =====")
    for name, result in results:
        print(f"{name}: {result}")
    
    print(f"\nOverall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

if __name__ == "__main__":
    run_tests()
