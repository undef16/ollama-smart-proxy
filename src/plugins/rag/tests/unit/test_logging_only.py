"""Minimal tests for enhanced error handling and logging functionality."""

import pytest
from unittest.mock import patch, MagicMock

# Import directly from the module
from src.plugins.rag.infrastructure.logging import (
    RagError, ConfigurationError, NetworkError, ExternalServiceError,
    SearchError, RetrievalError, GradingError, InjectionError, ValidationError,
    ErrorContext, ErrorCategory, ErrorSeverity,
    LoggingUtils, ErrorMetrics
)
from src.plugins.rag.infrastructure.error_handler import ErrorHandler


class TestEnhancedErrors:
    """Test enhanced error classes."""

    def test_rag_error_creation(self):
        """Test basic RagError creation."""
        error = RagError("Test error")
        assert str(error) == "Test error"
        assert error.context is not None
        assert error.suggestions == []
        assert error.cause is None

    def test_rag_error_with_context(self):
        """Test RagError with full context."""
        context = ErrorContext(
            operation="test_op",
            component="test_component",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            metadata={"key": "value"}
        )
        suggestions = ["Try this", "Try that"]
        cause = ValueError("Original error")

        error = RagError("Test error", context=context, suggestions=suggestions, cause=cause)

        assert error.context == context
        assert error.suggestions == suggestions
        assert error.cause == cause

        details = error.get_error_details()
        assert details["error_type"] == "RagError"
        assert details["message"] == "Test error"
        assert details["context"]["operation"] == "test_op"
        assert details["suggestions"] == suggestions
        assert details["cause"] == "Original error"

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config error", config_key="database_url")
        assert isinstance(error, RagError)
        assert error.context.category == ErrorCategory.CONFIGURATION
        assert error.context.severity == ErrorSeverity.HIGH
        assert error.context.metadata["config_key"] == "database_url"
        assert len(error.suggestions) > 0

    def test_network_error(self):
        """Test NetworkError."""
        error = NetworkError("Network error", url="http://example.com", timeout=30.0)
        assert isinstance(error, RagError)
        assert error.context.category == ErrorCategory.NETWORK
        assert error.context.metadata["url"] == "http://example.com"
        assert error.context.metadata["timeout"] == 30.0

    def test_external_service_error(self):
        """Test ExternalServiceError."""
        error = ExternalServiceError("Service error", service_name="ollama", operation="invoke")
        assert isinstance(error, RagError)
        assert error.context.category == ErrorCategory.EXTERNAL_SERVICE
        assert error.context.metadata["service"] == "ollama"

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Validation error", field="query", value="invalid")
        assert isinstance(error, RagError)
        assert error.context.category == ErrorCategory.VALIDATION
        assert error.context.metadata["field"] == "query"
        assert error.context.metadata["value"] == "invalid"


class TestErrorMetrics:
    """Test error metrics functionality."""

    def test_error_metrics_recording(self):
        """Test recording errors in metrics."""
        metrics = ErrorMetrics()

        # Record different types of errors
        config_error = ConfigurationError("Config error")
        network_error = NetworkError("Network error")
        grading_error = GradingError("Grading error")

        metrics.record_error(config_error)
        metrics.record_error(network_error)
        metrics.record_error(grading_error)

        assert metrics.total_errors == 3
        assert metrics.errors_by_category["configuration"] == 1
        assert metrics.errors_by_category["network"] == 1
        assert metrics.errors_by_category["processing"] == 1  # grading is processing

        assert metrics.errors_by_severity["high"] == 1  # config error
        assert metrics.errors_by_severity["medium"] == 1  # network
        assert metrics.errors_by_severity["low"] == 1  # grading

    def test_error_alerts(self):
        """Test alert generation based on error thresholds."""
        metrics = ErrorMetrics()

        # Add some high severity errors
        for i in range(6):  # Exceed threshold of 5
            error = ConfigurationError(f"Config error {i}")
            metrics.record_error(error)

        alerts = metrics.should_alert()
        assert len(alerts) > 0
        assert any("High severity errors" in alert for alert in alerts)


class TestLoggingUtils:
    """Test LoggingUtils functionality."""

    def test_create_error(self):
        """Test error creation utility."""
        error = LoggingUtils.create_error(
            operation="test_op",
            message="Test message",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            field="test_field"
        )

        assert isinstance(error, RagError)
        assert error.context.operation == "test_op"
        assert error.context.category == ErrorCategory.VALIDATION
        assert error.context.severity == ErrorSeverity.LOW
        assert error.context.metadata["field"] == "test_field"


class TestErrorHandler:
    """Test ErrorHandler decorators."""

    def test_retry_on_failure_success(self):
        """Test retry decorator with successful operation."""
        call_count = 0

        @ErrorHandler.retry_on_failure(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure_eventual_success(self):
        """Test retry decorator with eventual success."""
        call_count = 0

        @ErrorHandler.retry_on_failure(max_attempts=3, exceptions=(ValueError,))
        def eventual_success_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = eventual_success_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_on_failure_exhaustion(self):
        """Test retry decorator exhaustion."""
        call_count = 0

        @ErrorHandler.retry_on_failure(max_attempts=2, exceptions=(ValueError,))
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")

        with pytest.raises(RagError) as exc_info:
            failing_func()

        assert call_count == 2
        assert "failed after 2 attempts" in str(exc_info.value)

    @patch('src.plugins.rag.infrastructure.logging.LoggingUtils.log_structured_error')
    def test_with_fallback(self, mock_log_error):
        """Test fallback decorator."""
        call_count = 0

        @ErrorHandler.with_fallback(fallback_value="fallback_result", exceptions=(ValueError,))
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failure")

        result = failing_func()
        assert result == "fallback_result"
        assert call_count == 1

    @patch('src.plugins.rag.infrastructure.logging.thread_local')
    @patch('src.plugins.rag.infrastructure.logging.LoggingUtils.log_structured_error')
    def test_log_error_context(self, mock_log_error, mock_thread_local):
        """Test error context logging decorator."""
        # Setup thread local mock
        mock_thread_local.request_id = None
        mock_thread_local.operation = None
        mock_thread_local.component = None
        mock_thread_local.user_id = None

        @ErrorHandler.log_error_context("test_operation", component="test_component")
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(RagError) as exc_info:
            failing_func()

        # Verify error was logged
        mock_log_error.assert_called_once()

        # Verify context was set
        assert mock_thread_local.request_id is None  # Should be restored
        assert mock_thread_local.operation is None
        assert mock_thread_local.component is None
        assert mock_thread_local.user_id is None


class TestErrorContext:
    """Test ErrorContext functionality."""

    def test_error_context_creation(self):
        """Test ErrorContext creation and serialization."""
        import time
        before = time.time()

        context = ErrorContext(
            operation="test_op",
            request_id="req-123",
            user_id="user-456",
            component="test_component",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            retry_count=2,
            metadata={"table": "users", "operation": "select"}
        )

        after = time.time()

        assert context.operation == "test_op"
        assert context.request_id == "req-123"
        assert context.user_id == "user-456"
        assert context.component == "test_component"
        assert context.category == ErrorCategory.DATABASE
        assert context.severity == ErrorSeverity.CRITICAL
        assert context.retry_count == 2
        assert context.metadata["table"] == "users"
        assert before <= context.timestamp <= after

        # Test serialization
        data = context.to_dict()
        assert data["operation"] == "test_op"
        assert data["request_id"] == "req-123"
        assert data["category"] == "database"
        assert data["severity"] == "critical"
        assert data["retry_count"] == 2
        assert data["metadata"]["table"] == "users"