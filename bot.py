import os
import logging
import logging.handlers
import time
import aiosqlite
import discord
from discord.ext import commands
import config


TOKEN = config.DISCORD_TOKEN
MY_GUILD_ID = config.MY_GUILD_ID
LOG_CHANNEL_ID = config.LOG_CHANNEL_ID
DEFAULT_PREFIX = "s!"
HOME_PATH = "/home/vronvron/StarBot"
DB_NAME = "bot.db"
EXTENSIONS = (
    "cogs.general",
    "cogs.minigames",
    "cogs.mods",
    "cogs.meta"
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename='StarBot.log',
    encoding='utf-8',
    maxBytes=8 * 1024 * 1024,  # 8 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)


class StarCityBot(commands.Bot):
    def __init__(self):
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

    async def setup_db(self):
        # connecting to sqlite database and creating tables if they don't exist
        self.db = await aiosqlite.connect(DB_NAME)
        async with self.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("CREATE TABLE IF NOT EXISTS guilds (guild_id INTEGER NOT NULL, prefix TEXT NOT NULL,"
                                 "system_channel_id TEXT ,PRIMARY KEY (guild_id))")
            await cursor.execute("CREATE TABLE IF NOT EXISTS sessions (pid INT)")
            await cursor.execute("SELECT pid from sessions")
            pid = await cursor.fetchone()
            if pid is not None:
                pid = pid[0]
                os.system(f"kill -9 {pid}")
            else:
                await cursor.execute("INSERT INTO sessions values (?)", (0, ))
            await cursor.execute("UPDATE sessions SET pid = ?", (os.getpid(), ))
        await self.db.commit()  # TODO CREATE TABLE FOR USERS

    async def setup_hook(self) -> None:
        # loading extensions
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception as e:
                logger.exception(f'Failed to load extension {extension}')
                await self.log_to_channel(f'Failed to load extension {extension}')

        # syncs slash commands
        if not self.synced:
            await self.tree.sync(guild=discord.Object(id=MY_GUILD_ID))
            print(f"synced slash commands for {self.user}")
            self.synced = True

        await self.setup_db()

    async def on_ready(self):
        print("running...")
        channel = self.get_guild(MY_GUILD_ID).get_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(description="Started running...", timestamp=discord.utils.utcnow())
        await channel.send(embed=embed)

    async def get_prefix(self, message: discord.Message):
        if message.guild is None:
            return DEFAULT_PREFIX

        async with self.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT prefix FROM guilds WHERE guild_id = ?", (message.guild.id, ))
            prefix = await cursor.fetchone()
            if prefix is None:  # we assign the default prefix and upload it to db
                prefix = DEFAULT_PREFIX
                await cursor.execute("INSERT INTO guilds VALUES (?, ?, ?)", (message.guild.id, prefix, None))
                await self.db.commit()
            else:
                prefix = prefix[0]

        return prefix

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, (commands.ArgumentParsingError, commands.MissingRequiredArgument)):
            await ctx.send(str(error))
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send('You do not have permissions for this command')
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send(f"{str(error)}. Try using the help command")
        else:
            logger.exception(str(error))
            await self.log_to_channel(str(error))

    async def log_to_channel(self, msg: str):
        channel = self.get_guild(MY_GUILD_ID).get_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(description=msg, timestamp=discord.utils.utcnow())
        await channel.send(embed=embed)


mybot = StarCityBot()
if __name__ == "__main__":
    time.sleep(10)
    mybot.run(TOKEN, log_handler=None)
