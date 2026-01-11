import logging
import functools
import time
import threading
import json
from typing import Any, Callable, Optional, TypeVar, Dict, List
from dataclasses import dataclass, field
from enum import Enum

from src.shared.logging import LoggingManager
from .logging import (
    RagError, ErrorContext, ErrorCategory, ErrorSeverity, LoggingUtils,
    RagLoggerAdapter, thread_local
)

# Error handling utilities
F = TypeVar('F', bound=Callable[..., Any])

class RecoveryStrategy(Enum):
    """Strategies for error recovery."""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    DEGRADATION = "degradation"
    SKIP = "skip"

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0
    max_delay: float = 60.0
    jitter: bool = True
    exponential_backoff: bool = True

@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""
    fallback_function: Optional[Callable] = None
    fallback_value: Any = None
    degrade_gracefully: bool = True

class ErrorHandler:
    """Enhanced class for error handling utilities in the RAG plugin."""

    @staticmethod
    def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
                          exceptions: tuple = (Exception,), recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY) -> Callable[[F], Any]:
        """Enhanced decorator to retry a function on failure with recovery strategies.

        Args:
            max_attempts: Maximum number of retry attempts
            delay: Initial delay between retries in seconds
            backoff: Backoff multiplier for delay
            exceptions: Tuple of exceptions to catch and retry on
            recovery_strategy: Strategy to use for recovery

        Returns:
            Decorated function
        """
        def decorator(func: F) -> Any:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                current_delay = delay
                logger = LoggingUtils.get_rag_logger(__name__)
                attempt = 0

                while attempt < max_attempts:
                    try:
                        result = func(*args, **kwargs)
                        if attempt > 0:
                            logger.info(f"Function {func.__name__} succeeded on attempt {attempt + 1}")
                        return result

                    except exceptions as e:
                        attempt += 1
                        error_context = ErrorContext(
                            operation=func.__name__,
                            component="error_handler",
                            category=ErrorCategory.PROCESSING,
                            severity=ErrorSeverity.MEDIUM,
                            retry_count=attempt,
                            metadata={"max_attempts": max_attempts}
                        )

                        if attempt >= max_attempts:
                            # Final failure - create structured error
                            error = RagError(
                                f"Function {func.__name__} failed after {max_attempts} attempts",
                                context=error_context,
                                suggestions=["Check service availability", "Review error logs", "Consider fallback strategies"],
                                cause=e
                            )
                            LoggingUtils.log_structured_error(error, logger)
                            raise error from e

                        # Log retry attempt
                        logger.warning(f"Function {func.__name__} failed on attempt {attempt}/{max_attempts}: {e}. Retrying in {current_delay:.2f}s")

                        # Apply recovery strategy
                        if recovery_strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                            # Could integrate with circuit breaker here
                            pass

                        time.sleep(current_delay)
                        if backoff > 1.0:
                            current_delay = min(current_delay * backoff, 60.0)  # Cap at 60 seconds

            return wrapper
        return decorator

    @staticmethod
    def with_fallback(fallback_func: Optional[Callable] = None, fallback_value: Any = None,
                      exceptions: tuple = (Exception,)) -> Callable[[F], Any]:
        """Decorator to provide fallback behavior on failure.

        Args:
            fallback_func: Function to call as fallback
            fallback_value: Value to return as fallback
            exceptions: Exceptions to catch and fallback on

        Returns:
            Decorated function
        """
        def decorator(func: F) -> Any:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                logger = LoggingUtils.get_rag_logger(__name__)
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(f"Function {func.__name__} failed, using fallback: {e}")

                    if fallback_func:
                        try:
                            return fallback_func(*args, **kwargs)
                        except Exception as fallback_error:
                            logger.error(f"Fallback function also failed: {fallback_error}")
                            if fallback_value is not None:
                                return fallback_value
                            raise fallback_error from e
                    elif fallback_value is not None:
                        return fallback_value

                    # Re-raise original error if no fallback
                    raise

            return wrapper
        return decorator

    @staticmethod
    def log_error_context(operation: str, request_id: Optional[str] = None,
                          component: str = "unknown", user_id: Optional[str] = None) -> Callable[[F], Any]:
        """Enhanced decorator to add comprehensive error context to logs.

        Args:
            operation: Operation name for context
            request_id: Request ID for context
            component: Component name for context
            user_id: User ID for context

        Returns:
            Decorated function
        """
        def decorator(func: F) -> Any:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Save previous values
                prev_request_id = getattr(thread_local, 'request_id', None)
                prev_operation = getattr(thread_local, 'operation', None)
                prev_component = getattr(thread_local, 'component', None)
                prev_user_id = getattr(thread_local, 'user_id', None)

                # Set new values
                thread_local.request_id = request_id
                thread_local.operation = operation
                thread_local.component = component
                thread_local.user_id = user_id

                try:
                    return func(*args, **kwargs)
                except RagError as e:
                    # Already structured error, just log it
                    LoggingUtils.log_structured_error(e)
                    raise
                except Exception as e:
                    # Convert to structured error
                    error_context = ErrorContext(
                        operation=operation,
                        request_id=request_id,
                        user_id=user_id,
                        component=component,
                        category=ErrorCategory.UNKNOWN,
                        severity=ErrorSeverity.MEDIUM
                    )

                    structured_error = RagError(
                        f"Unexpected error in {operation}: {str(e)}",
                        context=error_context,
                        suggestions=["Check application logs", "Review system health", "Contact support if issue persists"],
                        cause=e
                    )

                    LoggingUtils.log_structured_error(structured_error)
                    raise structured_error from e
                finally:
                    # Restore previous values
                    if prev_request_id is not None:
                        thread_local.request_id = prev_request_id
                    else:
                        thread_local.request_id = None
                    if prev_operation is not None:
                        thread_local.operation = prev_operation
                    else:
                        thread_local.operation = None
                    if prev_component is not None:
                        thread_local.component = prev_component
                    else:
                        thread_local.component = None
                    if prev_user_id is not None:
                        thread_local.user_id = prev_user_id
                    else:
                        thread_local.user_id = None

            return wrapper
        return decorator

    @staticmethod
    def handle_errors_with_recovery(operation: str, recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY,
                                    **recovery_kwargs) -> Callable[[F], Any]:
        """Decorator that combines error handling with recovery strategies.

        Args:
            operation: Operation name
            recovery_strategy: Recovery strategy to use
            **recovery_kwargs: Additional kwargs for recovery strategy

        Returns:
            Decorated function
        """
        def decorator(func: F) -> Any:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                logger = LoggingUtils.get_rag_logger(__name__)

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if recovery_strategy == RecoveryStrategy.DEGRADATION:
                        logger.warning(f"Operation {operation} failed, degrading gracefully: {e}")
                        return recovery_kwargs.get('default_value', None)
                    elif recovery_strategy == RecoveryStrategy.SKIP:
                        logger.info(f"Operation {operation} failed, skipping: {e}")
                        return None
                    else:
                        # Re-raise for other strategies to be handled by other decorators
                        raise

            return wrapper
        return decorator

    @staticmethod
    def setup_rag_logging(level: str = "INFO", enable_structured_logging: bool = True) -> None:
        """Setup logging specifically for the RAG plugin.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_structured_logging: Whether to enable structured JSON logging for errors
        """
        LoggingManager.setup_logging(level)

        # Configure structured logging if enabled
        if enable_structured_logging:
            # Add JSON formatter for error logs if needed
            root_logger = logging.getLogger()
            # Could add custom formatter here for JSON structured logs

        logger = LoggingUtils.get_rag_logger(__name__)
        logger.info("RAG logging initialized", extra={
            "structured_logging": enable_structured_logging,
            "log_level": level
        })

    @staticmethod
    def create_error(operation: str, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN,
                     severity: ErrorSeverity = ErrorSeverity.MEDIUM, **metadata) -> RagError:
        """Create a structured RagError with context.

        Args:
            operation: Operation that failed
            message: Error message
            category: Error category
            severity: Error severity
            **metadata: Additional metadata

        Returns:
            Structured RagError instance
        """
        context = ErrorContext(
            operation=operation,
            request_id=getattr(thread_local, 'request_id', None),
            user_id=getattr(thread_local, 'user_id', None),
            component=getattr(thread_local, 'component', 'unknown'),
            category=category,
            severity=severity,
            metadata=metadata
        )

        return RagError(message, context=context)

    @staticmethod
    def log_and_raise(error: RagError) -> None:
        """Log a structured error and raise it.

        Args:
            error: The error to log and raise

        Raises:
            RagError: The provided error
        """
        LoggingUtils.log_structured_error(error)
        raise error

    @staticmethod
    def get_error_summary() -> Dict[str, Any]:
        """Get a summary of error metrics and recent issues.
        
        Returns:
            Dictionary containing error metrics and timestamp
        """
        return {
            "error_metrics": LoggingUtils.get_error_metrics(),
            "timestamp": time.time()
        }