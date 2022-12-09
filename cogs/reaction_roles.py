import aiosqlite
import discord
from discord.ext import commands
from bot import StarCityBot, MY_GUILD_ID

class ReactionRoles(commands.Cog):
    """Some commands for reaction roles"""
    def __init__(self, bot):
        self.bot: StarCityBot = bot

    def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.guild_permissions.administrator

    @commands.hybrid_command(name="reactionrole", aliases=["rr"])
    async def reaction_roles(self, ctx: commands.Context, message_id: int, emoji: str, role: discord.Role):
        """Adds a reaction role to a message. Must have admin permissions."""
        guild: discord.Guild = self.bot.get_guild(MY_GUILD_ID)
        channel: discord.TextChannel = await guild.fetch_channel(1029452188621222008)
        message: discord.Message = await channel.fetch_message(message_id)
        if message is None:
            channel: discord.TextChannel = await guild.fetch_channel(
                1050721692068102174)
            message: discord.Message = await channel.fetch_message(message_id)

        await message.add_reaction(emoji)
        async with self.bot.db.cursor() as cursor:
          cursor: aiosqlite.Cursor
          await cursor.execute("INSERT INTO reaction_roles (message_id, emoji, role_id) VALUES (?, ?, ?)", (message_id, emoji, role.id))
          await self.bot.db.commit()
        await ctx.send("Successfully added reaction role for this server")
  
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?", (payload.message_id, payload.emoji.name))
            result = await cursor.fetchone()
        if result is not None:
            guild: discord.Guild = self.bot.get_guild(payload.guild_id)
            role: discord.Role = guild.get_role(result[0])
            await payload.member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?", (payload.message_id, payload.emoji.name))
            result = await cursor.fetchone()

        if result is not None:
            guild: discord.Guild = self.bot.get_guild(payload.guild_id)
            role: discord.Role = guild.get_role(result[0])
            member: discord.Member = guild.get_member(payload.user_id)
            await member.remove_roles(role)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))
