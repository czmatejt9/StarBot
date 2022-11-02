import discord
from discord import app_commands
from discord.ext import commands
from bot import StarCityBot, MY_GUILD_ID
FEEDBACK_CHANNEL_ID = 1037423626179313744


class FeedbackModal(discord.ui.Modal, title="Feedback"):
    def __init__(self, bot: StarCityBot, user: discord.User):
        super().__init__()
        self.bot = bot
        self.user = user

    type = discord.ui.TextInput(label="Type of feedback", placeholder="Bug report, suggestion, etc.")
    feedback = discord.ui.TextInput(placeholder="Your feedback goes here", style=discord.TextStyle.paragraph, label="Feedback")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Thanks for your feedback!", ephemeral=True)
        guild: discord.Guild = self.bot.get_guild(MY_GUILD_ID)
        channel: discord.TextChannel = await guild.fetch_channel(FEEDBACK_CHANNEL_ID)
        embed = discord.Embed(title=self.type.value, description=self.feedback.value, color=discord.Color.blurple(),
                              timestamp=discord.utils.utcnow())
        embed.set_author(name=self.user, icon_url=self.user.display_avatar)
        await channel.send(embed=embed)


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

    @commands.cooldown(1, 3600, commands.BucketType.user)
    @app_commands.command(name="feedback")  # Note this is only slash command not a hybrid command like the others
    async def feedback(self, ctx: commands.Context):
        """Invokes a discord modal to send feedback to the bot owner"""
        await ctx.interaction.response.send_modal(FeedbackModal(self.bot, ctx.author))


async def setup(bot: StarCityBot):
    await bot.add_cog(Meta(bot))
