import logging
import logging.handlers
import random
import os
import aiosqlite
import discord
from discord.ext import commands
import config
from cogs.utils import formatters

TOKEN = config.DISCORD_TOKEN
MY_GUILD_ID = config.MY_GUILD_ID
LOG_CHANNEL_ID = config.LOG_CHANNEL_ID
GAMBLE_RANDOM = random.Random(config.GAMBLE_SEED)
ALPACA_BASE_URL = config.ALPACA_BASE_URL
ALPACA_KEY_ID = config.ALPACA_KEY_ID
ALPACA_SECRET_KEY = config.ALPACA_SECRET_KEY
DEFAULT_PREFIX = "s!"
HOME_PATH = os.path.dirname(os.path.abspath(__name__))
DB_NAME = "bot.db"
EXTENSIONS = (
    "cogs.general",
    "cogs.minigames",
    "cogs.mods",
    "cogs.meta",
    "cogs.admin",
    "cogs.currency",
    "cogs.crypto",
)
ITEMS = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger('discord.http').setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename='StarBot.log',
    encoding='utf-8',
    maxBytes=8 * 1024 * 1024,  # 8 MiB
    backupCount=10,  # Rotate through 10 files
)
dt_fmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name:<15}: {message}', dt_fmt, style='{')
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
        self.id = 0
        self.session_id = None
        self.alpaca = None
        self.failed_cogs = []

    async def setup_db(self):
        """connecting to sqlite database and creating tables if they don't exist"""
        self.db = await aiosqlite.connect(DB_NAME)
        async with self.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT max(session_id) FROM sessions")
            session_id = await cursor.fetchone()
            await cursor.execute("SELECT session_id, pid FROM sessions WHERE session_id = ?", (session_id[0], ))
            pid = await cursor.fetchone()
            _id, pid = pid
            if _id > 0 and pid is not None:
                os.system(f"kill {pid}")  # killing previous session
            await cursor.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)",
                                 (_id + 1, os.getpid(), discord.utils.utcnow(), None))
        await self.db.commit()
        self.session_id = _id + 1

    async def setup_hook(self) -> None:
        """setting up the bot"""
        # sqlite
        await self.setup_db()
        # loading extensions
        for extension in EXTENSIONS:
            try:
                await self.load_extension(extension)
            except Exception as e:
                logger.exception(f'Failed to load extension {extension}')
                self.failed_cogs.append(extension)

        # syncs slash commands
        if not self.synced:
            await self.tree.sync(guild=discord.Object(id=MY_GUILD_ID))
            logger.info(f"synced slash commands for {self.user}")
            self.synced = True

    async def on_ready(self):
        self.id = self.user.id
        logger.info(f"Started running as {self.user}")
        for each in self.failed_cogs:
            await self.log_to_channel(f"Failed to load cog {each}")
        await self.log_to_channel(f"Started running as {self.user}")

    async def get_prefix(self, message: discord.Message):
        """gets prefix for current guild from db"""
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
        """some command error handling"""
        if isinstance(error, (commands.MissingPermissions, commands.CheckFailure)):
            await ctx.send('You do not have permissions for this command')
            logger.debug(f"{ctx.author.name} used **{ctx.invoked_with}** without needed permissions")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandOnCooldown):
            time_left = formatters.format_seconds(round(error.retry_after))
            await ctx.send(f"Please wait {time_left} before using this command again")
        elif isinstance(error, (commands.ArgumentParsingError, commands.MissingRequiredArgument)):
            await ctx.send(str(error))
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send(f"{str(error)}. Try using the help command")
        else:
            logger.exception(f"**{ctx.invoked_with}** {error}")
            await self.log_to_channel(f"**{ctx.invoked_with}** {error}")

    async def log_to_channel(self, msg: str, embed: discord.Embed = None):
        """sends log info directly to discord channel"""
        channel = self.get_guild(MY_GUILD_ID).get_channel(LOG_CHANNEL_ID)
        if embed is None:
            embed = discord.Embed(description=msg, timestamp=discord.utils.utcnow())
        await channel.send(embed=embed)


mybot = StarCityBot()
if __name__ == "__main__":
    mybot.run(TOKEN, log_handler=None)
