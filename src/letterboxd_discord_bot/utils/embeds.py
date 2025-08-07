import datetime

import discord
from letterboxdpy import movie as lb_movie  # type: ignore
from letterboxdpy import user as lb_user  # type: ignore
from letterboxdpy.core.scraper import parse_url

from letterboxd_discord_bot.database import MovieWatch  # type: ignore


def create_watchers_embed(
    movie: lb_movie.Movie, watchers: list[MovieWatch]
) -> discord.Embed:
    embed = discord.Embed(
        title=movie.title,
        url=movie.url,
        color=discord.Color.green() if watchers else discord.Color.red(),
    )

    if hasattr(movie, "genres"):
        genres = ", ".join(
            genre["name"] for genre in movie.genres if genre.get("type") == "genre"
        )
        embed.set_footer(text=f"{movie.year} - {genres}")

    if movie.poster:
        embed.set_thumbnail(url=movie.poster)

    if watchers:
        lines = []

        for watcher in watchers:
            if watcher.rating is not None:
                rating_val = watcher.rating / 2  # consistency

                rating_str = (
                    f"{int(rating_val)}" if rating_val % 1 == 0 else f"{rating_val}"
                )
                rating_part = f" - ⭐ **{rating_str}**"
            else:
                rating_part = " - (no rating)"

            liked_part = " ❤️" if watcher.liked else ""

            if watcher.watch_date:
                dt = datetime.datetime.strptime(watcher.watch_date, "%d %b %Y")
                timestamp = int(dt.timestamp())
                date_part = f" <t:{timestamp}:R>"
            else:
                date_part = ""

            line = f"• [{watcher.letterboxd_username}](https://letterboxd.com/{watcher.letterboxd_username}/){rating_part}{liked_part}{date_part}"
            lines.append(line)

        embed.description = "\n".join(lines)

    else:
        embed.description = (
            f"None of the users you follow have watched '{movie.title}'."
        )

    return embed


def create_diary_embed(
    user: lb_user.User, movie: lb_movie.Movie, diary_entry: dict
) -> discord.Embed:
    actions = diary_entry.get("actions", {})

    url = actions.get("review_link")
    if url:
        url = "https://letterboxd.com" + url
    else:
        url = movie.url

    rating_val = actions.get("rating")
    if rating_val:
        rating_val /= 2  # consistency

    liked = diary_entry.get("liked", False)
    date = diary_entry.get("date")
    review_text = None

    if url:
        # fetch review text
        review_dom = parse_url(url)
        review_text = review_dom.find("div", class_="js-review-body").text.strip()

    repeat_emoji = " 🔁" if actions.get("rewatched") else ""

    if rating_val is not None:
        rating_str = (
            f"{int(rating_val)}"
            if isinstance(rating_val, (int, float)) and rating_val % 1 == 0
            else f"{rating_val}"
        )
        rating_part = f"⭐ **{rating_str}**"
    else:
        rating_part = "Not rated"

    liked_part = " ❤️" if liked else ""

    if date:
        dt = datetime.datetime.combine(date, datetime.time())
        ts = int(dt.timestamp())
        date_part = f" <t:{ts}:R>"
    else:
        date_part = ""

    description = f"**Rating:** {rating_part}{liked_part}{repeat_emoji}{date_part}"

    if review_text:
        description += f"\n{'―' * 15}\n{review_text}"

    embed = discord.Embed(
        title=diary_entry["name"],
        description=description,
        color=discord.Color.green(),
        url=url,
    )

    poster = diary_entry.get("poster") or getattr(movie, "poster", None)
    if poster:
        embed.set_thumbnail(url=poster)

    avatar_url = user.avatar.get("url")
    embed.set_author(name=f"{user.display_name} watched", icon_url=avatar_url)

    if hasattr(movie, "genres"):
        genres = ", ".join(
            genre["name"] for genre in movie.genres if genre.get("type") == "genre"
        )
        if genres:
            embed.set_footer(text=f"{movie.year} - {genres}")

    return embed
