import os
import logging

import aiosqlite
import discord
from discord.ext import commands
import config
# from dotenv import load_dotenv
# load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "variables.env"))

TOKEN = config.DISCORD_TOKEN
MY_GUILD_ID = config.MY_GUILD_ID
DEFAULT_PREFIX = "s!"
DB_NAME = "bot.db"
EXTENSIONS = (
    "cogs.general",
    "cogs.minigames",
    "cogs.mods",
    "cogs.meta"
)
log = logging.getLogger(__name__)  # TODO logging


class StarCityBot(commands.Bot):
    def __init__(self, command_prefix):
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            voice_states=True,
            messages=True,
            reactions=True,
            message_content=True,
        )
        super().__init__(command_prefix=self.get_prefix, self_bot=False, intents=intents)
        self.synced = False
        self.db: aiosqlite.Connection = None
        # TODO your initialization

    async def setup_hook(self) -> None:
        # loading extensions
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception as e:
                log.exception(f'Failed to load extension {extension}')

        # syncs slash commands
        if not self.synced:
            await self.tree.sync(guild=discord.Object(id=MY_GUILD_ID))
            print(f"synced slash commands for {self.user}")
            self.synced = True

        # connecting to sqlite database and creating tables if they don't exist
        self.db = await aiosqlite.connect(DB_NAME)
        async with self.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("CREATE TABLE IF NOT EXISTS guilds (guild_id INTEGER NOT NULL, prefix TEXT NOT NULL,"
                                 "PRIMARY KEY (guild_id))")
        await self.db.commit()  # TODO CREATE TABLE FOR USERS

    async def on_ready(self):
        print("Running...")
        # TODO

    async def get_prefix(self, message: discord.Message):
        if message.guild is None:
            return DEFAULT_PREFIX

        async with self.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT prefix FROM guilds WHERE guild_id = ?", (message.guild.id, ))
            prefix = await cursor.fetchone()
            if prefix is None:  # we assign the default prefix and upload it to db
                prefix = DEFAULT_PREFIX
                await cursor.execute("INSERT INTO guilds VALUES (?, ?)", (message.guild.id, prefix))
                await self.db.commit()
            else:
                prefix = prefix[0]

        return prefix

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                log.exception('In %s:', ctx.command.qualified_name, exc_info=original)
        elif isinstance(error, (commands.ArgumentParsingError, commands.MissingRequiredArgument)):
            print(error)
            await ctx.send(str(error))


mybot = StarCityBot(DEFAULT_PREFIX)
if __name__ == "__main__":
    mybot.run(TOKEN)
