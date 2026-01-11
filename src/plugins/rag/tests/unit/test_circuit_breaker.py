"""Unit tests for circuit breaker implementation."""

import asyncio
import time
from unittest.mock import Mock, patch
import pytest

from src.plugins.rag.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    CircuitBreakerOpenException,
    CircuitBreakerRegistry,
)


def test_circuit_breaker_initial_state():
    """Test that circuit breaker starts in CLOSED state."""
    config = CircuitBreakerConfig(name="test", failure_threshold=3, recovery_timeout=10.0)
    cb = CircuitBreaker(config)
    
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.config.name == "test"


def test_successful_calls_keep_circuit_closed():
    """Test that successful calls keep the circuit in CLOSED state."""
    config = CircuitBreakerConfig(name="test", failure_threshold=3, recovery_timeout=10.0)
    cb = CircuitBreaker(config)
    
    def success_func():
        return "success"
    
    # Multiple successful calls should keep circuit closed
    for _ in range(5):
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
    
    # Metrics should reflect successful calls
    metrics = cb.metrics
    assert metrics.successful_requests == 5
    assert metrics.failed_requests == 0
    assert metrics.consecutive_successes == 5
    assert metrics.consecutive_failures == 0


def test_circuit_opens_after_failure_threshold():
    """Test that circuit opens after reaching failure threshold."""
    config = CircuitBreakerConfig(name="test", failure_threshold=3, recovery_timeout=1.0)
    cb = CircuitBreaker(config)
    
    def failure_func():
        raise ValueError("Simulated failure")
    
    # First 2 failures should keep circuit closed
    for i in range(2):
        with pytest.raises(ValueError):
            cb.call(failure_func)
        assert cb.state == CircuitBreakerState.CLOSED
    
    # Third failure should open the circuit
    with pytest.raises(ValueError):
        cb.call(failure_func)
    assert cb.state == CircuitBreakerState.OPEN
    
    # Metrics should reflect failures
    metrics = cb.metrics
    assert metrics.failed_requests == 3
    assert metrics.consecutive_failures == 3


def test_circuit_breaker_rejects_calls_when_open():
    """Test that circuit breaker rejects calls when in OPEN state."""
    config = CircuitBreakerConfig(name="test", failure_threshold=2, recovery_timeout=0.1)
    cb = CircuitBreaker(config)
    
    def failure_func():
        raise ValueError("Simulated failure")
    
    # Cause circuit to open
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failure_func)
    assert cb.state == CircuitBreakerState.OPEN
    
    # Now calls should be rejected immediately
    with pytest.raises(CircuitBreakerOpenException):
        cb.call(lambda: "should_not_be_called")
    
    # Metrics should reflect rejection
    metrics = cb.metrics
    assert metrics.rejected_requests == 1


def test_circuit_moves_to_half_open_after_recovery_timeout():
    """Test that circuit moves to HALF_OPEN after recovery timeout."""
    config = CircuitBreakerConfig(name="test", failure_threshold=2, recovery_timeout=0.1)
    cb = CircuitBreaker(config)
    
    def failure_func():
        raise ValueError("Simulated failure")
    
    # Cause circuit to open
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failure_func)
    assert cb.state == CircuitBreakerState.OPEN
    
    # Wait for recovery timeout to pass
    time.sleep(0.2)
    
    # Next call should move to HALF_OPEN
    def success_func():
        return "success"

    # First call after timeout should move to HALF_OPEN (and still fail because func fails)
    with pytest.raises(ValueError):
        cb.call(failure_func)
    assert cb.state == CircuitBreakerState.OPEN

    # Wait for recovery timeout again
    time.sleep(0.2)

    # Successful call should move to HALF_OPEN
    result = cb.call(success_func)
    assert result == "success"
    # Now HALF_OPEN because we need more successes (threshold is 3 by default)
    assert cb.state == CircuitBreakerState.HALF_OPEN

    result = cb.call(success_func)
    assert result == "success"
    # Still HALF_OPEN because we need 3 total successes
    assert cb.state == CircuitBreakerState.HALF_OPEN

    result = cb.call(success_func)
    assert result == "success"
    # Now it should be CLOSED because we had 3 consecutive successes
    assert cb.state == CircuitBreakerState.CLOSED


