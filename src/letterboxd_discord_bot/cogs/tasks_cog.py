import asyncio

from discord.ext import commands, tasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.db_actions import (
    update_all_user_diaries,
    update_all_user_films,
)


class TasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_new_films.start()
        self.update_all_movie_watches.start()

    def cog_unload(self):
        self.check_new_films.cancel()
        self.update_all_movie_watches.cancel()

    @tasks.loop(minutes=15)
    async def check_new_films(self):
        print("Running scheduled check for new films...")

        db: Session = next(get_db())
        await asyncio.to_thread(update_all_user_diaries, db, self.bot)

        print("Finished checking diaries")

    @tasks.loop(hours=6)
    async def update_all_movie_watches(self):  # todo: how to run this in bg? it blocks
        print("Running scheduled update for all movie watches...")

        db: Session = next(get_db())
        await asyncio.to_thread(update_all_user_films, db)

        print("Finished updating all movie watches")

    @check_new_films.before_loop
    async def before_check(self):
        """Waits until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

    @update_all_movie_watches.before_loop
    async def before_update_watches(self):
        """Waits until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(TasksCog(bot))
