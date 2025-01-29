"""A rate limiter decorator for Python functions.
"""

from functools import wraps
import time
from typing import Dict


class RateLimiter:
    # Class-level dict to store last call times for each key
    _last_called: Dict[str, float] = {}

    @classmethod
    def limit(cls, key, interval=1):
        """
        Decorator that ensures at least `interval` seconds between function calls
        that share the same key.

        Args:
            key (str): Identifier for the rate limit group
            interval (float): Minimum time in seconds between calls
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Get the last called time for this key, defaulting to 0
                last_time = cls._last_called.get(key, 0)

                # Calculate time elapsed since last call
                elapsed = time.time() - last_time

                # If not enough time has elapsed, sleep for the remaining time
                if elapsed < interval:
                    time.sleep(interval - elapsed)

                # Update the last called time for this key
                cls._last_called[key] = time.time()

                # Call the original function
                return func(*args, **kwargs)

            return wrapper

        return decorator
