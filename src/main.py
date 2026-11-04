#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path
import yaml
from aiohttp import web
import discord
from discord.ext import commands

# Ensure src/ directory is in sys.path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Load config with fallback to environment variables
config = {}
if os.path.exists("config.yaml"):
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.full_load(f) or {}

DISCORD_CFG = config.get("DISCORD", {})
TOKEN = os.getenv("DISCORD_TOKEN", DISCORD_CFG.get("TOKEN", ""))
GUILD_NAME = os.getenv("DISCORD_GUILD_NAME", DISCORD_CFG.get("GUILD_NAME", ""))
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", DISCORD_CFG.get("WEBHOOK_URL", ""))

# Configure Discord Bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Triggered when the bot successfully connects to Discord."""
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    guild_info = f"{guild.name} (id: {guild.id})" if guild else f"'{GUILD_NAME}' (not found yet)"
    print(f"\n[Bot Ready] Logged in as: {bot.user} | Guild: {guild_info}\n")


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Instagram Discord Bot Dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      min-height: 100vh;
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 32px;
      max-width: 460px;
      width: 100%;
      text-align: center;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #064e3b;
      color: #34d399;
      font-size: 0.8rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 9999px;
      margin-bottom: 16px;
    }
    .badge-dot {
      width: 8px;
      height: 8px;
      background: #34d399;
      border-radius: 50%;
      box-shadow: 0 0 8px #34d399;
    }
    h1 { margin: 0 0 10px; font-size: 1.5rem; color: #f8fafc; }
    p { color: #94a3b8; font-size: 0.92rem; line-height: 1.5; margin: 0 0 20px; }
    .feeds {
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 0.88rem;
      color: #cbd5e1;
      margin-bottom: 20px;
      text-align: left;
    }
    .feeds strong { color: #38bdf8; }
    .btn {
      width: 100%;
      background: linear-gradient(135deg, #e1306c 0%, #f77737 100%);
      color: white;
      border: none;
      padding: 14px 20px;
      font-size: 1rem;
      font-weight: 600;
      border-radius: 10px;
      cursor: pointer;
      transition: transform 0.1s, opacity 0.2s;
    }
    .btn:hover { opacity: 0.92; }
    .btn:active { transform: scale(0.98); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }
    .status {
      margin-top: 20px;
      padding: 12px;
      border-radius: 8px;
      background: #0f172a;
      border: 1px solid #334155;
      font-size: 0.85rem;
      color: #38bdf8;
      text-align: left;
      white-space: pre-wrap;
      display: none;
      line-height: 1.4;
    }
    .spinner {
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      vertical-align: middle;
      margin-right: 8px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge"><span class="badge-dot"></span> 24/7 Service Online</div>
    <h1>Instagram Bot</h1>
    <p>Automated feed monitor running 24/7 on Render. Use the button below to trigger an immediate manual check.</p>
    
    <div class="feeds">
      <strong>Tracked Feeds:</strong> @gameofthrones, @houseofthedragonhbo
    </div>

    <button class="btn" id="btn" onclick="sendNow()">Send Latest Posts to Discord</button>
    <div class="status" id="status"></div>
  </div>

  <script>
    async function sendNow() {
      const btn = document.getElementById('btn');
      const status = document.getElementById('status');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span>Fetching & sending to Discord...';
      status.style.display = 'block';
      status.textContent = 'Contacting Instagram and packaging carousel slides...';

      try {
        const res = await fetch('/trigger', { method: 'POST' });
        const data = await res.json();
        status.textContent = data.message || JSON.stringify(data);
      } catch (err) {
        status.textContent = 'Error: ' + err.message;
      } finally {
        btn.disabled = false;
        btn.innerHTML = 'Send Latest Posts to Discord';
      }
    }
  </script>
</body>
</html>
"""


async def dashboard_handler(request):
    """Serves the one-click control dashboard."""
    return web.Response(text=DASHBOARD_HTML, content_type="text/html")


async def health_check_handler(request):
    """Health check endpoint for UptimeRobot and Render."""
    return web.Response(text="Instagram Discord Bot is running healthy!\n")


async def trigger_handler(request):
    """Manual trigger: immediately fetches and sends the latest posts to Discord."""
    from instagram import (
        fetch_latest_post_sync,
        send_post_via_webhook,
        TARGET_USERS,
        SESSION_ID,
    )

    if not WEBHOOK_URL:
        return web.json_response({
            "status": "error",
            "message": "DISCORD_WEBHOOK_URL is not set."
        }, status=400)

    loop_obj = asyncio.get_running_loop()
    results = []

    for username in TARGET_USERS:
        try:
            print(f"[Manual Trigger] Fetching latest post for @{username}...")
            post = await loop_obj.run_in_executor(
                None, fetch_latest_post_sync, username, SESSION_ID
            )
            if post:
                await loop_obj.run_in_executor(
                    None, send_post_via_webhook, WEBHOOK_URL, post
                )
                slides_count = len(post.get("images", []))
                results.append(f"[Success] Sent @{username}: {slides_count} slide(s) delivered to Discord.")
            else:
                results.append(f"[Warning] Could not fetch post for @{username} at this time.")
        except Exception as e:
            results.append(f"[Error] Failed for @{username}: {e}")
        await asyncio.sleep(2)

    return web.json_response({
        "status": "ok",
        "message": "\n".join(results)
    })


async def start_web_server():
    """Runs a lightweight HTTP server with a dashboard, health check, and trigger endpoint."""
    app = web.Application()
    app.router.add_get("/", dashboard_handler)
    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/trigger", trigger_handler)
    app.router.add_post("/trigger", trigger_handler)

    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[Web Server] Dashboard and health endpoint listening on port {port}")


async def run_webhook_loop():
    """Autonomous scheduler loop that posts updates directly via Webhook without needing a bot token."""
    from instagram import (
        fetch_latest_post_sync,
        send_post_via_webhook,
        TARGET_USERS,
        CHECK_HOURS,
        SESSION_ID,
    )

    print(f"[Webhook Mode] Starting loop checking {TARGET_USERS} every {CHECK_HOURS} hour(s)...")
    last_shortcodes = {}
    loop_obj = asyncio.get_running_loop()

    while True:
        for username in TARGET_USERS:
            try:
                print(f"[Webhook Mode] Checking posts for @{username}...")
                post = await loop_obj.run_in_executor(
                    None, fetch_latest_post_sync, username, SESSION_ID
                )
                if post:
                    shortcode = post["shortcode"]
                    if last_shortcodes.get(username) != shortcode:
                        await loop_obj.run_in_executor(
                            None, send_post_via_webhook, WEBHOOK_URL, post
                        )
                        last_shortcodes[username] = shortcode
                        print(f"[Webhook Mode] Successfully delivered @{username} ({shortcode})")
                    else:
                        print(f"[Webhook Mode] No new post for @{username} (already posted {shortcode})")
            except Exception as e:
                print(f"[Webhook Mode] Error processing @{username}: {e}")
            await asyncio.sleep(4)

        sleep_seconds = int(CHECK_HOURS * 3600)
        print(f"[Webhook Mode] Check complete. Next check in {CHECK_HOURS} hour(s)...")
        await asyncio.sleep(sleep_seconds)


async def main():
    # 1. Start the keep-alive web server
    await start_web_server()

    # Mode A: If a Discord Webhook URL is provided, run the autonomous webhook loop
    if WEBHOOK_URL:
        print("[Mode] Running in Discord Webhook mode (no bot token required).")
        await run_webhook_loop()
        return

    # Mode B: If Discord Bot Token is provided, run the py-cord bot
    if not TOKEN or TOKEN == "Your discord bot token":
        print(
            "ERROR: Neither DISCORD_TOKEN nor DISCORD_WEBHOOK_URL was provided!\n"
            "Please set DISCORD_WEBHOOK_URL or DISCORD_TOKEN in config.yaml or as environment variables."
        )
        sys.exit(1)

    # Load Instagram Cog
    try:
        bot.load_extension("instagram")
        print("[Extensions] Instagram cog loaded successfully.")
    except Exception:
        try:
            bot.load_extension("src.instagram")
            print("[Extensions] Instagram cog loaded successfully.")
        except Exception as e:
            print(f"[Extensions] Error loading Instagram cog: {e}")

    # Start Discord Bot
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nBot shutting down gracefully.")
