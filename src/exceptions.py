"""Custom exception classes for better error handling."""


class AIOpsOrchestratorError(Exception):
    """Base exception for all AIOps Orchestrator errors."""

    pass


# ── Configuration Errors ──────────────────────────────────────────────────────


class ConfigurationError(AIOpsOrchestratorError):
    """Raised when configuration is invalid or missing."""

    pass


# ── Health Check Errors ───────────────────────────────────────────────────────


class HealthCheckError(AIOpsOrchestratorError):
    """Raised when a health check fails."""

    pass


class DatabaseHealthCheckError(HealthCheckError):
    """Raised when database health check fails."""

    pass


class RedisHealthCheckError(HealthCheckError):
    """Raised when Redis health check fails."""

    pass


# ── Kubernetes Errors ─────────────────────────────────────────────────────────


class K8sClientError(AIOpsOrchestratorError):
    """Base exception for Kubernetes client errors."""

    pass


class K8sConnectionError(K8sClientError):
    """Raised when unable to connect to Kubernetes cluster."""

    pass


class K8sResourceNotFoundError(K8sClientError):
    """Raised when a Kubernetes resource is not found."""

    pass


class K8sOperationError(K8sClientError):
    """Raised when a Kubernetes operation fails."""

    pass


# ── MCP Errors ────────────────────────────────────────────────────────────────


class MCPError(AIOpsOrchestratorError):
    """Base exception for MCP-related errors."""

    pass


class MCPInitializationError(MCPError):
    """Raised when MCP server fails to initialize."""

    pass


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails."""

    pass


class MCPToolCallError(MCPError):
    """Raised when an MCP tool call fails."""

    pass


class MCPTimeoutError(MCPError):
    """Raised when an MCP operation times out."""

    pass


# ── API Backend Monitoring Errors ─────────────────────────────────────────────


class ApiBackendError(AIOpsOrchestratorError):
    """Base exception for API backend monitoring errors."""

    pass


class ApiBackendConnectionError(ApiBackendError):
    """Raised when unable to connect to an API backend."""

    pass


class ApiBackendTimeoutError(ApiBackendError):
    """Raised when API backend request times out."""

    pass


class ApiBackendConfigError(ApiBackendError):
    """Raised when API backend configuration is invalid."""

    pass


# ── AIOps Engine Errors ───────────────────────────────────────────────────────


class AIOpsError(AIOpsOrchestratorError):
    """Base exception for AIOps engine errors."""

    pass


class PlaybookExecutionError(AIOpsError):
    """Raised when playbook execution fails."""

    pass


class RuleEngineError(AIOpsError):
    """Raised when rule engine encounters an error."""

    pass


class ApprovalError(AIOpsError):
    """Raised when approval processing fails."""

    pass


class ApprovalTimeoutError(ApprovalError):
    """Raised when approval request times out."""

    pass


# ── A2A (Agent-to-Agent) Errors ───────────────────────────────────────────────


class A2AError(AIOpsOrchestratorError):
    """Base exception for A2A integration errors."""

    pass


class A2AAuthenticationError(A2AError):
    """Raised when A2A authentication fails."""

    pass


class A2ARegistrationError(A2AError):
    """Raised when agent registration fails."""

    pass


class A2ATaskDelegationError(A2AError):
    """Raised when task delegation fails."""

    pass


class A2ACapabilityNotFoundError(A2AError):
    """Raised when requested capability is not available."""

    pass


class A2ATimeoutError(A2AError):
    """Raised when A2A operation times out."""

    pass


# ── Channel Adapter Errors ────────────────────────────────────────────────────


class ChannelError(AIOpsOrchestratorError):
    """Base exception for channel adapter errors."""

    pass


class ChannelConnectionError(ChannelError):
    """Raised when unable to connect to a messaging channel."""

    pass


class ChannelSendError(ChannelError):
    """Raised when sending a message to a channel fails."""

    pass


class ChannelAuthenticationError(ChannelError):
    """Raised when channel authentication fails."""

    pass
