import time
import threading
from collections import deque
import logging
from typing import Any, Callable, Dict, List, Optional
import requests

# Import from config to ensure consistency
from config import FINNHUB_KEY, NEWS_API_KEY, NEWS_API_URL, OLLAMA_MODEL

class RateLimiter:
    """
    Advanced rate limiter that implements token bucket algorithm
    to manage API requests and prevent hitting rate limits.
    """
    
    def __init__(self, max_rate=1.0, burst_limit=5, 
                 wait_on_limit=True, name="API"):
        """
        Initialize rate limiter with appropriate limits.
        
        Args:
            max_rate (float): Maximum requests per second (default: 1)
            burst_limit (int): Maximum burst of requests allowed (default: 5)
            wait_on_limit (bool): Whether to wait when limited (True) or raise error (False)
            name (str): Name identifier for this limiter for logging purposes
        """
        self.max_rate = max_rate  # Max requests per second
        self.burst_limit = burst_limit  # Max token bucket size
        self.wait_on_limit = wait_on_limit  # Whether to wait or raise an exception
        self.name = name  # Name for logging
        
        # Internal state
        self.tokens = burst_limit  # Initial tokens (full bucket)
        self.last_refill = time.time()  # Last token refill timestamp
        self.lock = threading.RLock()  # Lock for thread safety
        self.waiters = 0  # Count of waiting requests
        
        # Statistics
        self.requests_made = 0
        self.requests_limited = 0
        self.total_wait_time = 0
        
        logging.info(f"Rate limiter initialized for {name}: {max_rate}/sec, burst={burst_limit}")
    
    def _refill_tokens(self):
        """Refill tokens based on time elapsed since last refill."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.max_rate
        
        if new_tokens > 0:
            self.tokens = min(self.burst_limit, self.tokens + new_tokens)
            self.last_refill = now
    
    def acquire(self, num_tokens=1):
        """
        Acquire tokens from the bucket. If not enough tokens are available,
        either wait or raise an exception depending on configuration.
        
        Args:
            num_tokens (int): Number of tokens to acquire (default: 1)
            
        Returns:
            float: Time spent waiting (if any)
            
        Raises:
            RuntimeError: If wait_on_limit=False and no tokens available
        """
        with self.lock:
            self.requests_made += 1
            self._refill_tokens()
            
            wait_time = 0
            
            # If not enough tokens, calculate wait time or raise error
            if self.tokens < num_tokens:
                required_tokens = num_tokens - self.tokens
                wait_time = required_tokens / self.max_rate
                
                if not self.wait_on_limit:
                    self.requests_limited += 1
                    raise RuntimeError(
                        f"{self.name} rate limit reached. "
                        f"Need {required_tokens} more tokens, "
                        f"would need to wait {wait_time:.2f}s"
                    )
                
                self.requests_limited += 1
                self.waiters += 1
                
                logging.warning(
                    f"{self.name} rate limited: waiting {wait_time:.2f}s "
                    f"for {required_tokens:.2f} tokens"
                )
                
                # Wait for tokens to refill
                time.sleep(wait_time)
                
                # Tokens should be available now
                self._refill_tokens()
                self.waiters -= 1
            
            # Consume tokens
            self.tokens -= num_tokens
            self.total_wait_time += wait_time
            
            return wait_time
    
    def get_stats(self):
        """Get statistics about rate limiter usage."""
        with self.lock:
            return {
                'requests_made': self.requests_made,
                'requests_limited': self.requests_limited,
                'total_wait_time': self.total_wait_time,
                'current_tokens': self.tokens,
                'waiters': self.waiters,
                'average_wait': (
                    self.total_wait_time / self.requests_limited 
                    if self.requests_limited > 0 else 0
                )
            }
    
    def __str__(self):
        stats = self.get_stats()
        return (
            f"{self.name} RateLimiter: {self.max_rate}/sec, "
            f"burst={self.burst_limit}, "
            f"requests={stats['requests_made']}, "
            f"limited={stats['requests_limited']}"
        )

class APIRequestQueue:
    """
    Manages a queue of API requests to ensure they're processed
    according to rate limits and priorities.
    """
    
    def __init__(self, rate_limiter, max_queue_size=100, 
                 workers=1, batch_size=1):
        """
        Initialize API request queue with a rate limiter.
        
        Args:
            rate_limiter (RateLimiter): Rate limiter to use
            max_queue_size (int): Maximum size of request queue
            workers (int): Number of worker threads
            batch_size (int): Number of requests to process in batch
        """
        self.rate_limiter = rate_limiter
        self.max_queue_size = max_queue_size
        self.workers = workers
        self.batch_size = batch_size
        
        self.queue = deque()
        self.lock = threading.RLock()
        self.not_empty = threading.Condition(self.lock)
        self.not_full = threading.Condition(self.lock)
        self.all_done = threading.Event()
        
        self.threads = []
        self.running = True
        
        # Start worker threads
        for i in range(workers):
            thread = threading.Thread(
                target=self._worker,
                name=f"{rate_limiter.name}Worker-{i+1}"
            )
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
    
    def _worker(self):
        """Worker thread that processes queued requests."""
        while self.running:
            request = None
            with self.lock:
                # Wait for queue to have items
                while len(self.queue) == 0 and self.running:
                    self.not_empty.wait(timeout=1.0)
                    
                if not self.running:
                    break
                    
                # Get item from queue
                if len(self.queue) > 0:
                    request = self.queue.popleft()
                    self.not_full.notify()
            
            # Process request outside lock
            if request:
                func, args, kwargs, result_event, result_container = request
                try:
                    # Apply rate limiting
                    wait_time = self.rate_limiter.acquire()
                    
                    if wait_time > 0:
                        logging.info(f"Request waited {wait_time:.2f}s due to rate limiting")
                    
                    # Execute the request
                    result = func(*args, **kwargs)
                    result_container['result'] = result
                    
                except Exception as e:
                    result_container['error'] = e
                    logging.error(f"Error executing queued request: {str(e)}")
                
                # Signal completion
                result_event.set()
    
    def execute(self, func, *args, **kwargs):
        """
        Queue a function for execution with rate limiting.
        
        Args:
            func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result of function call
            
        Raises:
            Exception: Any exception the function raised
        """
        result_event = threading.Event()
        result_container = {'result': None, 'error': None}
        
        with self.lock:
            # Wait for space in the queue
            while len(self.queue) >= self.max_queue_size and self.running:
                self.not_full.wait(timeout=1.0)
                
            if not self.running:
                raise RuntimeError("API request queue is shutting down")
                
            # Add to queue
            self.queue.append((func, args, kwargs, result_event, result_container))
            self.not_empty.notify()
        
        # Wait for result
        result_event.wait()
        
        # Check if there was an error
        if result_container['error']:
            raise result_container['error']
            
        return result_container['result']
    
    def shutdown(self):
        """Shutdown the queue and worker threads."""
        self.running = False
        
        with self.lock:
            self.not_empty.notify_all()
            self.not_full.notify_all()
        
        for thread in self.threads:
            thread.join(timeout=2.0)
            
        logging.info(f"API request queue shutdown complete, {len(self.queue)} requests remained in queue")


# Global rate limiters and request queues
finnhub_limiter = RateLimiter(
    max_rate=0.5,  # Max 1 per 2 seconds (conservative)
    burst_limit=3,
    name="Finnhub"
)

news_api_limiter = RateLimiter(
    max_rate=0.2,  # Max 1 per 5 seconds (conservative)
    burst_limit=2,
    name="NewsAPI"
)

ollama_limiter = RateLimiter(
    max_rate=0.33,  # Max 1 per 3 seconds
    burst_limit=1,
    name="Ollama"
)

# Create request queues
finnhub_queue = APIRequestQueue(finnhub_limiter, workers=1)
news_api_queue = APIRequestQueue(news_api_limiter, workers=1)
ollama_queue = APIRequestQueue(ollama_limiter, workers=1)

def get_rate_limiter_stats():
    """Get stats from all rate limiters for display."""
    return {
        "finnhub": finnhub_limiter.get_stats(),
        "news_api": news_api_limiter.get_stats(),
        "ollama": ollama_limiter.get_stats()
    }

# Shutdown function to cleanly close all queues
def shutdown_all():
    finnhub_queue.shutdown()
    news_api_queue.shutdown()
    ollama_queue.shutdown()
    logging.info("All API request queues have been shut down")

# Helper utility functions for common operations
def execute_finnhub_request(func, *args, **kwargs):
    """Execute a Finnhub API request with proper rate limiting."""
    return finnhub_queue.execute(func, *args, **kwargs)

def execute_news_api_request(func, *args, **kwargs):
    """Execute a News API request with proper rate limiting."""
    return news_api_queue.execute(func, *args, **kwargs)

def execute_ollama_request(func, *args, **kwargs):
    """Execute an Ollama API request with proper rate limiting."""
    return ollama_queue.execute(func, *args, **kwargs)
