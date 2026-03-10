import asyncio, sys, json
sys.path.insert(0, '/app')

async def main():
    from src.database.redis import init_redis
    from src.config import get_settings
    from slack_sdk.web.async_client import AsyncWebClient

    settings = get_settings()
    redis = await init_redis()
    slack = AsyncWebClient(token=settings.slack_bot_token)

    keys = await redis.keys('approval:*')
    approval_keys = [k for k in keys if not k.startswith('approval_idx:')]
    print(f'Found {len(approval_keys)} approval key(s) in Redis')

    sent = 0
    for key in approval_keys:
        raw = await redis.get(key)
        if not raw:
            continue
        data = json.loads(raw)
        if data.get('status') != 'pending':
            print(f'  Skipping {key}: status={data.get("status")}')
            continue
        approval_id = data['approval_id']
        short_id = approval_id[:8]
        risk = data.get('risk_level', 'medium')
        tool = data.get('tool_name', '?')
        desc = data.get('description', '')
        params = json.dumps(data.get('tool_params', {}), indent=2)
        timeout_min = settings.approval_timeout_seconds // 60
        risk_emoji = {'low': '🟡', 'medium': '🟠', 'high': '🔴'}.get(risk, '⚠️')

        msg = (
            f"{risk_emoji} *Approval Required* [{risk.upper()}]\n\n"
            f"*Action:* {desc}\n"
            f"*Tool:* `{tool}`\n"
            f"*Parameters:*\n```{params}```\n\n"
            f"Reply with *`approve {short_id}`* to proceed or *`reject {short_id}`* to cancel.\n"
            f"This request expires in {timeout_min} minutes."
        )

        channel = data.get('channel_target', 'D0AHV7N42NS')
        resp = await slack.chat_postMessage(channel=channel, text=msg, mrkdwn=True)
        print(f'  Sent to {channel}: ok={resp["ok"]}, approval_id={approval_id}, short_id={short_id}')
        sent += 1

    if sent == 0:
        print('No pending approvals found — the TTL may have expired.')
        print('Re-run trigger_aiops_approval.py after rebuilding the container with the bug fix.')

asyncio.run(main())
