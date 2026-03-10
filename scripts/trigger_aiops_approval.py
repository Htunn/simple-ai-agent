"""
Trigger an AIOps CrashLoop remediation playbook that sends a MEDIUM-risk
approval request to Slack DM.

Run: docker exec simple-ai-agent python3 /app/scripts/trigger_aiops_approval.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")

SLACK_DM_CHANNEL = "D0AHV7N42NS"
POD_NAME = "nginx-crashloop-demo"
NAMESPACE = "default"


async def main() -> None:
    from slack_sdk.web.async_client import AsyncWebClient

    from src.config import get_settings
    from src.database.redis import init_redis
    from src.mcp.mcp_manager import MCPManager
    from src.services.approval_manager import ApprovalManager
    from src.aiops.playbooks import PlaybookExecutor, PlaybookRegistry

    settings = get_settings()
    slack_client = AsyncWebClient(token=settings.slack_bot_token)

    async def send_to_slack(channel_target: str, message: str) -> None:
        slack_msg = re.sub(r"\*\*(.+?)\*\*", r"*\1*", message)
        try:
            await slack_client.chat_postMessage(
                channel=channel_target, text=slack_msg, mrkdwn=True
            )
            print(f"  [slack->Slack] {slack_msg[:100]}")
        except Exception as exc:
            print(f"  [slack ERROR] {exc}")

    # Redis
    from src.database.redis import init_redis
    redis = await init_redis()

    # MCP
    print("Starting MCP manager...")
    mcp = MCPManager()
    started = await mcp.start()
    info = mcp.get_server_info()
    print(f"MCP started={started}, servers={info['connected_servers']}, tools={info['total_tools']}")

    # Approval Manager
    approval_mgr = ApprovalManager(redis_client=redis, mcp_manager=mcp)

    # Playbook Executor
    registry = PlaybookRegistry()
    executor = PlaybookExecutor(
        registry=registry,
        mcp_manager=mcp,
        approval_manager=approval_mgr,
        notify_callback=send_to_slack,
    )

    # Alert notification first
    await send_to_slack(
        SLACK_DM_CHANNEL,
        f"🚨 *AIOps Alert* [CRITICAL]\n"
        f"Type: `crash_loop`\n"
        f"Resource: `Pod/{POD_NAME}` in `{NAMESPACE}`\n"
        f"Pod `{POD_NAME}` has restarted *8 times* in the last 10 minutes.\n\n"
        f"🔧 Playbooks queued: `crash_loop_remediation`\n"
        f"High-risk steps will require your approval.",
    )

    # Execute playbook
    print(f"\nExecuting crash_loop_remediation for {POD_NAME}...")
    incident_context = {
        "event_type": "crash_loop",
        "severity": "critical",
        "resource_kind": "Pod",
        "resource_name": POD_NAME,
        "namespace": NAMESPACE,
        "message": f"Pod {POD_NAME} is in CrashLoopBackOff (restarts: 8)",
        "restart_count": 8,
    }

    run = await executor.execute(
        playbook_id="crash_loop_remediation",
        incident_context=incident_context,
        channel_type="slack",
        channel_target=SLACK_DM_CHANNEL,
        requested_by="aiops-watchloop",
    )

    print(f"\nPlaybook run finished:")
    print(f"  run_id : {run.run_id}")
    print(f"  status : {run.status}")
    print(f"  steps  : {len(run.step_outputs)} completed")
    for i, out in enumerate(run.step_outputs):
        print(f"  step[{i}]: {out[:120]}")

    await mcp.stop()
    print("\nDone — check your Slack DM for the approval request.")


if __name__ == "__main__":
    asyncio.run(main())
