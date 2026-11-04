#!/usr/bin/env python3
"""Quick script to test sending live Instagram posts directly to your Discord channel.
Can test via Discord Webhook URL or via Discord Bot Token.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
import yaml
import requests

# Ensure src/ is in path for both IDE resolution and direct execution
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.instagram import (
    fetch_latest_post_sync,
    _download_image_bytes,
    send_post_via_webhook,
)


async def main():
    # Load configuration
    config = {}
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = yaml.full_load(f) or {}

    INSTA_CFG = config.get("INSTAGRAM", {})
    raw_users = INSTA_CFG.get("USERNAMES") or INSTA_CFG.get("USERNAME") or ["gameofthrones", "houseofthedragonhbo"]
    if isinstance(raw_users, str):
        target_users = [u.strip() for u in raw_users.split(",") if u.strip()]
    else:
        target_users = list(raw_users)

    # 1. If Webhook URL is supplied via CLI arguments
    if len(sys.argv) > 1 and "discord.com/api/webhooks" in sys.argv[1]:
        webhook_url = sys.argv[1]
        print(f"Testing via Discord Webhook: {webhook_url[:50]}...")
        
        # Check which account(s) to test
        users_to_test = [sys.argv[2]] if len(sys.argv) > 2 else target_users

        for username in users_to_test:
            print(f"\nFetching latest post for @{username}...")
            post = fetch_latest_post_sync(username)
            if post:
                send_post_via_webhook(webhook_url, post)
            else:
                print(f"[Warning] Could not fetch latest post for @{username} at this time.")
        return

    # 2. Otherwise test via Bot Token from config.yaml
    import discord
    token = os.getenv("DISCORD_TOKEN", config.get("DISCORD", {}).get("TOKEN", ""))
    guild_name = os.getenv("DISCORD_GUILD_NAME", config.get("DISCORD", {}).get("GUILD_NAME", ""))
    channel_name = os.getenv("INSTAGRAM_CHANNEL", config.get("INSTAGRAM", {}).get("CHANNEL", ""))

    if not token or token == "Your discord bot token":
        print("Error: Please set your bot token in config.yaml or pass a webhook URL.")
        sys.exit(1)

    print("Connecting to Discord with Bot Token...")
    intents = discord.Intents.default()
    bot = discord.Client(intents=intents)

    @bot.event
    async def on_ready():
        print(f"Connected as bot: {bot.user}")
        guild = discord.utils.get(bot.guilds, name=guild_name)
        if not guild:
            print(f"Server '{guild_name}' not found.")
            await bot.close()
            return
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            print(f"Channel '{channel_name}' not found in '{guild.name}'.")
            await bot.close()
            return

        for username in target_users:
            print(f"Fetching latest post for @{username}...")
            post = fetch_latest_post_sync(username)
            if post:
                # Send to channel
                pass

        await bot.close()

    await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
