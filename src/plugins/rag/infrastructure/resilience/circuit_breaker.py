"""Circuit breaker implementation for external service resilience.

This module provides a circuit breaker pattern implementation to protect against
cascading failures when external services (SearxNG, Ollama) become unavailable.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union
from functools import wraps

from ..logging import LoggingUtils


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Number of failures before opening circuit
    recovery_timeout: float = 60.0  # Seconds to wait before trying half-open
    success_threshold: int = 3  # Number of successes needed to close circuit from half-open
    timeout: float = 30.0  # Request timeout in seconds
    name: str = "default"  # Circuit breaker name for logging/metrics


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker state and performance."""
    state_changes: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0  # Requests rejected when circuit is open
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_successes: int = 0
    consecutive_failures: int = 0


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for external service protection.

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail fast with CircuitBreakerOpenException
    - HALF_OPEN: Testing if service has recovered, limited requests allowed
    """

    def __init__(self, config: CircuitBreakerConfig):
        """Initialize the circuit breaker.

        Args:
            config: Configuration for circuit breaker behavior
        """
        self.config = config
        self._state = CircuitBreakerState.CLOSED
        self._state_lock = threading.RLock()
        self._metrics = CircuitBreakerMetrics()
        self._last_state_change = time.time()
        self.logger = LoggingUtils.get_rag_logger(__name__)

        self.logger.debug(f"Circuit breaker '{config.name}' initialized with state: {self._state.value}")

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._state_lock:
            return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics."""
        with self._state_lock:
            return CircuitBreakerMetrics(**self._metrics.__dict__)

    def _change_state(self, new_state: CircuitBreakerState) -> None:
        """Change circuit breaker state and update metrics."""
        with self._state_lock:
            if self._state != new_state:
                old_state = self._state
                self._state = new_state
                self._last_state_change = time.time()
                self._metrics.state_changes += 1

                self.logger.info(
                    f"Circuit breaker '{self.config.name}' state changed: "
                    f"{old_state.value} -> {new_state.value} "
                    f"(changes: {self._metrics.state_changes})"
                )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt resetting the circuit."""
        if self._state != CircuitBreakerState.OPEN:
            return False

        time_since_last_failure = time.time() - (self._metrics.last_failure_time or 0)
        return time_since_last_failure >= self.config.recovery_timeout

    def _record_success(self) -> None:
        """Record a successful request."""
        with self._state_lock:
            self._metrics.total_requests += 1
            self._metrics.successful_requests += 1
            self._metrics.consecutive_successes += 1
            self._metrics.consecutive_failures = 0
            self._metrics.last_success_time = time.time()

            # Transition from HALF_OPEN to CLOSED if success threshold met
            if (self._state == CircuitBreakerState.HALF_OPEN and
                self._metrics.consecutive_successes >= self.config.success_threshold):
                self._change_state(CircuitBreakerState.CLOSED)

    def _record_failure(self) -> None:
        """Record a failed request."""
        with self._state_lock:
            self._metrics.total_requests += 1
            self._metrics.failed_requests += 1
            self._metrics.consecutive_failures += 1
            self._metrics.consecutive_successes = 0
            self._metrics.last_failure_time = time.time()

            # Transition to OPEN if failure threshold exceeded
            if (self._state == CircuitBreakerState.CLOSED and
                self._metrics.consecutive_failures >= self.config.failure_threshold):
                self._change_state(CircuitBreakerState.OPEN)
            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Single failure in HALF_OPEN goes back to OPEN
                self._change_state(CircuitBreakerState.OPEN)

    def _record_rejection(self) -> None:
        """Record a rejected request (circuit open)."""
        with self._state_lock:
            self._metrics.rejected_requests += 1

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Any exception from the wrapped function
        """
        with self._state_lock:
            current_state = self._state

            # Check if we should attempt to reset from OPEN to HALF_OPEN
            if current_state == CircuitBreakerState.OPEN and self._should_attempt_reset():
                self._change_state(CircuitBreakerState.HALF_OPEN)
                current_state = CircuitBreakerState.HALF_OPEN

            # Reject request if circuit is open
            if current_state == CircuitBreakerState.OPEN:
                self._record_rejection()
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.config.name}' is OPEN. "
                    f"Last failure: {self._metrics.last_failure_time}, "
                    f"Consecutive failures: {self._metrics.consecutive_failures}"
                )

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute an async function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the async function call

        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Any exception from the wrapped function
        """
        with self._state_lock:
            current_state = self._state

            # Check if we should attempt to reset from OPEN to HALF_OPEN
            if current_state == CircuitBreakerState.OPEN and self._should_attempt_reset():
                self._change_state(CircuitBreakerState.HALF_OPEN)
                current_state = CircuitBreakerState.HALF_OPEN

            # Reject request if circuit is open
            if current_state == CircuitBreakerState.OPEN:
                self._record_rejection()
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.config.name}' is OPEN. "
                    f"Last failure: {self._metrics.last_failure_time}, "
                    f"Consecutive failures: {self._metrics.consecutive_failures}"
                )

        # Execute the async function
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap a function with circuit breaker protection.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function with circuit breaker protection
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)
            return sync_wrapper

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the circuit breaker.

        Returns:
            Dictionary with state, metrics, and configuration
        """
        with self._state_lock:
            return {
                "name": self.config.name,
                "state": self._state.value,
                "state_changed_at": self._last_state_change,
                "time_since_last_change": time.time() - self._last_state_change,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout,
                },
                "metrics": {
                    "total_requests": self._metrics.total_requests,
                    "successful_requests": self._metrics.successful_requests,
                    "failed_requests": self._metrics.failed_requests,
                    "rejected_requests": self._metrics.rejected_requests,
                    "state_changes": self._metrics.state_changes,
                    "consecutive_successes": self._metrics.consecutive_successes,
                    "consecutive_failures": self._metrics.consecutive_failures,
                    "last_failure_time": self._metrics.last_failure_time,
                    "last_success_time": self._metrics.last_success_time,
                    "success_rate": (
                        self._metrics.successful_requests / self._metrics.total_requests
                        if self._metrics.total_requests > 0 else 0.0
                    ),
                },
            }


