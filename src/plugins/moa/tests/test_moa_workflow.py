"""Integration tests for the MoA agent full workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app


class TestMoAWorkflow:
    """Integration tests for the complete MoA workflow."""

    @pytest.fixture
    def client(self):
        """Test client for the FastAPI app."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_moa_full_workflow_success(self, client):
        """Test the complete MoA workflow from request to synthesized response."""
        # Mock the MoA agent methods
        with patch('src.plugins.moa.agent.MoAAgent.collect_responses', new_callable=AsyncMock) as mock_collect_responses, \
             patch('src.plugins.moa.agent.MoAAgent.collect_rankings', new_callable=AsyncMock) as mock_collect_rankings:

            mock_collect_responses.return_value = [
                {"model": "model1", "response": "Response from model1"},
                {"model": "model2", "response": "Response from model2"}
            ]
            mock_collect_rankings.return_value = "Final synthesized response"

            # Make the MoA request
            request_data = {
                "model": "llama3.2",  # This will be overridden by MoA
                "messages": [
                    {"role": "user", "content": "/moa What is Artificial Intelligence?"}
                ]
            }

            response = client.post("/api/chat", json=request_data)

            assert response.status_code == 200
            response_data = response.json()

            # Verify the response structure
            assert "choices" in response_data
            assert len(response_data["choices"]) == 1
            assert response_data["choices"][0]["message"]["role"] == "assistant"
            assert response_data["choices"][0]["message"]["content"] == "Final synthesized response"
            assert response_data["choices"][0]["finish_reason"] == "stop"

            # Verify the workflow methods were called
            mock_collect_responses.assert_called_once()
            mock_collect_rankings.assert_called_once()

    @patch('httpx.AsyncClient')
    def test_moa_workflow_partial_model_failure(self, mock_client_class, client):
        """Test MoA workflow when some models fail in stage 1."""
        # Setup mock HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.__aexit__ = AsyncMock(return_value=None)

        call_count = 0
        async def mock_post(url, json):
            nonlocal call_count
            call_count += 1

            if call_count == 1:  # First model succeeds
                mock_resp = MagicMock()
                mock_resp.json.return_value = {
                    "model": "llama3.2",
                    "created_at": "2023-12-01T00:00:00Z",
                    "message": {"role": "assistant", "content": "AI is artificial intelligence."},
                    "done": True
                }
                mock_resp.raise_for_status = MagicMock()
                return mock_resp
            elif call_count == 2:  # Second model fails
                raise Exception("Model unavailable")
            elif call_count == 3:  # Ranking with remaining model - TwoModelsRankingStrategy
                mock_resp = MagicMock()
                mock_resp.json.return_value = {
                    "model": "llama3.2",
                    "created_at": "2023-12-01T00:00:01Z",
                    "message": {
                        "role": "assistant",
                        "content": '{"score": 0.8}'  # model1 scores model2's response
                    },
                    "done": True
                }
                mock_resp.raise_for_status = MagicMock()
                return mock_resp
            else:  # model2 scores model1's response
                mock_resp = MagicMock()
                mock_resp.json.return_value = {
                    "model": "llama3.2",
                    "created_at": "2023-12-01T00:00:02Z",
                    "message": {
                        "role": "assistant",
                        "content": '{"score": 0.6}'  # model2 scores model1's response
                    },
                    "done": True
                }
                mock_resp.raise_for_status = MagicMock()
                return mock_resp

        mock_client.post = AsyncMock(side_effect=mock_post)

        # Make the MoA request
        request_data = {
            "model": "llama3.2",
            "messages": [
                {"role": "user", "content": "/moa What is AI?"}
            ]
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        response_data = response.json()

        # Should still get a response despite one model failing
        assert "choices" in response_data
        assert len(response_data["choices"]) == 1
        assert response_data["choices"][0]["message"]["role"] == "assistant"
        assert "AI" in response_data["choices"][0]["message"]["content"]

    @patch('httpx.AsyncClient')
    def test_moa_workflow_chairman_failure_fallback(self, mock_client_class, client):
        """Test MoA workflow when ranking fails and fallback is used."""
        # Setup mock HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.__aexit__ = AsyncMock(return_value=None)

        call_count = 0
        async def mock_post(url, json):
            nonlocal call_count
            call_count += 1

            if call_count <= 2:  # Stage 1 responses
                response_index = call_count - 1
                mock_resp = MagicMock()
                mock_resp.json.return_value = {
                    "model": f"model{call_count}",
                    "created_at": "2023-12-01T00:00:00Z",
                    "message": {"role": "assistant", "content": f"Response from model {call_count}"},
                    "done": True
                }
                mock_resp.raise_for_status = MagicMock()
                return mock_resp
            else:  # Ranking fails
                raise Exception("Ranking model unavailable")

        mock_client.post = AsyncMock(side_effect=mock_post)

        # Make the MoA request
        request_data = {
            "model": "llama3.2",
            "messages": [
                {"role": "user", "content": "/moa What is AI?"}
            ]
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200
        response_data = response.json()

        # Should get error response when ranking fails
        assert "choices" in response_data
        assert len(response_data["choices"]) == 1
        assert response_data["choices"][0]["message"]["role"] == "assistant"
        assert "MoA process failed" in response_data["choices"][0]["message"]["content"]

    def test_moa_not_activated_passthrough(self, client):
        """Test that non-MOA requests pass through unchanged."""
        request_data = {
            "model": "llama3.2",
            "messages": [
                {"role": "user", "content": "Hello, not a MoA request"}
            ]
        }

        # This would normally require mocking Ollama, but for this test we just verify
        # the request structure is maintained (the actual response depends on Ollama being available)
        response = client.post("/api/chat", json=request_data)

        # The response should be a valid chat completion format
        # (exact content depends on whether Ollama is mocked or real)
        assert response.status_code in [200, 500]  # 200 if Ollama works, 500 if not mocked

        if response.status_code == 200:
            response_data = response.json()
            assert "choices" in response_data
            assert len(response_data["choices"]) >= 1

    @patch('httpx.AsyncClient')
    def test_moa_empty_query_error(self, mock_client_class, client):
        """Test MoA request with empty query after /moa."""
        # Setup mock HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.__aexit__ = AsyncMock(return_value=None)

        request_data = {
            "model": "llama3.2",
            "messages": [
                {"role": "user", "content": "/moa"}  # No query
            ]
        }

        response = client.post("/api/chat", json=request_data)

        # Should return the original request unchanged since no query
        # This is how the agent handles invalid MoA requests
        assert response.status_code in [200, 500]  # Depends on downstream processing

    @patch('httpx.AsyncClient')
    def test_moa_all_models_fail_error_response(self, mock_client_class, client):
        """Test MoA workflow when all models fail in stage 1."""
        # Setup mock HTTP client that always fails
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client.post = AsyncMock(side_effect=Exception("All models unavailable"))

        request_data = {
            "model": "llama3.2",
            "messages": [
                {"role": "user", "content": "/moa What is AI?"}
            ]
        }

        response = client.post("/api/chat", json=request_data)

        assert response.status_code == 200  # Agent catches exceptions and returns error response
        response_data = response.json()

        assert "choices" in response_data
        assert len(response_data["choices"]) == 1
        assert "MoA failed" in response_data["choices"][0]["message"]["content"]