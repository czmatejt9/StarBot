import os
from enum import Enum
from typing import Optional, Literal
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks
from bot import StarCityBot, MY_GUILD_ID
from alpaca_trade_api import REST, TimeFrame
from bot import ALPACA_BASE_URL, ALPACA_KEY_ID, ALPACA_SECRET_KEY

HOME_PATH = os.path.dirname(os.path.abspath(__name__))
alpaca = REST(ALPACA_KEY_ID, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
crypto_symbols = alpaca.list_assets(status='active', asset_class='crypto')
crypto_symbols = sorted([(asset.symbol.replace("/", ""), asset.name) for asset in crypto_symbols
                        if asset.tradable and "/USDT" not in asset.symbol and "/USD" in asset.symbol],
                        key=lambda x: x[0])
my_list = [name.split("/")[0] + "(" + symbol[:-3] + ")" for symbol, name in crypto_symbols]
available_cryptos = Literal[tuple(my_list)]
CURRENCY_EMOTE = "<:SMURFPENIZE:1038485999795318844>"
PENDING_CONFIRMATIONS = []


def get_latest_bar(alpaca: REST, symbol):
    """
    Get the latest bar of stock data from Alpaca API.
    """
    bar = alpaca.get_latest_crypto_bar(symbol, "BNCU")
    return bar.t, bar.c


class Confirm(discord.ui.View):
    def __init__(self, embed: discord.Embed, crypto: str, amount: float, price: float, user_id: int,
                 crypto_cls: "Crypto", buy_or_sell: Literal["buy", "sell"]):
        super().__init__(timeout=30.0)
        self.embed = embed
        self.crypto = crypto
        self.amount = amount
        self.price = price
        self.price_per_unit = price / amount
        self.user_id = user_id
        self.crypto_cls = crypto_cls
        self.buy_or_sell = buy_or_sell
        self.message = None
        global PENDING_CONFIRMATIONS
        PENDING_CONFIRMATIONS.append(user_id)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed.title = "Confirmed ✅"
        if self.buy_or_sell == "buy":
            self.embed.set_footer(text="Purchase confirmed")
            await interaction.response.edit_message(embed=self.embed, view=None)

            await self.crypto_cls.bot.get_cog("Currency").transfer_money(self.user_id, 1, self.price, 0,
                                                                         f"{self.crypto} purchase")
            await self.crypto_cls.give_crypto(self.user_id, self.crypto, self.amount, self.price_per_unit)
        else:
            self.embed.set_footer(text="Sale confirmed")
            await interaction.response.edit_message(embed=self.embed, view=None)

            await self.crypto_cls.bot.get_cog("Currency").transfer_money(1, self.user_id, self.price,
                                                                         0, f"{self.crypto} sale")
            profit = await self.crypto_cls.remove_crypto(self.user_id, self.crypto, self.amount, self.price_per_unit)
            async with self.crypto_cls.bot.db.cursor() as cursor:
                await cursor.execute("UPDATE users SET crypto_profit = crypto_profit + ? WHERE user_id = ?",
                                     (profit, self.user_id))
                await self.crypto_cls.bot.db.commit()

        global PENDING_CONFIRMATIONS
        PENDING_CONFIRMATIONS.remove(self.user_id)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed.title = "Cancelled ❎"
        if self.buy_or_sell == "buy":
            self.embed.set_footer(text="Purchase cancelled")
        else:
            self.embed.set_footer(text="Sell cancelled")
        await interaction.response.edit_message(embed=self.embed, view=None)

        global PENDING_CONFIRMATIONS
        PENDING_CONFIRMATIONS.remove(self.user_id)
        self.stop()

    async def on_timeout(self):
        self.embed.title = "Timed out ⏰"
        if self.buy_or_sell == "buy":
            self.embed.set_footer(text="Purchase timed out")
        else:
            self.embed.set_footer(text="Sell timed out")
        await self.message.edit(embed=self.embed, view=None)
        global PENDING_CONFIRMATIONS
        PENDING_CONFIRMATIONS.remove(self.user_id)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You are not the author of this message!", ephemeral=True)
            return False
        return True


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot: StarCityBot = bot
        self.crypto_symbols_dict = {name.split("/")[0] + "(" + symbol[:-3] + ")": symbol for symbol, name in crypto_symbols}
        self.current_crypto_prices = {}
        self.update_crypto_prices.start()
        self.currency = self.bot.get_cog("Currency")  # to access the currency cog, use self.currency

    def cog_unload(self):
        self.update_crypto_prices.cancel()
        alpaca.close()

    def generate_crypto_graph(self, crypto_name: str,  timeframe: str):
        symbol = self.crypto_symbols_dict[crypto_name]
        str_to_days = {"today": 0, "3days": 2, "1week": 6, "1month": 30, "3months": 90, "6months": 182, "1year": 364, "3years": 1095}
        days = str_to_days[timeframe]
        timeunit = TimeFrame.Minute if timeframe in {"today"}\
            else TimeFrame.Hour if timeframe in {"3days", "1week"} else TimeFrame.Day
        bars = alpaca.get_crypto_bars(symbol, timeunit, (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d"))
        bars = {bar.t.astimezone(pytz.utc): bar.c for bar in bars}
        plt.figure(figsize=(16, 9))
        plt.plot(bars.keys(), bars.values())
        plt.xlabel("Time", fontdict={"fontsize": 16, "fontweight": "bold", "horizontalalignment": "right"})
        plt.ylabel("Price", fontdict={"fontsize": 16, "fontweight": "bold", "verticalalignment": "top"})
        plt.grid()
        plt.xticks(rotation=45)
        plt.yticks(rotation=45)
        plt.title(f"{crypto_name} price over the last {timeframe}. (Price in USD, Time in UTC)" if timeframe != "today"
                  else f"{crypto_name} price today. (Price in USD, Time in UTC)",
                  fontdict={"fontsize": 20, "fontweight": "bold"})
        plt.savefig("images/graph.png")
        plt.clf()
        return "images/graph.png"

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

    async def remove_crypto(self, user_id, crypto, amount, price_per_unit) -> float:  # returns profit
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT * FROM crypto_holdings WHERE user_id = ? AND coin = ?", (user_id, crypto))
            a = await cursor.fetchone()
            _user_id, _crypto, _amount, _avg_price = a
            new_amount = _amount - amount
            if new_amount < 0:
                raise ValueError("Not enough crypto")
            profit = (price_per_unit - _avg_price) * amount
            if new_amount == 0:
                await cursor.execute("DELETE FROM crypto_holdings WHERE user_id = ? AND coin = ?", (user_id, crypto))
            else:
                await cursor.execute("UPDATE crypto_holdings SET amount = ? WHERE user_id = ? AND coin = ?",
                                     (new_amount, user_id, crypto))
            return profit

    async def get_crypto_holds(self, user_id):
        async with self.bot.db.cursor() as cursor:
            cursor: aiosqlite.Cursor
            await cursor.execute("SELECT coin, amount FROM crypto_holdings WHERE user_id = ?", (user_id, ))
            crypto_holds = await cursor.fetchall()
        return list(crypto_holds) if crypto_holds else None

# #######################################TASKS##############################################
    @tasks.loop(minutes=5)
    async def update_crypto_prices(self):
        for symbol, name in crypto_symbols:
            c_time, close = get_latest_bar(alpaca, symbol)
            self.current_crypto_prices[name.split("/")[0] + "(" + symbol[:-3] + ")"] = close
# #######################################TASKS##############################################

    @commands.command(name="crypto_debug", hidden=True)
    @commands.is_owner()
    async def crypto_debug(self, ctx):
        await ctx.send(self.current_crypto_prices)

    @commands.hybrid_group(name="crypto", invoke_without_command=False, with_app_command=True)
    async def crypto(self, ctx: commands.Context):
        """Crypto commands"""
        pass

    # invoke the following with crypto price with no argument
    async def crypto_prices(self, ctx: commands.Context):
        """Get the current price of all cryptos"""
        embed = discord.Embed(title="Current crypto Prices", color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
        for name_s, price in self.current_crypto_prices.items():
            embed.add_field(name=f"{name_s}", value=f"${price: .2f}", inline=False)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Crypto prices are updated every 5 minutes. Data provided by Alpaca.")
        await ctx.reply(embed=embed)

    @crypto.command(name="price", with_app_command=True)
    @app_commands.describe(crypto_name="The name of the crypto you want to get the price of")
    async def crypto_price(self, ctx: commands.Context, *, crypto_name: Optional[available_cryptos]):
        """Get the current price of a crypto"""
        if crypto_name is None:
            await self.crypto_prices(ctx)
            return

        if isinstance(crypto_name, int):
            crypto_name = crypto_symbols[crypto_name][1].split("/")[0] + "(" + crypto_symbols[crypto_name][0][:-3] + ")"

        embed = discord.Embed(title=f"Current {crypto_name} price", color=discord.Color.blurple(),
                              description=f"${self.get_current_crypto_price(crypto_name): .5f}", timestamp=discord.utils.utcnow())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Crypto prices are updated every 5 minutes. Data provided by Alpaca.")
        await ctx.reply(embed=embed)

    @crypto.command(name="buy", with_app_command=True)
    @app_commands.describe(crypto_name="The name of the crypto you want to buy",
                           amount="The amount of the crypto you want to buy")
    async def crypto_buy(self, ctx: commands.Context, crypto_name: available_cryptos, amount: float, quick_buy: bool = False):
        """Buy (fake) crypto"""
        if ctx.author.id in PENDING_CONFIRMATIONS:
            await ctx.reply("You already have a pending confirmation. Please confirm or deny that first.")
            return
        if isinstance(crypto_name, int):
            crypto_name = crypto_symbols[crypto_name][1].split("/")[0] + "(" + crypto_symbols[crypto_name][0][:-3] + ")"

        wallet, bank = await self.currency.get_balance(ctx.author.id)
        price = int(self.get_current_crypto_price(crypto_name) * amount)
        if price > wallet:
            return await ctx.reply(f"You don't have enough money in your wallet to buy this amount of {crypto_name}.")
        if price == 0:  # minimal price is 1
            price = 1
        if not quick_buy:
            embed = discord.Embed(
                title="Review your PURCHASE order", color=discord.Color.blurple(),
                description=f"Buying {amount} {crypto_name} for {price}{CURRENCY_EMOTE}",
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
            embed.set_footer(text="Confirm or cancel your order within 30 seconds")
            view = Confirm(embed, crypto_name, amount, price, ctx.author.id, self, "buy")
            msg = await ctx.reply(embed=embed, view=view)
            view.message = msg
        else:
            await self.bot.get_cog("Currency").transfer_money(ctx.author.id, 1, price, 0, f"{crypto_name} purchase")
            await self.give_crypto(ctx.author.id, crypto_name, amount, price / amount)
            await ctx.reply(f"Successfully bought {amount} {crypto_name} for {price}{CURRENCY_EMOTE}")

    @crypto.command(name="sell", with_app_command=True)
    @app_commands.describe(crypto_name="The name of the crypto you want to sell",
                           amount="The amount of the crypto you want to sell")
    async def crypto_sell(self, ctx: commands.Context, crypto_name: available_cryptos, amount: float, quick_sell: bool = False):
        """Sell your (fake) crypto"""
        if ctx.author.id in PENDING_CONFIRMATIONS:
            await ctx.reply("You already have a pending confirmation. Please confirm or deny that first.")
            return
        if isinstance(crypto_name, int):
            crypto_name = crypto_symbols[crypto_name][1].split("/")[0] + "(" + crypto_symbols[crypto_name][0][:-3] + ")"

        crypto_holds = await self.get_crypto_holds(ctx.author.id)
        if crypto_holds is None:
            return await ctx.reply("You don't own any crypto.")
        crypto_holds = dict(crypto_holds)
        if crypto_name not in crypto_holds:
            return await ctx.reply(f"You don't own any {crypto_name}.")
        if amount > crypto_holds[crypto_name]:
            return await ctx.reply(f"You don't own that much {crypto_name}.")

        price = int(self.get_current_crypto_price(crypto_name) * amount)
        if not quick_sell:
            embed = discord.Embed(
                title="Review your SELL order", color=discord.Color.blurple(),
                description=f"Selling {amount} {crypto_name} for {price}{CURRENCY_EMOTE}",
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
            embed.set_footer(text="Confirm or cancel your order within 30 seconds")
            view = Confirm(embed, crypto_name, amount, price, ctx.author.id, self, "sell")
            msg = await ctx.reply(embed=embed, view=view)
            view.message = msg
        else:
            await self.bot.get_cog("Currency").transfer_money(1, ctx.author.id, price, 0, f"{self.crypto} sale")
            profit = await self.remove_crypto(ctx.author.id, crypto_name, amount, price / amount)
            async with self.bot.db.cursor() as cursor:
                await cursor.execute("UPDATE users SET crypto_profit = crypto_profit + ? WHERE user_id = ?",
                                     (profit, ctx.author.id))
                await self.bot.db.commit()
            await ctx.reply(f"Successfully sold {amount} {crypto_name} for {price}{CURRENCY_EMOTE}")

    # show how much crypto user have
    @crypto.command(name="wallet")
    @app_commands.describe(member="user to check balance of, leave blank to check your own balance")
    async def crypto_wallet(self, ctx: commands.Context, member: Optional[discord.Member]):
        """Check yours or someone's crypto wallet"""
        if member is None:
            member = ctx.author

        # fetch crypto profit from db
        async with self.bot.db.cursor() as cursor:
            await cursor.execute("SELECT crypto_profit FROM users WHERE user_id = ?", (member.id,))
            crypto_profit = await cursor.fetchone()
            crypto_profit = 0 if crypto_profit is None else crypto_profit[0]

        embed = discord.Embed(title=f"{member.name}'s crypto wallet", description=f"Lifetime profit: {crypto_profit}{CURRENCY_EMOTE}",
                              color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
        if crypto_holds := await self.get_crypto_holds(member.id):
            crypto_holds = sorted(crypto_holds, key=lambda x: x[0])
            for coin, amount in crypto_holds:
                embed.add_field(name=f"{coin}", value=f"{amount} ~ {self.get_current_crypto_price(coin) * amount}"
                                                      f"{CURRENCY_EMOTE}", inline=False)
        else:
            embed.add_field(name="No crypto", value="You don't have any crypto in your wallet")
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        await ctx.reply(embed=embed)

    @crypto.command(name="graph", with_app_command=True)
    @app_commands.describe(crypto_name="The crypto you want to get the graph of", time_frame="The time period of the graph")
    async def crypto_graph(self, ctx: commands.Context, crypto_name: available_cryptos,
                           time_frame: Literal["today", "3days", "1week", "1month", "3months", "6months", "1year", "3years"]):
        """Get the graph of a crypto"""
        if isinstance(crypto_name, int):
            crypto_name = crypto_symbols[crypto_name][1].split("/")[0] + "(" + crypto_symbols[crypto_name][0][:-3] + ")"
        file = self.generate_crypto_graph(crypto_name, time_frame)
        file = discord.File(f"{HOME_PATH}/{file}", filename="graph.png")
        await ctx.reply(file=file)


async def setup(bot: StarCityBot):
    await bot.add_cog(Crypto(bot))
