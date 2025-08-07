import datetime

from discord.ext import commands, tasks
from letterboxdpy import movie as lb_movie  # type: ignore
from letterboxdpy import user as lb_user  # type: ignore
from sqlalchemy.orm import Session

from letterboxd_discord_bot.utils.db_actions import update_user_films

from ..database import FollowedUser, get_db
from ..utils.embeds import create_diary_embed


def get_diary(user: lb_user.User, last_diary_entry: datetime.date | None = None):
    lb_diary_to_process: list[dict] = []

    page = 1
    while True:
        lb_page_diary_entries: dict[str, dict] = user.get_diary(page=page)["entries"]
        if not lb_page_diary_entries:
            # reached the end.
            return lb_diary_to_process

        for entry_key, entry in lb_page_diary_entries.items():
            # convert date dict to date object
            entry["date"] = datetime.date(
                entry["date"]["year"],
                entry["date"]["month"],
                entry["date"]["day"],
            )

            if last_diary_entry:
                if entry["date"] <= last_diary_entry:
                    # reached stuff we've already processed
                    return lb_diary_to_process

            lb_diary_to_process.append(entry)

            if not last_diary_entry:
                # just getting the newest :)
                return lb_diary_to_process

        page += 1


class TasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.check_new_films.start()
        self.update_all_movie_watches.start()

    def cog_unload(self):
        self.check_new_films.cancel()
        self.update_all_movie_watches.cancel()

    @tasks.loop(minutes=15)
    async def check_new_films(self):
        print("Running scheduled check for new films...")
        db: Session = next(get_db())

        channels = db.query(FollowedUser).all()

        for channel in channels:
            guild = self.bot.get_guild(channel.guild_id)
            if not guild:
                print(f"Guild ID {channel.guild_id} not found.")
                continue

            ch = guild.get_channel(channel.channel_id)
            if not ch:
                print(
                    f"Channel ID {channel.channel_id} not found in guild {channel.guild_id}"
                )
                continue

            user = lb_user.User(username=channel.letterboxd_username)

            last_diary_entry: datetime.datetime | None = channel.last_diary_entry

            new_diary_entries = get_diary(
                user,
                last_diary_entry.date() if last_diary_entry else None,
            )

            new_diary_entries.reverse()  # reverse so newest = last

            if not new_diary_entries:
                continue

            films = [lb_movie.Movie(entry["slug"]) for entry in new_diary_entries]

            for diary_entry, film in zip(new_diary_entries, films):
                embed = create_diary_embed(user, film, diary_entry)
                await ch.send(embed=embed)

            channel.last_diary_entry = new_diary_entries[-1][
                "date"
            ]  # store newest diary entry date
            db.commit()

        db.close()
        print("Finished checking diaries")

    @tasks.loop(hours=6)
    async def update_all_movie_watches(self):  # todo: how to run this in bg? it blocks
        print("Running scheduled update for all movie watches...")
        db: Session = next(get_db())

        try:
            # Get all unique followed users
            followed_users = db.query(FollowedUser.letterboxd_username).distinct().all()

            for (username,) in followed_users:
                print(f"Updating watches for user: {username}")

                update_user_films(db, username)

                db.commit()
        finally:
            db.close()
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
