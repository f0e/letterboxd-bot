import datetime
from dataclasses import dataclass

import discord
from discord.ext import commands
from letterboxdpy import movie as lb_movie  # type: ignore
from letterboxdpy import user as lb_user  # type: ignore
from sqlalchemy.orm import Session

from ..database import FollowedUser, MovieWatch
from ..utils.embeds import create_diary_embed
from ..utils.letterboxd_actions import get_diary


@dataclass(frozen=True)
class DiaryUpdate:
    channel: discord.guild.GuildChannel
    embed: discord.Embed
    diary_entry_date: datetime.datetime


def collect_diary_updates(db: Session, bot: commands.Bot) -> list[DiaryUpdate]:
    channels = db.query(FollowedUser).all()
    updates: list[DiaryUpdate] = []

    for channel in channels:
        guild = bot.get_guild(channel.guild_id)
        if not guild:
            continue

        ch = guild.get_channel(channel.channel_id)
        if not ch:
            continue

        user = lb_user.User(username=channel.letterboxd_username)
        last_diary_entry = channel.last_diary_entry

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
            updates.append(
                DiaryUpdate(
                    channel=ch, embed=embed, diary_entry_date=diary_entry["date"]
                )
            )

        # store newest diary entry date
        channel.last_diary_entry = new_diary_entries[-1]["date"]

    db.commit()
    return updates


def update_all_user_films(db: Session):
    # Get all unique followed users
    followed_users = db.query(FollowedUser.letterboxd_username).distinct().all()

    for (username,) in followed_users:
        print(f"Updating watches for user: {username}")

        update_user_films(db, username)

        db.commit()


def update_user_films(db: Session, username: str):
    user = lb_user.User(username=username)

    user_films = user.get_films()  # todo: modify fn to return more info - date, review url. may need to use different function?

    # todo: this can def be optimised
    for movie_slug, watch in user_films["movies"].items():
        movie_id = watch["id"]

        # Check if this watch already exists
        existing_watch = (
            db.query(MovieWatch)
            .filter_by(movie_id=movie_id, letterboxd_username=username)
            .first()
        )

        rating = watch.get("rating")
        liked = watch.get("liked")

        if existing_watch:
            if existing_watch.rating != rating:
                existing_watch.rating = rating

            if existing_watch.liked != liked:
                existing_watch.liked = liked
        else:
            new_watch = MovieWatch(
                movie_id=movie_id,
                letterboxd_username=username,
                rating=rating,
                liked=liked,
            )
            db.add(new_watch)

    db.commit()
