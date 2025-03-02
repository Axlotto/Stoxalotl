from datetime import datetime, timedelta
import time

class RequestCounter:
    def __init__(self):
        self.api_count = 0
        self.cache_count = 0
        self.news_api_count = 0
        self.start_time = time.time()

    def increment_api(self):
        self.api_count += 1

    def increment_cache(self):
        self.cache_count += 1

    def increment(self, counter_name):
        if counter_name == 'news_api':
            self.news_api_count += 1

    def get_counts(self):
        return {
            'api': self.api_count,
            'cache': self.cache_count,
            'news_api': self.news_api_count,
            'total': self.api_count + self.cache_count + self.news_api_count
        }

    def time_since_reset(self):
        return timedelta(seconds=int(time.time() - self.start_time))
