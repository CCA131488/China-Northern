import discord
from discord.ext import tasks
import requests
from datetime import datetime, timedelta
import os

# Configuration
GITHUB_REPO_OWNER = "CCA131488"
GITHUB_REPO_NAME = "China-Northern"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/commits"
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "YOUR_DISCORD_BOT_TOKEN_HERE")
DISCORD_CHANNEL_ID = 1434461852490010624
BOT_NAME = "GitHub"
BOT_AVATAR_URL = "https://raw.githubusercontent.com/CCA131488/China-Northern/refs/heads/main/logo.png"
CHECK_INTERVAL = 30  # Check for new commits every 30 seconds
LAST_COMMIT_HASH_FILE = "last_commit_hash.txt"

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents, activity=discord.Activity(type=discord.ActivityType.watching, name=f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME} Commits"))

def load_last_commit_hash():
    """Load the last recorded commit hash from file"""
    if os.path.exists(LAST_COMMIT_HASH_FILE):
        with open(LAST_COMMIT_HASH_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_commit_hash(hash):
    """Save the latest commit hash to file"""
    with open(LAST_COMMIT_HASH_FILE, "w") as f:
        f.write(hash)

def fetch_latest_commits():
    """Fetch latest commits from GitHub API"""
    try:
        response = requests.get(GITHUB_API_URL, headers={"Accept": "application/vnd.github.v3+json"})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching commits: {e}")
        return []

@tasks.loop(seconds=CHECK_INTERVAL)
async def monitor_commits():
    """Monitor GitHub repository for new commits"""
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        print(f"Could not find Discord channel with ID: {DISCORD_CHANNEL_ID}")
        return

    last_commit_hash = load_last_commit_hash()
    commits = fetch_latest_commits()

    if not commits:
        return

    # Process commits in reverse order (oldest to newest)
    for commit in reversed(commits):
        current_hash = commit["sha"]
        # Stop if we reach the last processed commit
        if current_hash == last_commit_hash:
            break

        # Extract commit details
        committer_name = commit["commit"]["committer"]["name"]
        committer_avatar = commit["author"]["avatar_url"] if commit.get("author") else BOT_AVATAR_URL
        commit_url = commit["html_url"]
        commit_hash_short = current_hash[:7]
        commit_message = commit["commit"]["message"].split("\n")[0]  # Get first line of message
        commit_timestamp = datetime.strptime(commit["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ")

        # Create Discord embed
        embed = discord.Embed(
            title=f"New Commit: {commit_message}",
            url=commit_url,
            color=discord.Color(0x24292e),  # GitHub dark gray color
            timestamp=commit_timestamp
        )
        embed.set_author(name=committer_name, icon_url=committer_avatar)
        embed.add_field(name="Commit ID", value=f"`{commit_hash_short}`", inline=False)
        embed.add_field(name="Commit Link", value=commit_url, inline=False)
        embed.set_footer(text=BOT_NAME, icon_url=BOT_AVATAR_URL)

        # Send message to Discord channel
        await channel.send(embed=embed)
        print(f"Sent notification for commit: {commit_hash_short}")

    # Update last processed commit hash
    latest_commit_hash = commits[0]["sha"]
    if latest_commit_hash != last_commit_hash:
        save_last_commit_hash(latest_commit_hash)

@bot.event
async def on_ready():
    """Triggered when bot is successfully connected"""
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"Monitoring GitHub repository: {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
    print(f"Target Discord channel ID: {DISCORD_CHANNEL_ID}")
    
    # Start commit monitoring task
    monitor_commits.start()

@bot.event
async def on_disconnect():
    """Triggered when bot disconnects"""
    print("Bot disconnected from Discord")

if __name__ == "__main__":
    # Run the bot
    bot.run(DISCORD_BOT_TOKEN)