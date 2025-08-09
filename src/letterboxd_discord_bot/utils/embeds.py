import datetime

import discord
from letterboxdpy import movie as lb_movie  # type: ignore
from letterboxdpy import user as lb_user  # type: ignore
from letterboxdpy.core.scraper import parse_url  # type: ignore

from letterboxd_discord_bot.database import MovieWatch  # type: ignore

EMOJI_STAR = "<:lb_star:1403009346492698764>"
EMOJI_STAR_HALF = "<:lb_halfstar:1403009343867191386>"


def get_stars(rating_out_of_10: int):
    rating = rating_out_of_10 / 2

    full_stars = int(rating)
    half_star = 1 if (rating - full_stars) >= 0.5 else 0

    return EMOJI_STAR * full_stars + EMOJI_STAR_HALF * half_star


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
            parts = []

            if watcher.rating is not None:
                parts.append(get_stars(watcher.rating))

            if watcher.liked:
                parts.append("❤️")

            if watcher.watch_date:
                dt = datetime.datetime.strptime(watcher.watch_date, "%d %b %Y")
                timestamp = int(dt.timestamp())
                parts.append(f"<t:{timestamp}:R>")

            watch_info = (" - " + " ".join(parts)) if parts else ""
            line = f"• [{discord.utils.escape_markdown(watcher.letterboxd_username)}](https://letterboxd.com/{watcher.letterboxd_username}/){watch_info}"
            lines.append(line)

        embed.description = "\n".join(lines)
    else:
        embed.description = (
            f"Nobody's watched '{discord.utils.escape_markdown(movie.title or '')}'."
        )

    return embed


def create_diary_embed(
    user: lb_user.User, movie: lb_movie.Movie, diary_entry: dict
) -> discord.Embed:
    actions = diary_entry.get("actions", {})

    url = actions.get("review_link")
    review_text = None

    if url:
        url = "https://letterboxd.com" + url

        # fetch review text
        review_dom = parse_url(url)
        if review_text_elem := review_dom.find("div", class_="js-review-body"):
            review_text = review_text_elem.text.strip()
    else:
        url = movie.url

    rating = actions.get("rating")
    liked = diary_entry.get("liked", False)
    date = diary_entry.get("date")

    repeat_emoji = " 🔁" if actions.get("rewatched") else ""

    if rating is not None:
        rating_part = f"{get_stars(rating)}"
    else:
        rating_part = "Not rated"

    liked_part = " ❤️" if liked else ""

    if date:
        dt = datetime.datetime.combine(date, datetime.time())
        ts = int(dt.timestamp())
        date_part = f" <t:{ts}:R>"
    else:
        date_part = ""

    description = f"""**Rating:** {rating_part}{liked_part}{repeat_emoji}"""

    embed = discord.Embed(
        title=diary_entry["name"],
        description=description,
        color=discord.Color.green(),
        url=url,
    )

    if review_text:
        embed.add_field(
            name="Review",
            value=discord.utils.escape_markdown(review_text),
            inline=False,
        )

    embed.add_field(name="", value=f"-# {date_part}")

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
