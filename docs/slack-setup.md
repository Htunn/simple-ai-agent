# Slack Integration Guide

This guide explains how to integrate Simple AI Agent with Slack using the Events API.
The recommended approach uses the [App Manifest](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/)
— a single YAML file that configures the entire Slack app in one step.

## Prerequisites

- A Slack workspace where you can create apps
- Simple AI Agent deployed and reachable via a public HTTPS URL
- Your deployment URL (e.g. `https://your-domain.com`)

---

## Method 1 — App Manifest (Recommended)

The project ships a ready-to-use manifest at [`slack_manifest.yml`](../slack_manifest.yml).
It pre-configures all OAuth scopes, event subscriptions, and bot settings.

### Step 1 — Edit the manifest with your deployment URL

Open `slack_manifest.yml` and replace `YOUR-DOMAIN` on the `request_url` line:

```yaml
settings:
  event_subscriptions:
    request_url: https://your-domain.com/api/webhook/slack
```

### Step 2 — Create the app from the manifest

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App**
2. Choose **From a manifest**
3. Select your development workspace and click **Next**
4. Switch to the **YAML** tab, paste the full contents of `slack_manifest.yml`, then click **Next**
5. Review the summary — you should see:
   - **Scopes**: `app_mentions:read`, `chat:write`, `im:history`, `im:write`, `users:read`, `channels:history`, `groups:history`
   - **Events**: `app_mention`, `message.im`
6. Click **Create**

### Step 3 — Verify the webhook URL

After creation, Slack needs to confirm your endpoint is live:

1. In the app settings, go to **App Manifest** in the left sidebar
2. If the `request_url` shows a yellow warning, click **Verify** next to it
3. Slack sends a `url_verification` challenge — the agent responds automatically
4. The URL turns green ✓

> **Tip:** Your application must be running before this step. For local development,
> use a tunnel such as [ngrok](https://ngrok.com): `ngrok http 8000`
> and set `request_url: https://<your-ngrok-id>.ngrok-free.app/api/webhook/slack`

### Step 4 — Install to workspace and copy tokens

1. In the left sidebar, go to **OAuth & Permissions**
2. Click **Install to Workspace** → **Allow**
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. Go to **Basic Information** → **App Credentials** and copy the **Signing Secret**

### Step 5 — Configure your .env

```env
# Slack Bot
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
```

### Step 6 — Restart and test

1. Restart the application: `docker compose up -d` or `uvicorn src.main:app --reload`
2. In Slack, invite the bot to a channel: `/invite @simple-ai-agent`
3. Mention it: `@simple-ai-agent hello!`
4. For a DM: open the bot's profile → **Message**

---

## Method 2 — Manual Setup (Alternative)

Use this if you prefer to configure each section individually via the Slack UI.

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Enter an app name and select your workspace

### 2. Configure OAuth & Permissions

In **OAuth & Permissions** → **Bot Token Scopes**, add:

| Scope | Purpose |
|---|---|
| `app_mentions:read` | Receive `app_mention` events |
| `chat:write` | Post messages as the bot |
| `im:history` | Read direct message threads |
| `im:write` | Open DM channels with users |
| `users:read` | Look up user profile info |
| `channels:history` | Read messages in public channels |
| `groups:history` | Read messages in private channels |

Then click **Install to Workspace** and copy the `xoxb-` Bot Token.

### 3. Enable Event Subscriptions

In **Event Subscriptions**:
1. Toggle **Enable Events** → ON
2. Set Request URL to `https://your-domain.com/api/webhook/slack`
3. Under **Subscribe to bot events**, add `app_mention` and `message.im`
4. Click **Save Changes**

### 4. Get Signing Secret

**Basic Information** → **App Credentials** → copy **Signing Secret**.

---

## Usage Patterns

### Direct Mentions
Mention the bot in any channel it has been invited to:
```
@simple-ai-agent list all pods in the default namespace
```

### Direct Messages
Send a DM directly — no mention needed:
```
What is the status of my Kubernetes cluster?
```

### Text Commands
These work in both mentions and DMs:

| Command | Description |
|---|---|
| `help` | Show available commands |
| `reset` | Clear your conversation history |
| `status` | Show current session and active AI model |
| `model <name>` | Switch AI model (e.g. `model gpt-4o`) |

---

## Architecture

```
User in Slack
     │
     │  @mention or DM
     ▼
Slack Events API
     │  POST /api/webhook/slack
     ▼
SlackAdapter.handle_incoming_message()
     │
     ▼
MessageRouter → MessageHandler
     │
     ▼
GitHubModelsClient (LLM)
     │  optionally
     ├─ MCPManager  (Kubernetes / SimplePortChecker tools)
     │
     ▼
SlackAdapter.send_message()  →  Slack Web API  →  User
```

---

## Security

| Practice | Details |
|---|---|
| Signature verification | Every inbound request is verified with `SLACK_SIGNING_SECRET` using HMAC-SHA256 |
| Replay protection | Requests older than 5 minutes are rejected |
| HTTPS required | Slack only delivers events to HTTPS endpoints |
| Token storage | Never commit `SLACK_BOT_TOKEN` or `SLACK_SIGNING_SECRET` to version control |
| Minimal scopes | The manifest requests only the scopes the agent actively uses |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Webhook URL not verified | Ensure the agent is running and the URL is publicly reachable |
| Bot not responding in channel | Run `/invite @simple-ai-agent` in the channel |
| `invalid_auth` error in logs | Check `SLACK_BOT_TOKEN` is correctly set and starts with `xoxb-` |
| `403` signature errors | Confirm `SLACK_SIGNING_SECRET` matches the value in Slack **Basic Information** |
| Bot replies to its own messages | Verify `auth.test` is succeeding — the adapter filters out its own `user_id` |
| Clock skew rejection | Sync your server clock: `ntpdate -u pool.ntp.org` |

---

## Updating the App Manifest

If you add features that require new scopes or events, update `slack_manifest.yml`,
then apply the change via the **App Manifest** editor in app settings (paste the new YAML)
or use the API:

```bash
# Validate first
curl -X POST https://slack.com/api/apps.manifest.validate \
  -H "Authorization: Bearer xoxe.xoxp-..." \
  --data-urlencode "manifest=$(cat slack_manifest.yml)"

# Then update
curl -X POST https://slack.com/api/apps.manifest.update \
  -H "Authorization: Bearer xoxe.xoxp-..." \
  -F "app_id=A0123ABC456" \
  --data-urlencode "manifest=$(cat slack_manifest.yml)"
```

> App config tokens (`xoxe.xoxp-...`) are generated under **Your App Configuration Tokens**
> on the [app settings page](https://api.slack.com/apps). They expire after 12 hours;
> rotate them with `tooling.tokens.rotate`.

---

## References

- [App Manifests](https://docs.slack.dev/app-manifests/configuring-apps-with-app-manifests/)
- [App Manifest Reference](https://docs.slack.dev/reference/app-manifest)
- [Events API](https://api.slack.com/apis/connections/events-api)
- [slack-sdk Python Library](https://slack.dev/python-slack-sdk/)
