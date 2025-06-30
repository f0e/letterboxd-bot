from concurrent.futures import ThreadPoolExecutor, as_completed

import discord
from discord import app_commands
from discord.ext import commands
from letterboxdpy import movie as lb_movie  # type: ignore
from letterboxdpy import search as lb_search  # type: ignore
from letterboxdpy import user as lb_user  # type: ignore
from sqlalchemy.orm import Session

from ..database import FollowedUser, get_db
from ..utils.embeds import create_watchers_embed


class LetterboxdCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="follow",
        description="Follow a Letterboxd user to get updates.",
    )
    async def follow(self, interaction: discord.Interaction, username: str):
        """Adds a Letterboxd user to the server's follow list."""
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

        await interaction.followup.send(
            f"✅ Successfully started following `{username}`!"
        )
        db.close()

    @app_commands.command(
        name="unfollow",
        description="Unfollow a Letterboxd user.",
    )
    async def unfollow(self, interaction: discord.Interaction, username: str):
        """Removes a Letterboxd user from the server's follow list."""
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
        """Lists all Letterboxd users this server is following."""
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
        """Checks which followed users have seen a specific movie."""
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

        watchers = []

        def check_user_watch(followed):
            try:
                user_obj = lb_user.User(followed.letterboxd_username)
                user_film = user_obj.get_film(
                    film_slug
                )  # todo: this is already a custom function ive made, but it only works atm if they logged it to diary. need to fix!

                print(followed.letterboxd_username, user_film)

                if user_film:
                    return {
                        "username": followed.letterboxd_username,
                        "rating": user_film.get("rating"),
                        "liked": user_film.get("liked"),
                        "date": user_film.get("view_date"),
                    }
            except Exception as e:
                print(f"Error checking watches for {followed.letterboxd_username}: {e}")
            return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(check_user_watch, followed)
                for followed in followed_list
            ]

            for future in as_completed(futures):
                result = future.result()
                if result:
                    watchers.append(result)

        # Sort by rating descending
        watchers.sort(key=lambda w: (w["rating"] is None, -(w["rating"] or 0)))

        embed = create_watchers_embed(movie, watchers)

        await interaction.followup.send(embed=embed)


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
