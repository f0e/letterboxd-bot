import datetime

import discord
from bs4 import Tag
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
            line = f"• [{discord.utils.escape_markdown(discord.utils.escape_mentions(watcher.letterboxd_username))}](https://letterboxd.com/{watcher.letterboxd_username}/){watch_info}"
            lines.append(line)

        embed.description = "\n".join(lines)
    else:
        embed.description = f"Nobody's watched '{discord.utils.escape_markdown(discord.utils.escape_mentions(movie.title or ''))}'."

    return embed


def create_diary_embed(
    user: lb_user.User, movie: lb_movie.Movie, diary_entry: dict
) -> discord.Embed:
    actions = diary_entry.get("actions", {})

    reviewed = actions.get("reviewed", {})
    url = actions.get("entry_link")
    review_text = None

    if reviewed and url:
        url = "https://letterboxd.com" + url

        review_dom = parse_url(url)
        review_text_elem = review_dom.find("div", class_="js-review-body")

        if isinstance(review_text_elem, Tag):
            # replace <br> with newline characters
            for br in review_text_elem.find_all("br"):
                br.replace_with("\n")

            paragraphs = review_text_elem.find_all("p")
            review_text = "\n\n".join(p.get_text().strip() for p in paragraphs).strip()
    else:
        url = movie.url

    description_parts = []

    rating = actions.get("rating")
    if rating is not None:
        description_parts.append(f"**Rating:** {get_stars(rating)}")

    if actions.get("liked"):
        description_parts.append("❤️")

    if actions.get("rewatched"):
        description_parts.append("🔁")

    description = " ".join(description_parts)

    embed = discord.Embed(
        title=diary_entry["name"],
        description=description,
        color=discord.Color.green(),
        url=url,
    )

    if review_text:
        embed.add_field(
            name="Review",
            value=discord.utils.escape_markdown(
                discord.utils.escape_mentions(review_text)
            ),
            inline=False,
        )

    date = diary_entry.get("date")
    if date:
        # TODO: bring back relative date when i can get precise datetime of watch. its available on https://letterboxd.com/[user]/film/[slug]/activity/ but not sure where else
        # dt = datetime.datetime.combine(date, datetime.time())
        # ts = int(dt.timestamp())
        # embed.add_field(name="", value=f"-# <t:{ts}:R>")
        formatted_date = date.strftime("%B %-d")
        embed.add_field(name="", value=f"-# {formatted_date}")

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
