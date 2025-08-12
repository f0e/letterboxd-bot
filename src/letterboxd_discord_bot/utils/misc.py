import discord


def escape(text: str):
    return discord.utils.escape_markdown(discord.utils.escape_mentions(text))