def test_circuit_returns_to_closed_after_success_threshold():
    """Test that circuit returns to CLOSED after success threshold in HALF_OPEN."""
    config = CircuitBreakerConfig(
        name="test", 
        failure_threshold=2, 
        recovery_timeout=0.1,
        success_threshold=2
    )
    cb = CircuitBreaker(config)
    
    def failure_func():
        raise ValueError("Simulated failure")
    
    # Cause circuit to open
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failure_func)
    assert cb.state == CircuitBreakerState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.2)
    
    # Move to HALF_OPEN with a successful call
    def success_func():
        return "success"
    
    result = cb.call(success_func)
    assert result == "success"
    assert cb.state == CircuitBreakerState.HALF_OPEN
    
    # Another success should close the circuit
    result = cb.call(success_func)
    assert result == "success"
    assert cb.state == CircuitBreakerState.CLOSED


def test_circuit_goes_back_to_open_on_failure_in_half_open():
    """Test that circuit goes back to OPEN if failure occurs in HALF_OPEN."""
    config = CircuitBreakerConfig(
        name="test", 
        failure_threshold=2, 
        recovery_timeout=0.1,
        success_threshold=2
    )
    cb = CircuitBreaker(config)
    
    def failure_func():
        raise ValueError("Simulated failure")
    
    # Cause circuit to open
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failure_func)
    assert cb.state == CircuitBreakerState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.2)
    
    # Move to HALF_OPEN with a successful call
    def success_func():
        return "success"
    
    result = cb.call(success_func)
    assert result == "success"
    assert cb.state == CircuitBreakerState.HALF_OPEN
    
    # A failure should move back to OPEN
    with pytest.raises(ValueError):
        cb.call(failure_func)
    assert cb.state == CircuitBreakerState.OPEN


def test_async_circuit_breaker():
    """Test async version of circuit breaker."""
    config = CircuitBreakerConfig(name="test", failure_threshold=2, recovery_timeout=10.0)
    cb = CircuitBreaker(config)
    
    async def async_success_func():
        return "async_success"
    
    async def async_failure_func():
        raise ValueError("Async simulated failure")
    
    async def run_test():
        # Successful async call
        result = await cb.call_async(async_success_func)
        assert result == "async_success"
        assert cb.state == CircuitBreakerState.CLOSED
        
        # Cause circuit to open with async failures
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call_async(async_failure_func)
        assert cb.state == CircuitBreakerState.OPEN
    
    asyncio.run(run_test())


def test_circuit_breaker_decorator():
    """Test circuit breaker as a decorator."""
    config = CircuitBreakerConfig(name="test", failure_threshold=2, recovery_timeout=10.0)
    cb = CircuitBreaker(config)
    
    @cb
    def decorated_success_func():
        return "decorated_success"
    
    @cb
    def decorated_failure_func():
        raise ValueError("Decorated failure")
    
    # Successful call through decorator
    result = decorated_success_func()
    assert result == "decorated_success"
    assert cb.state == CircuitBreakerState.CLOSED
    
    # Cause circuit to open
    for _ in range(2):
        with pytest.raises(ValueError):
            decorated_failure_func()
    assert cb.state == CircuitBreakerState.OPEN
    
    # Should raise CircuitBreakerOpenException now
    with pytest.raises(CircuitBreakerOpenException):
        decorated_success_func()


