from discord.ext import commands
from bot import StarCityBot, MY_GUILD_ID


class Meta(commands.Cog):
    def __init__(self, bot: StarCityBot):
        self.bot = bot


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
