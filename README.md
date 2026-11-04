# The Citadel Dispatch: Instagram Discord Notification Service

An automated, self-hosted Instagram monitoring service built to stream updates from `@houseofthedragonhbo`, `@gameofthrones`, `@aknightofthe7kingdomshbo`, `@westerosies`, and any other public accounts directly into Discord channels with full multi-image carousel support.

Operates 100% free with no paid subscriptions (no MEE6, no Pingcord, no RSS.app limitations) and includes a built-in keep-alive server for permanent 24/7 uptime on Render's free tier.

---

## Features

- **Full Carousel Support:** Automatically detects multi-image carousel posts and packages all slides into Discord lightbox galleries. Users can click any image to view all slides full-screen without cropping.
- **Multi-Feed Tracking:** Concurrently monitors multiple accounts (`@houseofthedragonhbo`, `@gameofthrones`, etc.) on a customizable schedule.
- **Dual Operating Modes:**
  - **Webhook Mode (Recommended):** Post directly to any channel via a Discord Webhook URL. Zero bot setup, developer portal, or guild permissions required.
  - **Bot Token Mode:** Connect as an authenticated Discord Bot user.
- **The Citadel Dashboard:** An A Song of Ice and Fire-themed web interface running on the server root, allowing server administrators to manually trigger post checks with a single click from any device.
- **No Redeploy Spam:** Establishes an initial baseline upon boot so that redeploying or restarting the server never re-sends previously posted content.
- **24/7 Keep-Alive Architecture:** Exposes a lightweight `/health` HTTP endpoint so free cloud hosts (like Render) remain awake indefinitely using free uptime pingers.

---

## Quick Webhook Setup Guide

The simplest and most reliable way to set this up for your Discord server is using **Webhook Mode**. This requires no bot inviting, no permissions, and runs in under 3 minutes.

### Step 1: Create a Discord Webhook
1. Open Discord and go to your server's target channel (e.g., `#instagram-updates` or `#testing-bot`).
2. Click the gear icon next to the channel name to open **Channel Settings**.
3. Go to **Integrations** > **Webhooks** > **New Webhook**.
4. Name the webhook (e.g., `Citadel Herald`), choose your channel, and click **Copy Webhook URL**.

### Step 2: Deploy to Render for Free
1. Fork or push this repository to your GitHub account.
2. Log in to [Render Dashboard](https://dashboard.render.com/) and click **New +** > **Web Service**.
3. Select your repository.
4. Configure the service settings:
   - **Name:** `instagram-discord-bot` (or any preferred name)
   - **Runtime:** `Python 3`
   - **Branch:** `main`
   - **Root Directory:** *(leave completely blank)*
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python src/main.py`
   - **Instance Type:** `Free ($0/month)`
5. Under **Environment Variables**, add:
   - `DISCORD_WEBHOOK_URL`: *(paste the Webhook URL from Step 1)*
   - `INSTAGRAM_HOURS`: `1` *(checks every 1 hour; use `0.5` for 30 minutes)*
6. Click **Deploy Web Service**.

### Step 3: Keep 24/7 Active via Free Uptime Monitor
Render's free tier idles web services after 15 minutes of inactivity. To prevent it from ever sleeping:
1. Copy your Render web service URL (e.g., `https://your-bot-name.onrender.com`).
2. Go to [UptimeRobot](https://uptimerobot.com) (free) or [cron-job.org](https://cron-job.org).
3. Create a free monitor:
   - **Monitor Type:** `HTTP(s)`
   - **URL:** `https://your-bot-name.onrender.com/health`
   - **Monitoring Interval:** Every `5 minutes` or `10 minutes`
4. Save the monitor. UptimeRobot will ping the health endpoint on schedule, keeping your bot alive 24/7 for free.

---

## The Citadel Web Dashboard

Every deployment serves a web control interface at the root URL of your service (e.g., `https://your-bot-name.onrender.com/`).

From this page, administrators can:
- Check server health and tracked feeds at a glance.
- Click **"Dispatch Ravens Now"** to immediately fetch and broadcast the latest posts to Discord without touching a terminal.
- Works from desktop browsers, iOS Safari, or Android Chrome.

---

## Local Testing and Commands

If running locally on macOS or Linux:

### One-Click Desktop Shortcut
On macOS, double-click `Test-Bot.command` in the project root. It will execute a test delivery of all tracked accounts directly to your webhook.

### Command Line Testing
To test sending via webhook directly:
```bash
python test_send.py "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"
```

To test a specific single account:
```bash
python test_send.py "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL" houseofthedragonhbo
```

---

## Configuration Reference

Settings can be managed either via `config.yaml` or as environment variables:

| Environment Variable | `config.yaml` Key | Description | Default |
| :--- | :--- | :--- | :--- |
| `DISCORD_WEBHOOK_URL` | `DISCORD.WEBHOOK_URL` | Discord Webhook URL for posting updates | `""` |
| `DISCORD_USE_WEBHOOK_PROFILE` | `DISCORD.USE_WEBHOOK_PROFILE` | Use webhook name and avatar configured in Discord | `true` |
| `DISCORD_TOKEN` | `DISCORD.TOKEN` | Bot token (if using Bot Token mode instead of Webhook) | `""` |
| `DISCORD_GUILD_NAME` | `DISCORD.GUILD_NAME` | Server name (for Bot Token mode) | `""` |
| `INSTAGRAM_CHANNEL` | `INSTAGRAM.CHANNEL` | Channel name (for Bot Token mode) | `""` |
| `INSTAGRAM_HOURS` | `INSTAGRAM.HOURS` | Frequency of checks in hours | `1` |
| `INSTAGRAM_SESSION_ID`| `INSTAGRAM.SESSION_ID` | (Optional) `sessionid` cookie from a burner IG account | `""` |

### Tracked Accounts
Configured under `USERNAMES` in `config.yaml`:
```yaml
INSTAGRAM:
  USERNAMES:
    - "gameofthrones"
    - "houseofthedragonhbo"
    - "aknightofthe7kingdomshbo"
    - "westerosies"
```

---

## License
MIT License.
