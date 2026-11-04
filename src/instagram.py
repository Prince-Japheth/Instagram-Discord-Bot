import asyncio
import io
import json
import os
import re
import ssl
import urllib.request
from datetime import datetime
import yaml
import requests
import discord
from discord.ext import commands
from discord.ext.tasks import loop

# Load configuration with fallback to environment variables
config = {}
if os.path.exists("config.yaml"):
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.full_load(f) or {}

DISCORD_CFG = config.get("DISCORD", {})
INSTA_CFG = config.get("INSTAGRAM", {})

GUILD_NAME = os.getenv("DISCORD_GUILD_NAME", DISCORD_CFG.get("GUILD_NAME", ""))
CHANNEL_NAME = os.getenv("INSTAGRAM_CHANNEL", INSTA_CFG.get("CHANNEL", ""))
CHECK_HOURS = float(os.getenv("INSTAGRAM_HOURS", INSTA_CFG.get("HOURS", 1)))
SESSION_ID = os.getenv("INSTAGRAM_SESSION_ID", INSTA_CFG.get("SESSION_ID", ""))

# Support both list USERNAMES and legacy single USERNAME
RAW_USERS = INSTA_CFG.get("USERNAMES") or INSTA_CFG.get("USERNAME") or [
    "gameofthrones",
    "houseofthedragonhbo",
    "aknightofthe7kingdomshbo",
    "westerosies",
]
if isinstance(RAW_USERS, str):
    TARGET_USERS = [u.strip() for u in RAW_USERS.split(",") if u.strip()]
else:
    TARGET_USERS = list(RAW_USERS)

# High-availability RSS-Bridge instances for anonymous public Instagram access
BRIDGE_HOSTS = [
    "https://rss-bridge.sans-nuage.fr",
    "https://wtf.roflcopter.fr/rss-bridge",
]

SSL_CTX = ssl._create_unverified_context()
REQ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def _fetch_from_bridge_sync(username: str):
    """Fetch latest post from public bridge instances without login, supporting carousels."""
    for host in BRIDGE_HOSTS:
        url = f"{host}/?action=display&bridge=Instagram&context=Username&u={username}&format=Json"
        try:
            req = urllib.request.Request(url, headers=REQ_HEADERS)
            with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                items = data.get("items", [])
                if not items:
                    continue

                latest = items[0]
                post_url = latest.get("url") or latest.get("id", "")
                match = re.search(r"/p/([A-Za-z0-9_-]+)", post_url)
                shortcode = match.group(1) if match else post_url

                # Extract all image attachments for carousel support
                image_urls = []
                attachments = latest.get("attachments", [])
                if attachments and isinstance(attachments, list):
                    for att in attachments:
                        u = att.get("url")
                        if u and u not in image_urls:
                            image_urls.append(u)

                if not image_urls and post_url:
                    image_urls.append(f"{post_url.rstrip('/')}/media/?size=l")

                # Parse date
                date_str = latest.get("date_modified")
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except Exception:
                    dt = datetime.utcnow()

                caption = latest.get("title", "")

                return {
                    "username": username,
                    "shortcode": shortcode,
                    "post_url": post_url,
                    "caption": caption,
                    "display_url": image_urls[0] if image_urls else None,
                    "images": image_urls,
                    "is_carousel": len(image_urls) > 1,
                    "timestamp": dt,
                    "acc_url": f"https://www.instagram.com/{username}/",
                }
        except Exception:
            continue

    return None


def _fetch_with_instaloader_sync(username: str, session_id: str):
    """Fallback fetcher using Instaloader when a sessionid is provided."""
    import instaloader

    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    loader.context._session.cookies.set(
        "sessionid", session_id, domain=".instagram.com"
    )

    profile = instaloader.Profile.from_username(loader.context, username)
    for post in profile.get_posts():
        image_urls = [post.url]
        return {
            "username": profile.username,
            "shortcode": post.shortcode,
            "post_url": f"https://www.instagram.com/p/{post.shortcode}/",
            "caption": post.caption or "",
            "display_url": post.url,
            "images": image_urls,
            "is_carousel": False,
            "timestamp": post.date_utc,
            "acc_url": f"https://www.instagram.com/{profile.username}/",
        }
    return None


