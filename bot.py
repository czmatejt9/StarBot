import os
import logging
import discord
from discord.ext import commands
from replit import db
# import config
# from dotenv import load_dotenv
# load_dotenv()

DEFAULT_PREFIX = "sc "
TOKEN = os.getenv("DISCORD_TOKEN")
MY_GUILD_ID = os.getenv("MY_GUILD_ID")
EXTENSIONS = (
    "cogs.general",
    "cogs.minigames",
    "cogs.mod"
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
        super().__init__(command_prefix=command_prefix, self_bot=False, intents=intents)
        self.synced = False
        self.db = db
        # TODO your initialization

    async def setup_hook(self) -> None:
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

    async def on_ready(self):
        print("Running...")
        # TODO

    async def get_prefix(self, message: discord.Message):
        if message.guild.id in self.db.keys():
            prefix = self.db[str(message.guild.id)]
        else:
            prefix = DEFAULT_PREFIX
            self.db[str(message.guild.id)] = prefix
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
