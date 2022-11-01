import aiosqlite
import discord
from discord.ext import commands
from bot import StarCityBot, MY_GUILD_ID

class ReactionRoles(commands.Cog):
  """Some commands for reaction roles"""
  def __init__(self, bot):
    self.bot: StarCityBot = bot

  @commands.command()
  async def reaction_roles(self, ctx: commands.Context, message_id: int, emoji: str, role: discord.Role):
    """Adds a reaction role to a message. Must have admin permissions."""
    guild: discord.Guild = self.bot.get_guild(MY_GUILD_ID)
    message: discord.Message = await guild.get_channel("1029452188621222008").fetch_message(message_id)
    await message.add_reaction(emoji)
    async with self.bot.db.cursor() as cursor:
      cursor: aiosqlite.Connection
      await cursor.execute("INSERT INTO reaction_roles (message_id, emoji, role_id) VALUES (?, ?, ?)", (message_id, emoji, role.id))
      await self.bot.db.commit()
    await ctx.send(f"Successfully added reaction role for this server")

  def cog_check(self, ctx: commands.Context) -> bool:
    return ctx.author.guild_permissions.administrator
  
  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    async with self.bot.db.cursor() as cursor:
      cursor: aiosqlite.Connection
      await cursor.execute("SELECT role_id FROM reaction_roles WHERE message_id = ? AND emoji = ?", (payload.message_id, payload.emoji.name))
      result = await cursor.fetchone()
    if result is not None:
      guild: discord.Guild = self.bot.get_guild(payload.guild_id)
      role: discord.Role = guild.get_role(result[0])
      await payload.member.add_roles(role)

async def setup(bot: commands.Bot):
  await bot.add_cog(ReactionRoles(bot))
