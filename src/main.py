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
  <title>Instagram Feed Monitor</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;800&family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'EB Garamond', Georgia, serif;
      background: #08090b;
      background-image: 
        radial-gradient(ellipse at 50% 20%, rgba(139, 30, 30, 0.12), transparent 70%),
        radial-gradient(circle at 50% 100%, rgba(20, 24, 33, 0.8), #08090b 80%);
      color: #d1c7b7;
      min-height: 100vh;
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    .sigil-frame {
      background: #0f1115;
      border: 1px solid #3d3428;
      outline: 1px solid #1f1b15;
      outline-offset: -5px;
      border-radius: 4px;
      padding: 40px 32px;
      max-width: 480px;
      width: 100%;
      text-align: center;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.95), 0 0 1px 1px rgba(197, 160, 89, 0.15);
      position: relative;
    }
    .sigil-frame::before {
      content: "";
      position: absolute;
      top: -1px; left: 50%;
      transform: translateX(-50%);
      width: 60px;
      height: 2px;
      background: #c5a059;
    }
    .sigil-frame::after {
      content: "";
      position: absolute;
      bottom: -1px; left: 50%;
      transform: translateX(-50%);
      width: 60px;
      height: 2px;
      background: #c5a059;
    }
    .sub-title {
      font-family: 'Cinzel', serif;
      font-size: 0.72rem;
      letter-spacing: 0.28em;
      text-transform: uppercase;
      color: #9c8353;
      margin-bottom: 8px;
    }
    h1 {
      font-family: 'Cinzel', serif;
      font-weight: 700;
      font-size: 1.65rem;
      letter-spacing: 0.08em;
      color: #f1e9da;
      margin: 0 0 12px;
      text-shadow: 0 2px 4px rgba(0,0,0,0.8);
    }
    .divider {
      height: 1px;
      background: linear-gradient(90deg, transparent, #6b5736, #c5a059, #6b5736, transparent);
      margin: 20px 0;
      border: 0;
    }
    p {
      color: #a39785;
      font-size: 0.98rem;
      line-height: 1.6;
      margin: 0 0 24px;
    }
    .ledger {
      background: #090a0d;
      border: 1px solid #29241d;
      border-radius: 2px;
      padding: 14px 18px;
      margin-bottom: 24px;
      text-align: left;
    }
    .ledger-header {
      font-family: 'Cinzel', serif;
      font-size: 0.68rem;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: #8c764e;
      margin-bottom: 8px;
    }
    .ledger-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 5px 0;
      font-size: 0.88rem;
      color: #c7bcab;
      border-bottom: 1px dashed #1c1a16;
    }
    .ledger-item:last-child { border-bottom: none; }
    .house-name {
      font-family: 'Cinzel', serif;
      font-size: 0.78rem;
      letter-spacing: 0.06em;
      color: #e5dcce;
    }
    .handle {
      color: #bfa163;
      font-family: monospace;
      font-size: 0.82rem;
    }
    .btn-dispatch {
      width: 100%;
      background: #3b0c13;
      border: 1px solid #8f2635;
      color: #f3ebd9;
      font-family: 'Cinzel', serif;
      font-size: 0.84rem;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      padding: 15px 24px;
      border-radius: 2px;
      cursor: pointer;
      transition: all 0.25s ease;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    }
    .btn-dispatch:hover {
      background: #54111c;
      border-color: #c5a059;
      color: #ffffff;
      box-shadow: 0 0 18px rgba(197, 160, 89, 0.25);
    }
    .btn-dispatch:active {
      transform: translateY(1px);
    }
    .btn-dispatch:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      border-color: #443c32;
    }
    .status-chronicle {
      margin-top: 20px;
      padding: 14px 16px;
      background: #07080a;
      border: 1px solid #2a251e;
      border-radius: 2px;
      font-size: 0.85rem;
      color: #bfa163;
      text-align: left;
      white-space: pre-wrap;
      display: none;
      line-height: 1.5;
      font-family: 'EB Garamond', Georgia, serif;
    }
    .spinner {
      display: inline-block;
      width: 12px;
      height: 12px;
      border: 2px solid rgba(197, 160, 89, 0.25);
      border-top-color: #c5a059;
      border-radius: 50%;
      animation: spin 0.9s linear infinite;
      vertical-align: middle;
      margin-right: 8px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .seal-footer {
      margin-top: 22px;
      font-family: 'Cinzel', serif;
      font-size: 0.65rem;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      color: #5c5244;
    }
  </style>
</head>
<body>
  <div class="sigil-frame">
    <div class="sub-title">Game of Thrones &bull; House of the Dragon</div>
    <h1>Instagram Feed Monitor</h1>
    <div class="divider"></div>
    <p>Automated feed monitor broadcasting new posts to your Discord channel. Use the button below to perform a manual check.</p>
    
    <div class="ledger">
      <div class="ledger-header">Tracked Feeds</div>
      <div class="ledger-item">
        <span class="house-name">House of the Dragon</span>
        <span class="handle">@houseofthedragonhbo</span>
      </div>
      <div class="ledger-item">
        <span class="house-name">Game of Thrones</span>
        <span class="handle">@gameofthrones</span>
      </div>
    </div>

    <button class="btn-dispatch" id="btn" onclick="sendNow()">Send Latest Posts to Discord</button>
    <div class="status-chronicle" id="status"></div>

    <div class="seal-footer">Active 24/7</div>
  </div>

  <script>
    async function sendNow() {
      const btn = document.getElementById('btn');
      const status = document.getElementById('status');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span>Fetching latest posts...';
      status.style.display = 'block';
      status.textContent = 'Contacting Instagram feeds and packaging posts...';

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

    # Establish baseline on boot so we do not re-send existing posts on deploy or restart
    print("[Webhook Mode] Establishing initial baseline for tracked feeds...")
    for username in TARGET_USERS:
        try:
            post = await loop_obj.run_in_executor(
                None, fetch_latest_post_sync, username, SESSION_ID
            )
            if post:
                last_shortcodes[username] = post["shortcode"]
                print(f"[Webhook Mode] Baseline recorded for @{username}: {post['shortcode']}")
        except Exception as e:
            print(f"[Webhook Mode] Could not establish baseline for @{username}: {e}")
        await asyncio.sleep(2)

    sleep_seconds = int(CHECK_HOURS * 3600)
    print(f"[Webhook Mode] Baseline complete. Monitoring for NEW posts every {CHECK_HOURS} hour(s)...")
    await asyncio.sleep(sleep_seconds)

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
                        print(f"[Webhook Mode] Successfully delivered new post for @{username} ({shortcode})")
                    else:
                        print(f"[Webhook Mode] No new post for @{username} (already posted {shortcode})")
            except Exception as e:
                print(f"[Webhook Mode] Error processing @{username}: {e}")
            await asyncio.sleep(4)

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
