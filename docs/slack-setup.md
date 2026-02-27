# Slack Integration Guide

This guide explains how to integrate your AI Agent with Slack using the Events API.

## Prerequisites

- A Slack workspace where you can create apps
- Access to the Slack API dashboard
- Your AI Agent deployed and accessible via a public URL (for webhooks)

## Setup Steps

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Enter an App Name (e.g., "AI Assistant")
5. Select your workspace
6. Click "Create App"

### 2. Configure OAuth & Permissions

1. In the left sidebar, click "OAuth & Permissions"
2. Scroll down to "Scopes" → "Bot Token Scopes"
3. Add the following scopes:
   - `app_mentions:read` - View messages that directly mention your bot
   - `chat:write` - Send messages as the bot
   - `channels:history` - View messages in public channels (if needed)
   - `groups:history` - View messages in private channels (if needed)
   - `im:history` - View messages in direct messages
   - `im:write` - Start direct messages with users
   - `users:read` - View user information

4. Scroll to the top and click "Install to Workspace"
5. Authorize the app
6. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
   - This is your `SLACK_BOT_TOKEN`

### 3. Enable Event Subscriptions

1. In the left sidebar, click "Event Subscriptions"
2. Toggle "Enable Events" to ON
3. In "Request URL", enter your webhook endpoint:
   ```
   https://your-domain.com/api/webhook/slack
   ```
4. Slack will send a verification challenge - your app will automatically respond

5. Scroll down to "Subscribe to bot events" and add:
   - `app_mention` - When someone mentions your bot
   - `message.im` - Messages in direct messages
   - `message.channels` - Messages in public channels (optional)
   - `message.groups` - Messages in private channels (optional)

6. Click "Save Changes"

### 4. Get Signing Secret

1. In the left sidebar, click "Basic Information"
2. Scroll to "App Credentials"
3. Copy the "Signing Secret"
   - This is your `SLACK_SIGNING_SECRET`

### 5. Configure Your Application

Add to your `.env` file:

```env
# Slack Bot
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
```

### 6. Deploy and Test

1. Restart your application to load the new configuration
2. In Slack, invite the bot to a channel: `/invite @YourBotName`
3. Mention the bot: `@YourBotName hello!`
4. The bot should respond!

## Usage Patterns

### Direct Mentions
Mention the bot in any channel:
```
@AIAssistant what's the weather like today?
```

### Direct Messages
Send a direct message to the bot - no mention needed:
```
Tell me a joke
```

### Channel Integration
Add the bot to channels where you want it to respond to mentions:
```
/invite @AIAssistant
```

## Commands

The bot supports the same commands as other channels:

- `/help` - Show available commands
- `/reset` - Clear conversation history
- `/status` - Show current session status
- `/model <name>` - Switch AI model

## Troubleshooting

### Bot Not Responding

1. **Check Logs**: Look for errors in your application logs
2. **Verify Token**: Ensure `SLACK_BOT_TOKEN` is correct
3. **Check Scopes**: Verify all required OAuth scopes are added
4. **Event Subscriptions**: Confirm webhook URL is verified
5. **Invite Bot**: Make sure bot is invited to the channel

### Webhook Verification Failed

- Ensure your application is running and accessible
- Check that the URL is correct and uses HTTPS
- Verify firewall/security group settings

### Signature Verification Errors

- Confirm `SLACK_SIGNING_SECRET` is set correctly
- Check that your system clock is synchronized
- Verify you're using the latest slack-sdk version

## Architecture

```
Slack App → Events API → Your Webhook Endpoint
                              ↓
                        SlackAdapter
                              ↓
                        MessageRouter
                              ↓
                        MessageHandler
                              ↓
                        AI Response
                              ↓
                        Slack Web API
                              ↓
                        User in Slack
```

## Security Considerations

1. **Always verify signatures** - The signing secret validates requests are from Slack
2. **Use HTTPS** - Required for production webhooks
3. **Rate limiting** - Implement rate limits to prevent abuse
4. **Token security** - Never commit tokens to version control
5. **Scopes principle** - Only request OAuth scopes you actually need

## Advanced Features

### Interactive Components

To add buttons and interactive elements:

1. Enable "Interactivity & Shortcuts" in Slack App settings
2. Set the Request URL to a new endpoint (e.g., `/api/slack/interactions`)
3. Implement handler in your application

### Slash Commands

To add custom slash commands:

1. Go to "Slash Commands" in Slack App settings
2. Click "Create New Command"
3. Set command name (e.g., `/ask`)
4. Set Request URL
5. Add description and usage hint

## Monitoring

Monitor these metrics for your Slack integration:

- **Response time**: Time from message receipt to response
- **Error rate**: Failed message processing attempts
- **Active conversations**: Number of unique users/channels
- **Command usage**: Frequency of different commands

## References

- [Slack API Documentation](https://api.slack.com/)
- [Events API](https://api.slack.com/apis/connections/events-api)
- [slack-sdk Python Library](https://slack.dev/python-slack-sdk/)
