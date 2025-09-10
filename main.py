# import os
# import logging
# import asyncio
# from dotenv import load_dotenv
# import discord
# from discord.ext import commands

# load_dotenv()
# DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
# if not DISCORD_TOKEN:
#     raise RuntimeError("DISCORD_TOKEN belum diset di environment.")

# handler = logging.FileHandler(filename='logs/discord.log', encoding='utf-8', mode='w')
# logging.basicConfig(level=logging.INFO, handlers=[handler])
# logger = logging.getLogger(__name__)

# intents = discord.Intents.default()
# intents.message_content = True
# bot = commands.Bot(command_prefix='!', intents=intents)

# @bot.event
# async def on_ready():
#     logger.info("Bot ready: %s", bot.user)
#     print(f"Bot ready: {bot.user}")

# async def load_cogs():
#     """Load all python files in cogs/ as extensions."""
#     import os
#     for filename in os.listdir("cogs"):
#         if filename.endswith(".py") and not filename.startswith("__"):
#             ext = f"cogs.{filename[:-3]}"
#             try:
#                 await bot.load_extension(ext)
#                 logger.info("Loaded cog: %s", ext)
#             except Exception as e:
#                 logger.exception("Failed to load extension %s: %s", ext, e)

# async def main():
#     await load_cogs()
#     await bot.start(DISCORD_TOKEN)

# if __name__ == "__main__":
#     asyncio.run(main())
import os
import logging
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Load token
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing in .env")

# Logging
os.makedirs("logs", exist_ok=True)
handler = logging.FileHandler(filename="logs/discord.log", encoding="utf-8", mode="w")
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info("🤖 Bot ready: %s", bot.user)
    print(f"🤖 Bot ready: {bot.user}")
    
@bot.event
async def on_command_error(ctx, error):
    # Ignore "CommandNotFound" errors (so bot acts like chatbot)
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

async def load_cogs():
    """Load semua file di folder cogs/"""
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            ext = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(ext)
                logger.info("✅ Loaded cog: %s", ext)
            except Exception as e:
                logger.exception("❌ Failed to load extension %s: %s", ext, e)

async def main():
    await load_cogs()
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

