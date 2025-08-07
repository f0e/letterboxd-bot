import discord
from discord import app_commands
from discord.ext import commands
from letterboxdpy import movie as lb_movie  # type: ignore
from letterboxdpy import search as lb_search  # type: ignore
from letterboxdpy import user as lb_user  # type: ignore
from sqlalchemy.orm import Session

from ..database import FollowedUser, MovieWatch, get_db
from ..utils.embeds import create_watchers_embed


class LetterboxdCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="follow",
        description="Follow a Letterboxd user to get updates.",
    )
    async def follow(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer()

        if not interaction.guild or not interaction.channel:
            # todo: when does this happen? in dms?
            await interaction.followup.send(
                "Failed to fetch channel.",
                ephemeral=True,
            )
            return

        try:
            if not lb_user.User(username).username:
                await interaction.followup.send(
                    f"Could not find a Letterboxd user with the username `{username}`.",
                    ephemeral=True,
                )
                return
        except Exception:
            await interaction.followup.send(
                f"Could not find a Letterboxd user with the username `{username}`.",
                ephemeral=True,
            )
            return

        db: Session = next(get_db())
        existing_follow = (
            db.query(FollowedUser)
            .filter_by(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                letterboxd_username=username,
            )
            .first()
        )

        if existing_follow:
            await interaction.followup.send(
                f"You are already following `{username}` on this server.",
                ephemeral=True,
            )
            db.close()
            return

        new_follow = FollowedUser(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            letterboxd_username=username,
        )
        db.add(new_follow)
        db.commit()

        # todo: would be nice to show profile on follow - in case you followed the wrong person

        await interaction.followup.send(
            f"✅ Successfully started following `{username}`!"
        )
        db.close()

    @app_commands.command(
        name="unfollow",
        description="Unfollow a Letterboxd user.",
    )
    async def unfollow(self, interaction: discord.Interaction, username: str):
        await interaction.response.defer()

        if not interaction.guild or not interaction.channel:
            # todo: when does this happen? in dms?
            await interaction.followup.send(
                "Failed to fetch channel.",
                ephemeral=True,
            )
            return

        db: Session = next(get_db())
        follow_to_delete = (
            db.query(FollowedUser)
            .filter_by(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
                letterboxd_username=username,
            )
            .first()
        )

        if not follow_to_delete:
            await interaction.followup.send(
                f"You are not currently following `{username}` on this server.",
                ephemeral=True,
            )
            db.close()
            return

        db.delete(follow_to_delete)
        db.commit()
        await interaction.followup.send(f"🗑️ Successfully unfollowed `{username}`.")
        db.close()

    @app_commands.command(
        name="following",
        description="List all Letterboxd users being followed.",
    )
    async def following(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not interaction.guild or not interaction.channel:
            # todo: when does this happen? in dms?
            await interaction.followup.send(
                "Failed to fetch channel.",
                ephemeral=True,
            )
            return

        db: Session = next(get_db())

        followed_list = (
            db.query(FollowedUser)
            .filter_by(
                guild_id=interaction.guild.id,
                channel_id=interaction.channel.id,
            )
            .all()
        )
        db.close()

        if not followed_list:
            await interaction.followup.send(
                "This server isn't following any Letterboxd users yet. Use `/follow` to add one!",
                ephemeral=True,
            )
            return

        description = "\n".join(
            [f"• {user.letterboxd_username}" for user in followed_list]
        )
        embed = discord.Embed(
            title=f"Following {len(followed_list)} Letterboxd Users",
            description=description,
            color=discord.Color.blue(),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="whowatched",
        description="See who has watched a specific movie.",
    )
    async def whowatched(self, interaction: discord.Interaction, movie_title: str):
        await interaction.response.defer()

        if not interaction.guild or not interaction.channel:
            # todo: when does this happen? in dms?
            await interaction.followup.send(
                "Failed to fetch channel.",
                ephemeral=True,
            )
            return

        query = lb_search.Search(movie_title, "films")
        search_results = query.get_results(max=1)["results"]

        db: Session = next(get_db())

        try:
            followed_usernames = set(
                r.letterboxd_username
                for r in db.query(FollowedUser)
                .filter_by(
                    guild_id=interaction.guild.id,
                    channel_id=interaction.channel.id,
                )
                .all()
            )

            if not followed_usernames:
                await interaction.followup.send(
                    "This server isn't following anyone yet! Use `/follow`.",
                    ephemeral=True,
                )
                return

            query = lb_search.Search(movie_title, "films")
            search_results = query.get_results(max=1)["results"]

            if not search_results:
                await interaction.followup.send(
                    f"Could not find a movie matching '{movie_title}'. Please try a different title or be more specific.",
                    ephemeral=True,
                )
                return

            film_slug = search_results[0]["slug"]

            movie = lb_movie.Movie(film_slug)

            watchers = (
                db.query(MovieWatch)
                .filter(
                    MovieWatch.movie_id == movie.letterboxd_id,
                    MovieWatch.letterboxd_username.in_(followed_usernames),
                )
                .all()
            )

            if not watchers:
                await interaction.followup.send(
                    f"Nobody's seen [**{movie.title} ({movie.year})**]({movie.url}).",
                    ephemeral=True,
                )
                return

            # sort by rating descending
            watchers.sort(
                key=lambda watcher: (watcher.rating is None, -(watcher.rating or 0))
            )

            embed = create_watchers_embed(movie, watchers)

            await interaction.followup.send(embed=embed)
        finally:
            db.close()


async def setup(bot: commands.Bot, TEST_GUILD_ID=None):
    cog = LetterboxdCog(bot)
    await bot.add_cog(cog)

    if TEST_GUILD_ID:
        guild = discord.Object(id=TEST_GUILD_ID)
        bot.tree.add_command(cog.follow, guild=guild)
        bot.tree.add_command(cog.unfollow, guild=guild)
        bot.tree.add_command(cog.following, guild=guild)
        bot.tree.add_command(cog.whowatched, guild=guild)
        await bot.tree.sync(guild=guild)
