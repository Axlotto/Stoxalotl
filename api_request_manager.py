import time
import threading
import queue
import logging
from typing import Any, Callable, Dict, Tuple

class ApiRequestManager:
    """
    Manages API requests to prevent rate limiting by queuing requests
    and processing them with appropriate delays.
    """
    
    def __init__(self, min_request_interval: float = 10.0):  # Increased to 10 seconds
        """
        Initialize the API request manager.
        
        Args:
            min_request_interval: Minimum time in seconds between requests
        """
        self.min_request_interval = min_request_interval
        self.last_request_time = 0
        self.request_queue = queue.Queue()
        self.lock = threading.Lock()
        self.process_semaphore = threading.Semaphore(1)  # Allow only one request at a time
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logging.info(f"API Request Manager initialized with {min_request_interval}s interval")
    
    def queue_request(self, func: Callable, *args, **kwargs) -> Any:
        """
        Queue a request to be processed when rate limits allow.
        
        Args:
            func: Function to call
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function call
        """
        request_id = id(func) + id(args) + id(tuple(sorted(kwargs.items())))
        logging.info(f"Queuing API request {request_id}")
        
        result_event = threading.Event()
        result_container = {"result": None, "error": None}
        
        self.request_queue.put((func, args, kwargs, result_event, result_container, request_id))
        
        # Wait for the result
        result_event.wait()
        
        if result_container["error"]:
            raise result_container["error"]
        
        return result_container["result"]
    
    def _process_queue(self) -> None:
        """Process queued requests with appropriate delays."""
        while True:
            try:
                # Get a request from the queue
                func, args, kwargs, result_event, result_container, request_id = self.request_queue.get()
                
                # Use semaphore to ensure only one request at a time
                with self.process_semaphore:
                    # Enforce minimum time between requests
                    with self.lock:
                        current_time = time.time()
                        elapsed = current_time - self.last_request_time
                        
                        if elapsed < self.min_request_interval:
                            wait_time = self.min_request_interval - elapsed
                            logging.info(f"Waiting {wait_time:.2f}s before processing request {request_id}")
                            time.sleep(wait_time)
                        
                        # Execute the request
                        try:
                            logging.info(f"Processing API request {request_id}")
                            result_container["result"] = func(*args, **kwargs)
                        except Exception as e:
                            logging.error(f"Error in API request {request_id}: {e}")
                            result_container["error"] = e
                        
                        # Update last request time after processing
                        self.last_request_time = time.time()
                
                # Signal completion
                result_event.set()
                
                # Mark the task as done in the queue
                self.request_queue.task_done()
                
                # Add an extra delay after each request to be extra safe
                time.sleep(2.0)
                
            except Exception as e:
                logging.error(f"Error in request queue processing: {e}")
                time.sleep(1)  # Avoid tight loop in case of persistent errors
