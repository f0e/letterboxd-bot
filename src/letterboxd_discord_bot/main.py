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
# intents.members = True
# intents.message_content = True

allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)


class LetterboxdBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="%",
            description=description,
            intents=intents,
            allowed_mentions=allowed_mentions,
        )

    async def setup_hook(self):
        await tasks_cog.setup(self)
        await letterboxd_cog.setup(self, config.TEST_GUILD_ID)

        print("Cogs initialised")

    async def close(self):
        await super().close()

    async def on_ready(self):
        print(f"Logged in as {self.user}")


print("Initializing database...")
create_tables()
print("Database tables verified.")

bot = LetterboxdBot()
bot.run(config.DISCORD_TOKEN)