def test_async_circuit_breaker_decorator():
    """Test async circuit breaker as a decorator."""
    config = CircuitBreakerConfig(name="test", failure_threshold=2, recovery_timeout=10.0)
    cb = CircuitBreaker(config)
    
    @cb
    async def async_decorated_success_func():
        return "async_decorated_success"
    
    async def run_test():
        result = await async_decorated_success_func()
        assert result == "async_decorated_success"
        assert cb.state == CircuitBreakerState.CLOSED
    
    asyncio.run(run_test())


def test_get_service_circuit_breaker():
    """Test getting service-specific circuit breakers."""
    # Get or create a circuit breaker for a service
    cb1 = CircuitBreakerRegistry.get_service_circuit_breaker("searxng", failure_threshold=5, recovery_timeout=60.0)
    cb2 = CircuitBreakerRegistry.get_service_circuit_breaker("searxng", failure_threshold=5, recovery_timeout=60.0)  # Same name
    cb3 = CircuitBreakerRegistry.get_service_circuit_breaker("ollama", failure_threshold=3, recovery_timeout=30.0)  # Different name

    # Same name should return same instance
    assert cb1 is cb2
    # Different name should return different instance
    assert cb1 is not cb3

    # Config should match
    assert cb1.config.failure_threshold == 5
    assert cb3.config.failure_threshold == 3


def test_get_circuit_breaker_status():
    """Test getting status of all circuit breakers."""
    # Clear any existing breakers
    CircuitBreakerRegistry.reset_all_circuit_breakers()
    
    # Create some circuit breakers
    CircuitBreakerRegistry.get_service_circuit_breaker("service1", failure_threshold=2)
    CircuitBreakerRegistry.get_service_circuit_breaker("service2", failure_threshold=3)

    status = CircuitBreakerRegistry.get_circuit_breaker_status()
    
    assert "service1" in status
    assert "service2" in status
    assert status["service1"]["state"] == "closed"
    assert status["service2"]["state"] == "closed"


def test_reset_all_circuit_breakers():
    """Test resetting all circuit breakers."""
    # Create some circuit breakers and cause one to open
    cb1 = CircuitBreakerRegistry.get_service_circuit_breaker("test1", failure_threshold=1, recovery_timeout=10.0)
    cb2 = CircuitBreakerRegistry.get_service_circuit_breaker("test2", failure_threshold=2, recovery_timeout=10.0)
    
    def failure_func():
        raise ValueError("Failure")
    
    # Open the first circuit breaker
    with pytest.raises(ValueError):
        cb1.call(failure_func)
    assert cb1.state == CircuitBreakerState.OPEN
    
    # Reset all
    CircuitBreakerRegistry.reset_all_circuit_breakers()
    
    # Both should be closed now
    assert cb1.state == CircuitBreakerState.CLOSED
    assert cb2.state == CircuitBreakerState.CLOSED


def test_circuit_breaker_metrics():
    """Test circuit breaker metrics tracking."""
    config = CircuitBreakerConfig(name="test", failure_threshold=3, recovery_timeout=10.0)
    cb = CircuitBreaker(config)
    
    def success_func():
        return "success"
    
    def failure_func():
        raise ValueError("Failure")
    
    # Record some successes
    for _ in range(3):
        cb.call(success_func)
    
    # Record some failures
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(failure_func)
    
    metrics = cb.metrics
    
    assert metrics.total_requests == 5
    assert metrics.successful_requests == 3
    assert metrics.failed_requests == 2
    assert metrics.consecutive_successes == 0  # Last calls were failures
    assert metrics.consecutive_failures == 2


def test_circuit_breaker_configurable_parameters():
    """Test that circuit breaker respects configurable parameters."""
    config = CircuitBreakerConfig(
        name="test",
        failure_threshold=5,
        recovery_timeout=5.0,
        success_threshold=4,
        timeout=30.0
    )
    cb = CircuitBreaker(config)
    
    assert cb.config.failure_threshold == 5
    assert cb.config.recovery_timeout == 5.0
    assert cb.config.success_threshold == 4
    assert cb.config.timeout == 30.0
    assert cb.config.name == "test"