"""
AIOps Playbooks - structured remediation step sequences.

Each playbook consists of ordered steps. Steps carry a risk level.
The PlaybookExecutor runs steps sequentially, routing high-risk steps
through the ApprovalManager before execution.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()


class RiskLevel(str, Enum):
    LOW = "low"        # Execute immediately, notify after
    MEDIUM = "medium"  # Require human approval
    HIGH = "high"      # Require human approval + explicit confirmation


@dataclass
class PlaybookStep:
    """A single step in a remediation playbook."""
    name: str
    description: str
    risk_level: RiskLevel
    # Tool name + kwargs to call via MCPManager
    tool_name: str
    tool_params_template: dict[str, Any]  # May contain {placeholders} from context
    # Optional: expected output pattern to verify success
    success_pattern: str | None = None

    def resolve_params(self, context: dict[str, Any]) -> dict[str, Any]:
        """Fill template placeholders from incident context."""
        resolved = {}
        for k, v in self.tool_params_template.items():
            if isinstance(v, str):
                try:
                    resolved[k] = v.format(**context)
                except KeyError:
                    resolved[k] = v
            else:
                resolved[k] = v
        return resolved


@dataclass
class Playbook:
    """A named collection of remediation steps."""
    id: str
    name: str
    description: str
    steps: list[PlaybookStep]
    # Callback invoked on playbook completion/failure
    on_complete: Callable[[str, bool, str], Coroutine] | None = None


@dataclass
class PlaybookRun:
    """A running instance of a playbook for a specific incident."""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    playbook_id: str = ""
    incident_context: dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    status: str = "pending"   # pending | running | awaiting_approval | completed | failed
    step_outputs: list[str] = field(default_factory=list)
    error: str | None = None


class PlaybookRegistry:
    """
    Registry of available remediation playbooks.

    Built-in playbooks cover common K8s failure scenarios.
    Custom playbooks can be registered at runtime.
    """

    def __init__(self) -> None:
        self._playbooks: dict[str, Playbook] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in remediation playbooks."""

        self.register(Playbook(
            id="crash_loop_remediation",
            name="CrashLoop Remediation",
            description="Diagnose and remediate a CrashLoopBackOff pod",
            steps=[
                PlaybookStep(
                    name="Describe Pod",
                    description="Gather pod conditions and events",
                    risk_level=RiskLevel.LOW,
                    tool_name="k8s_describe_resource",
                    tool_params_template={"resource_type": "pod", "resource_name": "{resource_name}", "namespace": "{namespace}"},
                ),
                PlaybookStep(
                    name="Fetch Recent Logs",
                    description="Get last 100 lines of logs for error analysis",
                    risk_level=RiskLevel.LOW,
                    tool_name="k8s_analyze_logs",
                    tool_params_template={"pod_name": "{resource_name}", "namespace": "{namespace}", "tail_lines": 100},
                ),
                PlaybookStep(
                    name="Restart Pod",
                    description="Delete pod to trigger fresh restart (controller will recreate)",
                    risk_level=RiskLevel.MEDIUM,
                    tool_name="k8s_restart_pod",
                    tool_params_template={"pod_name": "{resource_name}", "namespace": "{namespace}"},
                ),
                PlaybookStep(
                    name="Verify Recovery",
                    description="Check pod status after restart",
                    risk_level=RiskLevel.LOW,
                    tool_name="k8s_get_pods",
                    tool_params_template={"namespace": "{namespace}", "label_selector": ""},
                ),
            ],
        ))

        self.register(Playbook(
            id="oom_kill_remediation",
            name="OOMKill Remediation",
            description="Increase memory limits for OOM-killed pods",
            steps=[
                PlaybookStep(
                    name="Get Current Limits",
                    description="Describe deployment to see current memory limits",
                    risk_level=RiskLevel.LOW,
                    tool_name="k8s_describe_resource",
                    tool_params_template={"resource_type": "deployment", "resource_name": "{resource_name}", "namespace": "{namespace}"},
                ),
                PlaybookStep(
                    name="Increase Memory Limit",
                    description="Patch deployment to increase memory limit by 50%",
                    risk_level=RiskLevel.HIGH,
                    tool_name="k8s_patch_resource",
                    tool_params_template={
                        "resource_type": "deployment",
                        "resource_name": "{resource_name}",
                        "namespace": "{namespace}",
                        "patch": '{"spec":{"template":{"spec":{"containers":[{"name":"{resource_name}","resources":{"limits":{"memory":"1Gi"}}}]}}}}',
                    },
                ),
            ],
        ))

        self.register(Playbook(
            id="deployment_rollback",
            name="Deployment Rollback",
            description="Roll back a failing deployment to the previous stable revision",
            steps=[
                PlaybookStep(
                    name="Get Rollout History",
                    description="Show deployment revisions available for rollback",
                    risk_level=RiskLevel.LOW,
                    tool_name="k8s_get_rollout_history",
                    tool_params_template={"deployment_name": "{resource_name}", "namespace": "{namespace}"},
                ),
                PlaybookStep(
                    name="Rollback Deployment",
                    description="Undo to previous stable revision",
                    risk_level=RiskLevel.HIGH,
                    tool_name="k8s_rollback_deployment",
                    tool_params_template={"deployment_name": "{resource_name}", "namespace": "{namespace}"},
                ),
                PlaybookStep(
                    name="Check Rollout Status",
                    description="Verify rollback completed successfully",
                    risk_level=RiskLevel.LOW,
                    tool_name="k8s_rollout_status",
                    tool_params_template={"deployment_name": "{resource_name}", "namespace": "{namespace}"},
                ),
            ],
        ))

        self.register(Playbook(
            id="node_not_ready_remediation",
            name="Node NotReady Remediation",
            description="Drain and cordon a NotReady node",
            steps=[
                PlaybookStep(
                    name="Describe Node",
                    description="Gather node conditions and events",
                    risk_level=RiskLevel.LOW,
                    tool_name="k8s_describe_resource",
                    tool_params_template={"resource_type": "node", "resource_name": "{resource_name}", "namespace": ""},
                ),
                PlaybookStep(
                    name="Cordon Node",
                    description="Prevent new pods from scheduling on this node",
                    risk_level=RiskLevel.MEDIUM,
                    tool_name="k8s_cordon_node",
                    tool_params_template={"node_name": "{resource_name}"},
                ),
                PlaybookStep(
                    name="Drain Node",
                    description="Evict all pods from the node",
                    risk_level=RiskLevel.HIGH,
                    tool_name="k8s_drain_node",
                    tool_params_template={"node_name": "{resource_name}"},
                ),
            ],
        ))

        self.register(Playbook(
            id="scale_up_on_load",
            name="Scale Up Under Load",
            description="Increase replica count when HPA has hit maxReplicas",
            steps=[
                PlaybookStep(
                    name="Scale Deployment",
                    description="Add replicas to handle increased load",
                    risk_level=RiskLevel.MEDIUM,
                    tool_name="k8s_scale_deployment",
                    tool_params_template={"deployment": "{resource_name}", "namespace": "{namespace}", "replicas": "{target_replicas}"},
                ),
            ],
        ))

    def register(self, playbook: Playbook) -> None:
        self._playbooks[playbook.id] = playbook
        logger.debug("playbook_registered", playbook_id=playbook.id, name=playbook.name)

    def get(self, playbook_id: str) -> Playbook | None:
        return self._playbooks.get(playbook_id)

    def list_playbooks(self) -> list[dict[str, Any]]:
        return [
            {
                "id": pb.id,
                "name": pb.name,
                "description": pb.description,
                "steps": len(pb.steps),
                "requires_approval": any(s.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH) for s in pb.steps),
            }
            for pb in self._playbooks.values()
        ]
