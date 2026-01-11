import logging
import functools
import time
import threading
import json
from typing import Any, Callable, Optional, TypeVar, Dict, List
from dataclasses import dataclass, field
from enum import Enum

from src.shared.logging import LoggingManager

# Thread-local variables for request tracking
thread_local = threading.local()

# Error severity levels
class ErrorSeverity(Enum):
    """Enumeration of error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Error categories for structured logging
class ErrorCategory(Enum):
    """Enumeration of error categories for structured logging."""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    PROCESSING = "processing"
    VALIDATION = "validation"
    RESOURCE = "resource"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Structured error context information."""
    operation: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    component: str = "unknown"
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "operation": self.operation,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "component": self.component,
            "category": self.category.value,
            "severity": self.severity.value,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

# Custom exception classes for RAG-specific errors
class RagError(Exception):
    """Base exception for RAG-related errors."""

    def __init__(self, message: str, context: Optional[ErrorContext] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext(operation="unknown")
        self.suggestions = suggestions or []
        self.cause = cause

    def get_error_details(self) -> Dict[str, Any]:
        """Get detailed error information."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context.to_dict() if self.context else None,
            "suggestions": self.suggestions,
            "cause": str(self.cause) if self.cause else None
        }

class ConfigurationError(RagError):
    """Exception raised for configuration-related errors."""

    def __init__(self, message: str, config_key: Optional[str] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation="configuration_validation",
            component="config",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            metadata={"config_key": config_key} if config_key else {}
        )
        default_suggestions = [
            "Check configuration file syntax",
            "Verify all required configuration keys are present",
            "Ensure configuration values are valid"
        ]
        if config_key:
            default_suggestions.append(f"Verify configuration for key: {config_key}")

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class NetworkError(RagError):
    """Exception raised for network-related errors."""

    def __init__(self, message: str, url: Optional[str] = None, timeout: Optional[float] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation="network_request",
            component="network",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            metadata={
                "url": url,
                "timeout": timeout
            }
        )
        default_suggestions = [
            "Check network connectivity",
            "Verify the service is running and accessible",
            "Check firewall and proxy settings"
        ]
        if timeout:
            default_suggestions.append(f"Consider increasing timeout from {timeout}s")

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class DatabaseError(RagError):
    """Exception raised for database-related errors."""

    def __init__(self, message: str, operation: str = "unknown", table: Optional[str] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation=f"db_{operation}",
            component="database",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            metadata={"table": table} if table else {}
        )
        default_suggestions = [
            "Check database connection and credentials",
            "Verify database server is running",
            "Check database permissions"
        ]
        if operation:
            default_suggestions.append(f"Verify {operation} operation permissions")

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class ExternalServiceError(RagError):
    """Exception raised for external service errors."""

    def __init__(self, message: str, service_name: str, operation: str = "unknown",
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation=f"{service_name}_{operation}",
            component=service_name,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            metadata={"service": service_name}
        )
        default_suggestions = [
            f"Check if {service_name} service is running",
            f"Verify {service_name} service configuration",
            f"Check {service_name} service logs for errors"
        ]

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class SearchError(RagError):
    """Exception raised for search-related errors."""

    def __init__(self, message: str, query: Optional[str] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation="search",
            component="search",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            metadata={"query": query} if query else {}
        )
        default_suggestions = [
            "Try simplifying the search query",
            "Check search service availability",
            "Verify search index is properly configured"
        ]

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class RetrievalError(RagError):
    """Exception raised for retrieval-related errors."""

    def __init__(self, message: str, query: Optional[str] = None, doc_count: Optional[int] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation="retrieval",
            component="retrieval",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            metadata={
                "query": query,
                "document_count": doc_count
            }
        )
        default_suggestions = [
            "Check if documents are properly indexed",
            "Verify retrieval service is functioning",
            "Try different query formulations"
        ]

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class GradingError(RagError):
    """Exception raised for grading-related errors."""

    def __init__(self, message: str, document_id: Optional[str] = None, query: Optional[str] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation="grading",
            component="grader",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.LOW,
            metadata={
                "document_id": document_id,
                "query": query
            }
        )
        default_suggestions = [
            "Check LLM service availability",
            "Verify grading prompt is valid",
            "Consider fallback grading strategy"
        ]

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class InjectionError(RagError):
    """Exception raised for context injection-related errors."""

    def __init__(self, message: str, context_length: Optional[int] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation="injection",
            component="injector",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            metadata={"context_length": context_length}
        )
        default_suggestions = [
            "Check context size limits",
            "Verify document formatting",
            "Consider truncating or summarizing content"
        ]

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class ValidationError(RagError):
    """Exception raised for validation-related errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None,
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation="validation",
            component="validator",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            metadata={
                "field": field,
                "value": str(value) if value is not None else None
            }
        )
        default_suggestions = [
            "Check input data format and types",
            "Verify required fields are present",
            "Review validation rules"
        ]
        if field:
            default_suggestions.append(f"Verify field '{field}' meets requirements")

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class ResourceError(RagError):
    """Exception raised for resource-related errors (memory, disk, etc.)."""

    def __init__(self, message: str, resource_type: str = "unknown",
                 suggestions: Optional[List[str]] = None, cause: Optional[Exception] = None):
        context = ErrorContext(
            operation="resource_management",
            component="resource_manager",
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            metadata={"resource_type": resource_type}
        )
        default_suggestions = [
            f"Check {resource_type} availability",
            "Monitor resource usage",
            "Consider increasing resource limits"
        ]

        super().__init__(
            message,
            context=context,
            suggestions=suggestions or default_suggestions,
            cause=cause
        )

class RagLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds RAG-specific context to log records."""

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        # Add context from thread-local variables
        extra = kwargs.get('extra', {})
        if request_id := getattr(thread_local, 'request_id', None):
            extra['request_id'] = request_id
        if operation := getattr(thread_local, 'operation', None):
            extra['operation'] = operation
        if user_id := getattr(thread_local, 'user_id', None):
            extra['user_id'] = user_id
        if component := getattr(thread_local, 'component', None):
            extra['component'] = component
        kwargs['extra'] = extra
        return msg, kwargs


@dataclass
class ErrorMetrics:
    """Metrics for error tracking and alerting."""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_component: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[ErrorContext] = field(default_factory=list)
    error_rate_window: float = 300.0  # 5 minutes
    alert_thresholds: Dict[str, int] = field(default_factory=lambda: {
        "high_severity_per_minute": 5,
        "critical_errors_per_hour": 10,
        "total_errors_per_minute": 20
    })

    def record_error(self, error: RagError) -> None:
        """Record an error in metrics."""
        self.total_errors += 1

        category = error.context.category.value if error.context else "unknown"
        severity = error.context.severity.value if error.context else "medium"
        component = error.context.component if error.context else "unknown"

        self.errors_by_category[category] = self.errors_by_category.get(category, 0) + 1
        self.errors_by_severity[severity] = self.errors_by_severity.get(severity, 0) + 1
        self.errors_by_component[component] = self.errors_by_component.get(component, 0) + 1

        # Keep recent errors (last 100)
        if error.context:
            self.recent_errors.append(error.context)
            if len(self.recent_errors) > 100:
                self.recent_errors.pop(0)

    def should_alert(self) -> List[str]:
        """Check if any alert thresholds are exceeded."""
        alerts = []

        # Calculate rates
        now = time.time()
        recent_window = now - self.error_rate_window
        recent_errors = [e for e in self.recent_errors if e.timestamp > recent_window]

        high_severity_recent = [e for e in recent_errors if e.severity.value == "high"]
        critical_recent = [e for e in recent_errors if e.severity.value == "critical"]

        # Check thresholds
        if len(high_severity_recent) >= self.alert_thresholds["high_severity_per_minute"]:
            alerts.append(f"High severity errors: {len(high_severity_recent)} in last 5 minutes")

        if len(critical_recent) >= self.alert_thresholds["critical_errors_per_hour"]:
            alerts.append(f"Critical errors: {len(critical_recent)} in last 5 minutes")

        if len(recent_errors) >= self.alert_thresholds["total_errors_per_minute"]:
            alerts.append(f"Total errors: {len(recent_errors)} in last 5 minutes")

        return alerts

    def get_summary(self) -> Dict[str, Any]:
        """Get error metrics summary."""
        return {
            "total_errors": self.total_errors,
            "errors_by_category": dict(self.errors_by_category),
            "errors_by_severity": dict(self.errors_by_severity),
            "errors_by_component": dict(self.errors_by_component),
            "recent_error_count": len(self.recent_errors),
            "alerts": self.should_alert()
        }


class LoggingUtils:
    """Utility class for logging operations in the RAG plugin."""

    # Global error metrics instance
    _error_metrics = ErrorMetrics()

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a configured logger for the RAG plugin.

        Args:
            name: Logger name, typically __name__

        Returns:
            Configured logger instance with RAG plugin prefix
        """
        return LoggingManager.get_logger(f"rag.{name}")

    @staticmethod
    def get_rag_logger(name: str) -> RagLoggerAdapter:
        """Get a RAG logger adapter with context support.

        Args:
            name: Logger name, typically __name__

        Returns:
            Logger adapter with RAG context
        """
        logger = LoggingUtils.get_logger(name)
        return RagLoggerAdapter(logger, {})

    @staticmethod
    def log_structured_error(error: RagError, logger: Optional[Any] = None) -> None:
        """Log an error with structured information.

        Args:
            error: The RagError to log
            logger: Optional logger to use, otherwise uses default RAG logger
        """
        if logger is None:
            logger = LoggingUtils.get_rag_logger(__name__)

        # Record in metrics
        LoggingUtils._error_metrics.record_error(error)

        # Create structured log message
        error_details = error.get_error_details()

        # Determine log level based on severity
        severity = error.context.severity if error.context else ErrorSeverity.MEDIUM
        if severity == ErrorSeverity.CRITICAL:
            log_level = logging.CRITICAL
        elif severity == ErrorSeverity.HIGH:
            log_level = logging.ERROR
        elif severity == ErrorSeverity.MEDIUM:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Log structured error
        logger.log(log_level, f"Structured Error: {json.dumps(error_details, default=str)}")

        # Log suggestions if any
        if error.suggestions:
            logger.info(f"Error Suggestions: {', '.join(error.suggestions)}")

        # Check for alerts
        alerts = LoggingUtils._error_metrics.should_alert()
        if alerts:
            for alert in alerts:
                logger.warning(f"ALERT: {alert}")

    @staticmethod
    def get_error_metrics() -> Dict[str, Any]:
        """Get current error metrics."""
        return LoggingUtils._error_metrics.get_summary()

    @staticmethod
    def create_error(
        operation: str,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        **kwargs
    ) -> RagError:
        """Create a structured error with context.

        Args:
            operation: The operation that failed
            message: Error message
            category: Error category
            severity: Error severity
            **kwargs: Additional metadata

        Returns:
            RagError instance with proper context
        """
        context = ErrorContext(
            operation=operation,
            category=category,
            severity=severity,
            metadata=kwargs
        )
        return RagError(message, context=context)

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