class ServiceCircuitBreakers:
    """Manager for service-specific circuit breakers."""

    def __init__(self):
        """Initialize service circuit breakers."""
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
        self.logger = LoggingUtils.get_rag_logger(__name__)

    def get_or_create(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        timeout: float = 30.0
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a service.

        Args:
            service_name: Name of the service
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            success_threshold: Number of successes needed to close circuit
            timeout: Request timeout in seconds

        Returns:
            CircuitBreaker instance for the service
        """
        with self._lock:
            if service_name not in self._breakers:
                config = CircuitBreakerConfig(
                    name=service_name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    success_threshold=success_threshold,
                    timeout=timeout,
                )
                self._breakers[service_name] = CircuitBreaker(config)
                self.logger.debug(f"Created circuit breaker for service: {service_name}")

            return self._breakers[service_name]

    def get_breaker(self, service_name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker for a service.

        Args:
            service_name: Name of the service

        Returns:
            CircuitBreaker instance or None if not found
        """
        with self._lock:
            return self._breakers.get(service_name)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers.

        Returns:
            Dictionary mapping service names to their status
        """
        with self._lock:
            return {
                name: breaker.get_status()
                for name, breaker in self._breakers.items()
            }

    def reset_all(self) -> None:
        """Reset all circuit breakers to initial state."""
        with self._lock:
            for breaker in self._breakers.values():
                # Reset by recreating the breaker (simplest way)
                config = breaker.config
                breaker._state = CircuitBreakerState.CLOSED
                breaker._metrics = CircuitBreakerMetrics()
                breaker._last_state_change = time.time()
                breaker._metrics.state_changes = 0  # Reset state changes too

            self.logger.info("Reset all circuit breakers")


class CircuitBreakerRegistry:
    """Registry class that encapsulates all global circuit breaker functionality."""

    # Class-level instance to maintain state across all calls
    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def _get_instance(cls):
        """Get or create the singleton instance of the registry."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = ServiceCircuitBreakers()
        return cls._instance

    @classmethod
    def reset_all_circuit_breakers(cls) -> None:
        """Reset all circuit breakers to initial state."""
        instance = cls._get_instance()
        instance.reset_all()

    @classmethod
    def get_service_circuit_breaker(
        cls,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        timeout: float = 30.0
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a service.

        Args:
            service_name: Name of the service
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            success_threshold: Number of successes needed to close circuit
            timeout: Request timeout in seconds

        Returns:
            CircuitBreaker instance for the service
        """
        registry = cls._get_instance()
        return registry.get_or_create(
            service_name=service_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            timeout=timeout
        )

    @classmethod
    def get_circuit_breaker_status(cls) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers.

        Returns:
            Dictionary mapping service names to their status
        """
        registry = cls._get_instance()
        return registry.get_all_status()


