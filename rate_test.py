"""
Simple utility to test API rate limits and verify our rate limiter implementation
"""
import time
import logging
import yfinance as yf
import requests
import sys
from concurrent.futures import ThreadPoolExecutor
from rate_limiter import execute_yfinance_request, execute_finnhub_request, execute_news_api_request
from config import FINNHUB_API_KEY, FINNHUB_API_URL, NEWS_API_KEY, NEWS_API_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("rate_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def yfinance_test_function(ticker):
    """Function to test yfinance API call"""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1mo")
    return len(hist)

def finnhub_test_function(url, params):
    """Function to test Finnhub API call"""
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def news_api_test_function(url, params):
    """Function to test News API call"""
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def test_yfinance_rate_limit(num_requests=10, tickers=None):
    """Test yfinance rate limiting"""
    if tickers is None:
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"] * 2
    
    logging.info(f"Testing yfinance rate limiting with {num_requests} requests")
    results = []
    start_time = time.time()
    
    for i in range(num_requests):
        ticker = tickers[i % len(tickers)]
        try:
            logging.info(f"Request {i+1}/{num_requests}: Fetching data for {ticker}")
            result = execute_yfinance_request(yfinance_test_function, ticker)
            results.append((ticker, result, True))
            logging.info(f"Request {i+1}/{num_requests}: Success - Got {result} rows for {ticker}")
        except Exception as e:
            results.append((ticker, str(e), False))
            logging.error(f"Request {i+1}/{num_requests}: Failed - {str(e)}")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    logging.info(f"Test completed in {elapsed:.2f} seconds")
    successes = sum(1 for _, _, success in results if success)
    logging.info(f"Success rate: {successes}/{num_requests} ({successes/num_requests*100:.1f}%)")
    logging.info(f"Average time per request: {elapsed/num_requests:.2f} seconds")
    
    return results, elapsed

def test_finnhub_rate_limit(num_requests=5):
    """Test Finnhub rate limiting"""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "FB", "NFLX", "INTC"]
    
    logging.info(f"Testing Finnhub rate limiting with {num_requests} requests")
    results = []
    start_time = time.time()
    
    for i in range(num_requests):
        ticker = tickers[i % len(tickers)]
        try:
            params = {'symbol': ticker, 'token': FINNHUB_API_KEY}
            url = f"{FINNHUB_API_URL}/quote"
            
            logging.info(f"Request {i+1}/{num_requests}: Fetching data for {ticker}")
            result = execute_finnhub_request(finnhub_test_function, url, params)
            results.append((ticker, result, True))
            logging.info(f"Request {i+1}/{num_requests}: Success - Got data for {ticker}")
        except Exception as e:
            results.append((ticker, str(e), False))
            logging.error(f"Request {i+1}/{num_requests}: Failed - {str(e)}")
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    logging.info(f"Test completed in {elapsed:.2f} seconds")
    successes = sum(1 for _, _, success in results if success)
    logging.info(f"Success rate: {successes}/{num_requests} ({successes/num_requests*100:.1f}%)")
    logging.info(f"Average time per request: {elapsed/num_requests:.2f} seconds")
    
    return results, elapsed

def run_all_tests():
    """Run all rate limit tests"""
    logging.info("Starting comprehensive rate limit testing")
    
    logging.info("\n=== YFINANCE RATE LIMITING TEST ===")
    yf_results, yf_time = test_yfinance_rate_limit(num_requests=8)
    
    logging.info("\n=== FINNHUB RATE LIMITING TEST ===")
    fh_results, fh_time = test_finnhub_rate_limit(num_requests=5)
    
    logging.info("\n=== PARALLEL TEST ===")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        yf_future = executor.submit(test_yfinance_rate_limit, 5)
        fh_future = executor.submit(test_finnhub_rate_limit, 3)
        
        yf_parallel_results, _ = yf_future.result()
        fh_parallel_results, _ = fh_future.result()
    
    parallel_time = time.time() - start_time
    
    logging.info(f"\nParallel test completed in {parallel_time:.2f} seconds")
    logging.info(f"YFinance success rate: {sum(1 for _, _, s in yf_parallel_results if s)}/{len(yf_parallel_results)}")
    logging.info(f"Finnhub success rate: {sum(1 for _, _, s in fh_parallel_results if s)}/{len(fh_parallel_results)}")
    
    return {
        "yfinance": {"results": yf_results, "time": yf_time},
        "finnhub": {"results": fh_results, "time": fh_time},
        "parallel": {
            "time": parallel_time,
            "yfinance": yf_parallel_results,
            "finnhub": fh_parallel_results
        }
    }

if __name__ == "__main__":
    print("Starting rate limit tests. This will take some time...")
    results = run_all_tests()
    print("\nTests completed. See rate_test.log for detailed results.")
    print(f"YFinance test: {sum(1 for _, _, s in results['yfinance']['results'] if s)}/{len(results['yfinance']['results'])} successful in {results['yfinance']['time']:.2f}s")
    print(f"Finnhub test: {sum(1 for _, _, s in results['finnhub']['results'] if s)}/{len(results['finnhub']['results'])} successful in {results['finnhub']['time']:.2f}s")
    print(f"Parallel test completed in {results['parallel']['time']:.2f}s")
