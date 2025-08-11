import asyncio

from discord.ext import commands, tasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.db_actions import (
    collect_diary_updates,
    update_all_user_films,
)

WAIT_UNTIL_READY_TIMEOUT = 900.0  # 15 minutes


async def wait_until_ready(bot) -> None:
    while True:
        try:
            if bot.is_ready():
                print("wait_until_ready: already ready")
                break

            ready_task = asyncio.create_task(
                bot.wait_for("ready", timeout=WAIT_UNTIL_READY_TIMEOUT)
            )
            resumed_task = asyncio.create_task(
                bot.wait_for("resumed", timeout=WAIT_UNTIL_READY_TIMEOUT)
            )

            done, unfinished = await asyncio.wait(
                {ready_task, resumed_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in unfinished:
                task.cancel()

            print("wait_until_ready: ready or resumed")
            break
        except TimeoutError:
            print("wait_until_ready: timeout waiting for ready or resumed")
            break
        except BaseException as e:  # Catch EVERYTHING so tasks don't die
            print("error: exception in task before loop: %s", e)


class TasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_new_films.start()
        self.update_all_movie_watches.start()

    def cog_unload(self):
        self.check_new_films.cancel()
        self.update_all_movie_watches.cancel()

    async def on_ready(self) -> None:
        print("client ready")

    async def on_shard_ready(self, shard_id: int) -> None:
        print(f"shard {shard_id} ready")

    @tasks.loop(minutes=15)
    async def check_new_films(self):
        try:
            print("Running scheduled check for new diary entries...")

            db: Session = next(get_db())
            updates = await asyncio.to_thread(collect_diary_updates, db, self.bot)

            for update in updates:
                try:
                    await update.channel.send(embed=update.embed)
                except Exception as e:
                    print(f"Failed to send message: {e}")

            print("Finished checking diaries")
        except BaseException as e:  # Catch EVERYTHING so tasks don't die
            print("error: exception in task cog: %s", e)

    @tasks.loop(hours=6)
    async def update_all_movie_watches(self):  # todo: how to run this in bg? it blocks
        try:
            print("Running scheduled update for all movie watches...")

            db: Session = next(get_db())
            await asyncio.to_thread(update_all_user_films, db)

            print("Finished updating all movie watches")
        except BaseException as e:  # Catch EVERYTHING so tasks don't die
            print("error: exception in task cog: %s", e)

    @check_new_films.before_loop
    @update_all_movie_watches.before_loop
    async def before_check(self):
        await wait_until_ready(self.bot)


async def setup(bot):
    await bot.add_cog(TasksCog(bot))
