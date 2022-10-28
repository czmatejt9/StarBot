from enum import Enum
from typing import Optional

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks
from bot import StarCityBot, MY_GUILD_ID
from alpaca_trade_api import REST
from bot import ALPACA_BASE_URL, ALPACA_KEY_ID, ALPACA_SECRET_KEY

alpaca = REST(ALPACA_KEY_ID, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
crypto_symbols = alpaca.list_assets(status='active', asset_class='crypto')
crypto_symbols = sorted([(asset.symbol.replace("/", ""), asset.name) for asset in crypto_symbols
                        if asset.tradable and "/USDT" not in asset.symbol and "/USD" in asset.symbol],
                        key=lambda x: x[0])
available_cryptos = Enum("available_cryptos", {name.split("/")[0] + "(" + symbol[:-3] + ")": i
                                               for i, (symbol, name) in enumerate(crypto_symbols)})
CRYPTO_TRADING_COMMISSION = 0.001  # 0.1% commission
CURRENCY_EMOTE = "💰"


def get_latest_bar(alpaca: REST, symbol):
    """
    Get the latest bar of stock data from Alpaca API.
    """
    bar = alpaca.get_latest_crypto_bar(symbol, "FTXU")
    return bar.t, bar.c


class Confirm(discord.ui.View):
    def __init__(self, embed: discord.Embed, crypto: str, amount: float, price: float, user_id: int, crypto_cls: "Crypto"):
        super().__init__(timeout=30.0)
        self.embed = embed
        self.crypto = crypto
        self.amount = amount
        self.price = price
        self.price_per_unit = price / amount
        self.user_id = user_id
        self.crypto_cls = crypto_cls

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed.title = "Confirmed ✅"
        self.embed.set_footer(text="Purchase confirmed")
        await interaction.response.edit_message(embed=self.embed, view=None)
        await self.crypto_cls.bot.get_cog("Currency").transfer_money(self.user_id, 1, self.price, 0,
                                                                     f"{self.crypto} purchase")
        await self.crypto_cls.give_crypto(self.user_id, self.crypto, self.amount, self.price_per_unit)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed.title = "Cancelled ❎"
        self.embed.set_footer(text="Purchase cancelled")
        await interaction.response.edit_message(embed=self.embed, view=None)
        self.stop()


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot: StarCityBot = bot
        self.crypto_symbols = crypto_symbols
        self.current_crypto_prices = {}
        self.update_crypto_prices.start()
        self.currency = self.bot.get_cog("Currency")  # to access the currency cog, use self.currency

    def cog_unload(self):
        self.update_crypto_prices.cancel()
        alpaca.close()

    def get_current_crypto_price(self, crypto):
        return self.current_crypto_prices[crypto]

    async def give_crypto(self, user_id, crypto, amount, price_per_unit):
        async with self.bot.db.cursor() as cursor:
            # check if user has crypto
            await cursor.execute("SELECT * FROM crypto_holdings WHERE user_id = ? AND coin = ?", (user_id, crypto))
            if a := await cursor.fetchone():
                # update crypto amount and avg price
                _user_id, _crypto, _amount, _avg_price = a
                new_amount = _amount + amount
                new_avg_price = (_avg_price * _amount + price_per_unit * amount) / new_amount
                await cursor.execute("UPDATE crypto_holdings SET amount = ?, avg_price = ? WHERE user_id = ? AND coin = ?",
                                     (new_amount, new_avg_price, user_id, crypto))
            else:
                # insert new crypto
                await cursor.execute("INSERT INTO crypto_holdings VALUES (?, ?, ?, ?)",
                                     (user_id, crypto, amount, price_per_unit))

    async def get_crypto_holds(self, user_id):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT coin, amount FROM crypto_holdings WHERE user_id = ?", (user_id, ))
            crypto_holds = await cursor.fetchall()
        return list(crypto_holds) if crypto_holds else None

# #######################################TASKS##############################################
    @tasks.loop(minutes=5)
    async def update_crypto_prices(self):
        for symbol, name in self.crypto_symbols:
            c_time, close = get_latest_bar(alpaca, symbol)
            self.current_crypto_prices[name.split("/")[0] + "(" + symbol[:-3] + ")"] = close
# #######################################TASKS##############################################

    @commands.hybrid_group(name="crypto", invoke_without_command=False, with_app_command=True)
    async def crypto(self, ctx: commands.Context):
        """Crypto commands"""
        pass

    @crypto.command(name="prices", with_app_command=True)
    async def crypto_prices(self, ctx: commands.Context):
        """Get the current price of all cryptos"""
        embed = discord.Embed(title="Current crypto Prices", color=discord.Color.blurple())
        for name_s, price in self.current_crypto_prices.items():
            embed.add_field(name=f"{name_s}", value=f"${price: .2f}", inline=False)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Crypto prices are updated every 5 minutes. Data provided by Alpaca.")
        await ctx.reply(embed=embed)

    @crypto.command(name="price", with_app_command=True)
    @app_commands.describe(crypto_name="The name of the crypto you want to get the price of")
    async def crypto_price(self, ctx: commands.Context, *, crypto_name: available_cryptos):
        """Get the current price of a crypto"""
        embed = discord.Embed(title=f"Current {crypto_name.name} price", color=discord.Color.blurple(),
                              description=f"${self.get_current_crypto_price(crypto_name.name): .5f}")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Crypto prices are updated every 5 minutes. Data provided by Alpaca.")
        await ctx.reply(embed=embed)

    @crypto.command(name="buy", with_app_command=True)
    @app_commands.describe(crypto_name="The name of the crypto you want to buy",
                           amount="The amount of the crypto you want to buy")
    @app_commands.guilds(discord.Object(id=MY_GUILD_ID))
    async def crypto_buy(self, ctx: commands.Context, crypto_name: available_cryptos, amount: float):
        """Buy (fake) crypto (0.01% commission per trade)"""
        wallet, bank = await self.currency.get_balance(ctx.author.id)
        price = int(self.get_current_crypto_price(crypto_name.name) * (1 + CRYPTO_TRADING_COMMISSION) * amount)
        if price > wallet:
            return await ctx.reply(f"You don't have enough money in your wallet to buy this amount of {crypto_name.name}.")
        embed = discord.Embed(
            title="Review your order", color=discord.Color.blurple(),
            description=f"Buying {amount} {crypto_name.name} for "
                        f"{price}{CURRENCY_EMOTE} (including {CRYPTO_TRADING_COMMISSION * 100}% commission)")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Confirm or cancel your order within 30 seconds")
        view = Confirm(embed, crypto_name.name, amount, price, ctx.author.id, self)
        await ctx.reply(embed=embed, view=view)

    # show how much crypto user have
    @crypto.command(name="wallet")
    @app_commands.describe(member="user to check balance of, leave blank to check your own balance")
    async def crypto_wallet(self, ctx: commands.Context, member: Optional[discord.Member]):
        """Check yours or someone's crypto wallet"""
        if member is None:
            member = ctx.author

        description_string = ""
        if crypto_holds := await self.get_crypto_holds(ctx.author.id):
            crypto_holds = sorted(crypto_holds, key=lambda x: x[0])
            for coin, amount in crypto_holds:
                description_string += f"{coin:21} - {amount}\n"
        else:
            description_string = "This user doesn't own any crypto"
        embed = discord.Embed(title=f"{member.name}'s crypto wallet", description=description_string)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        await ctx.reply(embed=embed)


async def setup(bot: StarCityBot):
    await bot.add_cog(Crypto(bot))
