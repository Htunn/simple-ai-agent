"""Unit tests for A2A authentication."""

import pytest
from datetime import datetime, timedelta, UTC

from src.exceptions import A2AAuthenticationError
from src.services.a2a_auth import A2AAuth


class TestA2AAuth:
    """Test A2A authentication and authorization."""

    @pytest.fixture
    def auth(self):
        """Create A2AAuth instance for testing."""
        return A2AAuth(jwt_secret="test-secret-key", token_expiry_hours=1)

    def test_generate_api_key(self, auth):
        """Test API key generation."""
        api_key = auth.generate_api_key()
        assert len(api_key) == 64  # 32 bytes as hex
        assert isinstance(api_key, str)

    def test_hash_api_key(self, auth):
        """Test API key hashing."""
        api_key = "test-api-key-12345"
        hash1 = auth.hash_api_key(api_key)
        hash2 = auth.hash_api_key(api_key)

        # Should be deterministic
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex chars
        assert hash1 != api_key  # Should be hashed

    def test_verify_api_key_success(self, auth):
        """Test API key verification with correct key."""
        api_key = "test-api-key-12345"
        api_key_hash = auth.hash_api_key(api_key)

        assert auth.verify_api_key(api_key, api_key_hash) is True

    def test_verify_api_key_failure(self, auth):
        """Test API key verification with incorrect key."""
        api_key = "test-api-key-12345"
        wrong_key = "wrong-api-key"
        api_key_hash = auth.hash_api_key(api_key)

        assert auth.verify_api_key(wrong_key, api_key_hash) is False

    def test_create_jwt_token(self, auth):
        """Test JWT token creation."""
        token = auth.create_jwt_token(
            agent_id="test-agent",
            capabilities=["kubernetes.scale", "database.query"],
            metadata={"version": "1.0.0"},
        )

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_jwt_token_success(self, auth):
        """Test JWT token verification with valid token."""
        token = auth.create_jwt_token(
            agent_id="test-agent",
            capabilities=["kubernetes.scale"],
        )

        payload = auth.verify_jwt_token(token)

        assert payload["sub"] == "test-agent"
        assert "kubernetes.scale" in payload["capabilities"]
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_jwt_token_invalid(self, auth):
        """Test JWT token verification with invalid token."""
        with pytest.raises(A2AAuthenticationError, match="Invalid token"):
            auth.verify_jwt_token("invalid.token.here")

    def test_extract_agent_id(self, auth):
        """Test extracting agent ID from token."""
        token = auth.create_jwt_token(agent_id="test-agent-123")
        agent_id = auth.extract_agent_id(token)

        assert agent_id == "test-agent-123"

    def test_extract_agent_id_invalid_token(self, auth):
        """Test extracting agent ID from malformed token."""
        with pytest.raises(A2AAuthenticationError, match="Failed to extract agent ID"):
            auth.extract_agent_id("not-a-jwt-token")

    def test_validate_request_success(self, auth):
        """Test request validation with valid authorization."""
        token = auth.create_jwt_token(
            agent_id="test-agent",
            capabilities=["kubernetes.scale", "database.query"],
        )

        authorization_header = f"Bearer {token}"
        agent_id = auth.validate_request(
            authorization_header=authorization_header,
            required_capabilities=["kubernetes.scale"],
        )

        assert agent_id == "test-agent"

    def test_validate_request_missing_header(self, auth):
        """Test request validation with missing authorization header."""
        with pytest.raises(A2AAuthenticationError, match="Missing Authorization header"):
            auth.validate_request(authorization_header=None)

    def test_validate_request_invalid_format(self, auth):
        """Test request validation with invalid header format."""
        with pytest.raises(A2AAuthenticationError, match="Invalid Authorization header format"):
            auth.validate_request(authorization_header="InvalidFormat token")

    def test_validate_request_missing_capabilities(self, auth):
        """Test request validation when token missing required capabilities."""
        token = auth.create_jwt_token(
            agent_id="test-agent",
            capabilities=["kubernetes.scale"],
        )

        authorization_header = f"Bearer {token}"

        with pytest.raises(A2AAuthenticationError, match="missing required capabilities"):
            auth.validate_request(
                authorization_header=authorization_header,
                required_capabilities=["database.query"],
            )

    def test_validate_request_subset_capabilities(self, auth):
        """Test request validation with multiple capabilities (subset required)."""
        token = auth.create_jwt_token(
            agent_id="test-agent",
            capabilities=["kubernetes.scale", "database.query", "logs.search"],
        )

        authorization_header = f"Bearer {token}"
        agent_id = auth.validate_request(
            authorization_header=authorization_header,
            required_capabilities=["kubernetes.scale", "database.query"],
        )

        assert agent_id == "test-agent"
