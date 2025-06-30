import discord
from discord.ext import commands
from dotenv import load_dotenv
from rich import print

from . import config
from .cogs import letterboxd_cog, tasks_cog
from .database import create_tables

description = """Hello bro"""

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="%", description=description, intents=intents)


@bot.event
async def on_ready():
    """Event that fires when the bot is logged in and ready."""
    print(f"Logged in as {bot.user}")

    await tasks_cog.setup(bot)
    await letterboxd_cog.setup(bot, config.TEST_GUILD_ID)

    print("Cogs initialised")
    print("-------------------")


print("Initializing database...")
create_tables()
print("Database tables verified.")

bot.run(config.DISCORD_TOKEN)
