import discord
from discord.ext import commands
from bot import StarCityBot, MY_GUILD_ID


class Meta(commands.Cog):
    def __init__(self, bot: StarCityBot):
        self.bot = bot

    @commands.hybrid_command(name="invite")
    async def invite(self, ctx: commands.Context):
        """Sends an invitation link for the bot"""
        perms = discord.Permissions.none()
        perms.read_messages = True
        perms.external_emojis = True
        perms.send_messages = True
        perms.manage_roles = True
        perms.manage_channels = True
        perms.ban_members = True
        perms.kick_members = True
        perms.manage_messages = True
        perms.embed_links = True
        perms.read_message_history = True
        perms.attach_files = True
        perms.add_reactions = True
        await ctx.send(f'<{discord.utils.oauth_url(self.bot.user.id, permissions=perms)}>')


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
