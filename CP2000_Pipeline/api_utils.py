"""
API Utility Functions
Resilient API call wrapper with exponential backoff and retry logic

Based on TRA_API parser_utils.py pattern for production-grade reliability.
Handles quota errors, rate limiting, network issues, and timeouts.

Author: Hemalatha Yalamanchi
Created: October 2025
Version: 1.0
"""

import time
import logging
from typing import Callable, Any, Optional, List, Tuple
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)


def run_resiliently(
    func: Callable,
    *args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[type, ...]] = None,
    retryable_status_codes: Optional[List[int]] = None,
    rate_limit_delay: float = 0.0,
    **kwargs
) -> Any:
    """
    Execute a function with exponential backoff retry logic.
    
    This wrapper handles transient failures gracefully with automatic retry,
    making API calls resilient to quota limits, rate limiting, and network issues.
    
    Args:
        func: Function to execute
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for delay on each retry (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        retryable_exceptions: Tuple of exception types to retry on
        retryable_status_codes: List of HTTP status codes to retry on
        rate_limit_delay: Fixed delay before each call for rate limiting
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of func(*args, **kwargs)
    
    Raises:
        Last exception if all retries exhausted
        
    Example:
        result = run_resiliently(
            api_call_function,
            param1, param2,
            max_retries=3,
            initial_delay=2.0
        )
    """
    
    # Default retryable exceptions
    if retryable_exceptions is None:
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            Exception  # Catch-all for API errors
        )
    
    # Default retryable HTTP status codes
    if retryable_status_codes is None:
        retryable_status_codes = [429, 500, 502, 503, 504]
    
    last_exception = None
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            # Apply rate limiting delay before each call
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Success!
            if attempt > 0:
                logger.info(f"✅ Success after {attempt} retry(ies)")
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Determine if we should retry this exception
            should_retry = False
            retry_reason = None
            error_str = str(e).lower()
            
            # Check for quota/rate limit errors (most common in production)
            if any(keyword in error_str for keyword in [
                'quota', 'rate limit', '429', 'too many requests',
                'quotaexceeded', 'userlimitexceeded'
            ]):
                should_retry = True
                retry_reason = "quota/rate limit"
            
            # Check for retryable HTTP status codes
            elif hasattr(e, 'status_code') and e.status_code in retryable_status_codes:
                should_retry = True
                retry_reason = f"HTTP {e.status_code}"
            
            # Check for network/connection errors
            elif any(isinstance(e, exc_type) for exc_type in retryable_exceptions):
                should_retry = True
                retry_reason = "network/connection error"
            
            # Check for timeout errors
            elif 'timeout' in error_str or 'timed out' in error_str:
                should_retry = True
                retry_reason = "timeout"
            
            # Check for temporary Google API errors
            elif 'backend error' in error_str or 'internal error' in error_str:
                should_retry = True
                retry_reason = "backend error"
            
            else:
                # Not retryable - raise immediately
                logger.error(f"❌ Non-retryable error: {type(e).__name__}: {str(e)[:200]}")
                raise
            
            # If this was the last attempt, raise the exception
            if attempt >= max_retries:
                logger.error(f"❌ Max retries ({max_retries}) exhausted for {retry_reason}")
                raise
            
            # Calculate wait time with exponential backoff
            wait_time = min(initial_delay * (backoff_factor ** attempt), max_delay)
            
            # Log the retry attempt
            logger.warning(
                f"⚠️  {retry_reason} - Attempt {attempt + 1}/{max_retries + 1} failed. "
                f"Retrying in {wait_time:.1f}s... Error: {str(e)[:100]}"
            )
            
            # Wait before retrying
            time.sleep(wait_time)
    
    # Should never reach here, but just in case
    if last_exception:
        raise last_exception


def resilient_api_call(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    rate_limit_delay: float = 0.0
):
    """
    Decorator version of run_resiliently for API functions.
    
    Use this to make any function resilient with a simple decorator.
    
    Args:
        max_retries: Maximum retry attempts
        initial_delay: Initial delay between retries
        backoff_factor: Exponential backoff multiplier
        max_delay: Maximum delay between retries
        rate_limit_delay: Fixed delay before each call
    
    Returns:
        Decorated function with retry logic
        
    Example:
        @resilient_api_call(max_retries=3, initial_delay=2.0)
        def download_file(file_id):
            return drive_service.files().get_media(fileId=file_id).execute()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return run_resiliently(
                func,
                *args,
                max_retries=max_retries,
                initial_delay=initial_delay,
                backoff_factor=backoff_factor,
                max_delay=max_delay,
                rate_limit_delay=rate_limit_delay,
                **kwargs
            )
        return wrapper
    return decorator


def rate_limited(calls_per_second: float = 10.0):
    """
    Decorator to rate limit function calls.
    
    Ensures function is not called more frequently than specified rate.
    Useful for API calls with quota limits.
    
    Args:
        calls_per_second: Maximum calls per second (default: 10.0)
    
    Returns:
        Decorated function with rate limiting
        
    Example:
        @rate_limited(calls_per_second=10.0)
        def api_call():
            return service.files().list().execute()
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Calculate time since last call
            elapsed = time.time() - last_called[0]
            
            # Wait if necessary to maintain rate limit
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            
            # Update last called time
            last_called[0] = time.time()
            
            # Execute function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_retries_and_rate_limit(
    max_retries: int = 3,
    calls_per_second: float = 10.0,
    initial_delay: float = 1.0
):
    """
    Combined decorator for both retry logic and rate limiting.
    
    This is the most common pattern for production API calls.
    
    Args:
        max_retries: Maximum retry attempts
        calls_per_second: Maximum calls per second
        initial_delay: Initial delay between retries
    
    Returns:
        Decorated function with both retry and rate limiting
        
    Example:
        @with_retries_and_rate_limit(max_retries=3, calls_per_second=10.0)
        def robust_api_call():
            return service.files().list().execute()
    """
    def decorator(func: Callable) -> Callable:
        # Apply rate limiting first, then retry logic
        rate_limited_func = rate_limited(calls_per_second)(func)
        resilient_func = resilient_api_call(
            max_retries=max_retries,
            initial_delay=initial_delay
        )(rate_limited_func)
        return resilient_func
    return decorator


# Convenience function for backward compatibility
def api_call_with_retry(func, *args, **kwargs):
    """
    Simple wrapper for backward compatibility with existing code.
    
    Example:
        result = api_call_with_retry(my_api_function, arg1, arg2)
    """
    return run_resiliently(
        func,
        *args,
        max_retries=3,
        initial_delay=2.0,
        rate_limit_delay=0.1,
        **kwargs
    )