def fetch_latest_post_sync(username: str, session_id: str = ""):
    """Combines authenticated instaloader with anonymous bridge fallbacks."""
    if session_id:
        try:
            res = _fetch_with_instaloader_sync(username, session_id)
            if res:
                return res
        except Exception as e:
            print(f"[Instagram Cog] Instaloader session fetch failed: {e}. Trying bridge...")

    return _fetch_from_bridge_sync(username)


def _download_image_bytes(url: str):
    """Safely downloads image data as bytes with timeout and fallback."""
    try:
        req = urllib.request.Request(url, headers=REQ_HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as resp:
            return resp.read()
    except Exception:
        pass

    try:
        r = requests.get(url, headers=REQ_HEADERS, timeout=15)
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        pass

    return None


class Instagram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_shortcodes = {}
        self.check_posts.change_interval(hours=CHECK_HOURS)
        self.check_posts.start()

    def cog_unload(self):
        self.check_posts.cancel()

    async def get_latest_post(self, username: str):
        """Runs the network fetch in a background thread executor."""
        loop_obj = asyncio.get_running_loop()
        try:
            return await loop_obj.run_in_executor(
                None, fetch_latest_post_sync, username, SESSION_ID
            )
        except Exception as e:
            print(f"[Instagram Cog] Warning: Failed to fetch posts for @{username}: {e}")
            return None

    @loop(hours=1)
    async def check_posts(self):
        """Periodically checks if new Instagram posts have been uploaded."""
        channel = discord.utils.get(
            self.bot.get_all_channels(),
            guild__name=GUILD_NAME,
            name=CHANNEL_NAME,
        )

        if not channel:
            print(
                f"[Instagram Cog] Could not find channel '{CHANNEL_NAME}' in guild '{GUILD_NAME}'."
            )
            return

        for username in TARGET_USERS:
            try:
                post = await self.get_latest_post(username)
                if not post:
                    continue

                shortcode = post["shortcode"]
                post_url = post["post_url"]

                # In-memory deduplication check
                if self.last_shortcodes.get(username) == shortcode:
                    continue

                # Channel history deduplication check
                already_posted = False
                async for message in channel.history(limit=40):
                    if message.author.id == self.bot.user.id and message.embeds:
                        embed = message.embeds[0]
                        if embed.url == post_url:
                            already_posted = True
                            break
                        if embed.author and embed.author.name.lower() == username.lower():
                            if shortcode in (embed.description or "") or embed.url == post_url:
                                already_posted = True
                                break

                if already_posted:
                    self.last_shortcodes[username] = shortcode
                    continue

                # Prepare post details
                formatted_time = post["timestamp"].strftime("%Y-%m-%d %H:%M UTC")
                caption = post["caption"]
                if len(caption) > 1000:
                    caption = caption[:997] + "..."

                images = post.get("images", [])
                total_slides = len(images)
                loop_obj = asyncio.get_running_loop()

                # Case 1: Carousel post (multiple images)
                if total_slides > 1:
                    # Discord allows at most 10 embeds/files per individual message.
                    # We chunk into batches of 10 so carousels of 10+ slides (up to Instagram's 20 limit) are completely sent.
                    CHUNK_SIZE = 10
                    for chunk_idx, i in enumerate(range(0, total_slides, CHUNK_SIZE)):
                        chunk_images = images[i:i + CHUNK_SIZE]
                        download_tasks = [
                            loop_obj.run_in_executor(None, _download_image_bytes, url)
                            for url in chunk_images
                        ]
                        downloaded_bytes = await asyncio.gather(*download_tasks)

                        embeds = []
                        files = []
                        for sub_idx, img_data in enumerate(downloaded_bytes):
                            if not img_data:
                                continue
                            slide_num = i + sub_idx + 1
                            filename = f"slide_{slide_num}.jpg"
                            files.append(discord.File(io.BytesIO(img_data), filename=filename))

                            # Multiple embeds sharing the same URL form a Discord Gallery Grid
                            e = discord.Embed(url=post_url, color=0xDD2A7B)
                            e.set_image(url=f"attachment://{filename}")

                            # Main embed details on first slide of first chunk
                            if sub_idx == 0 and chunk_idx == 0:
                                e.title = f"New Instagram post ({formatted_time})"
                                desc = caption if caption else "*(No caption)*"
                                e.description = f"{desc}\n\n[View all {total_slides} slides on Instagram ↗]({post_url})"
                                e.set_author(name=f"@{post['username']}", url=post["acc_url"])
                                e.set_footer(text=f"All {total_slides} slides attached • Click any image to view all slides")
                            elif sub_idx == 0:
                                e.title = f"Post continuation (Slides {i+1}–{min(i+CHUNK_SIZE, total_slides)})"
                                e.set_footer(text=f"Slides {i+1} to {min(i+CHUNK_SIZE, total_slides)} of {total_slides}")

                            embeds.append(e)

                        if embeds:
                            await channel.send(embeds=embeds, files=files)
                        await asyncio.sleep(1)
                    else:
                        single_embed = discord.Embed(
                            title=f"New Instagram post ({formatted_time})",
                            description=caption,
                            url=post_url,
                            color=0xDD2A7B,
                        )
                        single_embed.set_author(name=f"@{post['username']}", url=post["acc_url"])
                        if post.get("display_url"):
                            single_embed.set_image(url=post["display_url"])
                        single_embed.set_footer(text=f"Carousel ({total_slides} slides)")
                        await channel.send(embed=single_embed)

                # Case 2: Single-image post
                else:
                    embed = discord.Embed(
                        title=f"New Instagram post ({formatted_time})",
                        description=caption if caption else "*(No caption)*",
                        url=post_url,
                        color=0xDD2A7B,
                    )
                    embed.set_author(name=f"@{post['username']}", url=post["acc_url"])

                    file_attachment = None
                    if post.get("display_url"):
                        img_data = await loop_obj.run_in_executor(
                            None, _download_image_bytes, post["display_url"]
                        )
                        if img_data:
                            file_attachment = discord.File(io.BytesIO(img_data), filename="post.jpg")
                            embed.set_image(url="attachment://post.jpg")
                        else:
                            embed.set_image(url=post["display_url"])

                    if file_attachment:
                        await channel.send(embed=embed, file=file_attachment)
                    else:
                        await channel.send(embed=embed)

                self.last_shortcodes[username] = shortcode
                print(
                    f"[Instagram Cog] Successfully posted update for @{username} ({shortcode}, carousel={total_slides > 1})"
                )

                # Small delay between multiple accounts
                await asyncio.sleep(4)

            except Exception as e:
                print(f"[Instagram Cog] Error processing @{username}: {e}")

    @check_posts.before_loop
    async def before_check_posts(self):
        """Wait until the bot is completely logged in and connected."""
        await self.bot.wait_until_ready()


def send_post_via_webhook(webhook_url: str, post: dict):
    """Sends a single Instagram post as an embed (or gallery if carousel) to Discord via Webhook.
    Handles carousels of any size by chunking into batches of 10 if necessary (Discord's per-message limit).
    """
    username = post["username"]
    post_url = post["post_url"]
    caption = post["caption"]
    formatted_time = post["timestamp"].strftime("%Y-%m-%d %H:%M UTC")

    images = post.get("images", [])
    if not images and post.get("display_url"):
        images = [post["display_url"]]

    total_slides = len(images)
    CHUNK_SIZE = 10

    avatars = {
        "gameofthrones": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Game_of_Thrones_2011_logo.svg/800px-Game_of_Thrones_2011_logo.svg.png",
        "houseofthedragonhbo": "https://upload.wikimedia.org/wikipedia/en/thumb/9/92/House_of_the_Dragon_title_card.png/800px-House_of_the_Dragon_title_card.png",
        "aknightofthe7kingdomshbo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Game_of_Thrones_2011_logo.svg/800px-Game_of_Thrones_2011_logo.svg.png",
        "westerosies": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Game_of_Thrones_2011_logo.svg/800px-Game_of_Thrones_2011_logo.svg.png",
    }
    avatar = avatars.get(username.lower(), "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Instagram_logo_2016.svg/800px-Instagram_logo_2016.svg.png")

    display_names = {
        "gameofthrones": "Game of Thrones",
        "houseofthedragonhbo": "House of the Dragon",
        "aknightofthe7kingdomshbo": "A Knight of the Seven Kingdoms",
        "westerosies": "Westerosies",
    }
    display_name = display_names.get(username.lower(), f"@{username}")

    print(f"[Webhook] Packaging {total_slides} slide(s) for @{username}...")

    # Chunk slides into batches of 10 for Discord
    for chunk_idx, i in enumerate(range(0, max(1, total_slides), CHUNK_SIZE)):
        chunk_images = images[i:i + CHUNK_SIZE] if images else []
        files_payload = {}
        embeds_payload = []

        for sub_idx, img_url in enumerate(chunk_images):
            img_data = _download_image_bytes(img_url)
            if not img_data:
                print(f"  [Warning] Failed to download slide {i + sub_idx + 1}")
                continue

            slide_num = i + sub_idx + 1
            filename = f"slide_{slide_num}.jpg"
            files_payload[f"files[{sub_idx}]"] = (filename, img_data, "image/jpeg")

            embed = {
                "url": post_url,
                "image": {"url": f"attachment://{filename}"}
            }

            if sub_idx == 0 and chunk_idx == 0:
                embed["title"] = f"New Instagram post ({formatted_time})"
                caption_text = caption[:900] if caption else "*(No caption)*"
                if total_slides > 1:
                    embed["description"] = f"{caption_text}\n\n[View all {total_slides} slides on Instagram ↗]({post_url})"
                    embed["footer"] = {
                        "text": f"All {total_slides} slides attached • Click any image to view all slides"
                    }
                else:
                    embed["description"] = f"{caption_text}\n\n[View on Instagram ↗]({post_url})"

                embed["color"] = 14494331
                embed["author"] = {
                    "name": f"@{username}",
                    "url": post["acc_url"],
                }
            elif sub_idx == 0:
                embed["title"] = f"Post continuation (Slides {i+1}–{min(i+CHUNK_SIZE, total_slides)})"
                embed["footer"] = {
                    "text": f"Slides {i+1} to {min(i+CHUNK_SIZE, total_slides)} of {total_slides}"
                }
                embed["color"] = 14494331

            embeds_payload.append(embed)

        payload = {
            "username": display_name,
            "avatar_url": avatar,
            "embeds": embeds_payload if embeds_payload else [
                {
                    "title": f"New Instagram post ({formatted_time})",
                    "url": post_url,
                    "description": f"{caption}\n\n[View on Instagram ↗]({post_url})",
                    "color": 14494331,
                    "author": {"name": f"@{username}", "url": post["acc_url"]}
                }
            ]
        }

        if files_payload:
            files_payload["payload_json"] = (None, json.dumps(payload), "application/json")
            resp = requests.post(webhook_url, files=files_payload)
        else:
            resp = requests.post(webhook_url, json=payload)

        if resp.status_code in [200, 204]:
            print(f"[Success] Delivered chunk {chunk_idx + 1} for @{username} to Discord webhook.")
        else:
            print(f"[Error] Discord error for @{username}: {resp.status_code} - {resp.text}")


def setup(bot):
    bot.add_cog(Instagram(bot))
