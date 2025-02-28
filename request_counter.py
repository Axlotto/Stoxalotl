from datetime import datetime

class RequestCounter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.api_count = 0
        self.cache_count = 0
        self.last_reset = datetime.now()

    def increment_api(self):
        self.api_count += 1

    def increment_cache(self):
        self.cache_count += 1

    def get_counts(self):
        return {
            'api': self.api_count,
            'cache': self.cache_count,
            'total': self.api_count + self.cache_count
        }

    def time_since_reset(self):
        return datetime.now() - self.last_reset
