"""
Utility decorators for common patterns
"""
import functools
import logging


def safe_operation(default_return=None, log_errors=True):
    """
    Decorator to safely handle exceptions in operations
    
    Args:
        default_return: Value to return if exception occurs
        log_errors: Whether to log errors (default: True)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger = logging.getLogger(func.__module__)
                    logger.error(f"{func.__name__} error: {e}")
                return default_return
        return wrapper
    return decorator


def retry_operation(max_attempts=3, delay=1.0, exceptions=(Exception,)):
    """
    Decorator to retry operations on failure
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                    continue
            
            # If we get here, all attempts failed
            raise last_exception
        return wrapper
    return decorator


def log_performance(log_level=logging.DEBUG):
    """
    Decorator to log function execution time
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger = logging.getLogger(func.__module__)
                logger.log(log_level, f"{func.__name__} executed in {execution_time:.3f}s")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger = logging.getLogger(func.__module__)
                logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator