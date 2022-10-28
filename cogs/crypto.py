from enum import Enum
import discord
from discord.ext import commands, tasks
from bot import StarCityBot, MY_GUILD_ID
from alpaca_trade_api import REST
from bot import ALPACA_BASE_URL, ALPACA_KEY_ID, ALPACA_SECRET_KEY

alpaca = REST(ALPACA_KEY_ID, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
crypto_symbols = alpaca.list_assets(status='active', asset_class='crypto')
crypto_symbols = sorted([(asset.symbol.replace("/", ""), asset.name) for asset in crypto_symbols
                        if asset.tradable and "/USDT" not in asset.symbol and "/USD" in asset.symbol],
                        key=lambda x: x[0])
available_cryptos = Enum("available_cryptos", {name.split("/")[0] + symbol[:-3]: i
                                               for i, (symbol, name) in enumerate(crypto_symbols)})


def get_latest_bar(alpaca: REST, symbol):
    """
    Get the latest bar of stock data from Alpaca API.
    """
    bar = alpaca.get_latest_crypto_bar(symbol, "FTXU")
    return bar.t, bar.c


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot: StarCityBot = bot
        self.crypto_symbols = crypto_symbols
        self.current_crypto_prices = {}
        self.update_crypto_prices.start()

    def cog_unload(self):
        self.update_crypto_prices.cancel()
        alpaca.close()

    @tasks.loop(minutes=5)
    async def update_crypto_prices(self):
        for symbol, name in self.crypto_symbols:
            c_time, close = get_latest_bar(alpaca, symbol)
            self.current_crypto_prices[name.split("/")[0] + symbol[:-3]] = close

    @commands.hybrid_group(name="crypto", invoke_without_command=False, with_app_command=True)
    async def crypto(self, ctx: commands.Context):
        """Crypto commands"""
        pass

    @crypto.command(name="prices", with_app_command=True)
    async def crypto_prices(self, ctx: commands.Context):
        await ctx.send(str(self.current_crypto_prices))
        """Get the current price of all cryptos"""
        embed = discord.Embed(title="Current crypto Prices", color=discord.Color.blurple())
        for name_s, price in self.current_crypto_prices.items():
            embed.add_field(name=f"{name_s.split()[0]} ({name_s.split[1]})", value=f"${price: .2f}", inline=False)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Crypto prices are updated every 5 minutes. Data provided by Alpaca.")
        await ctx.send(embed=embed)

    @crypto.command(name="price", with_app_command=True)
    async def crypto_price(self, ctx: commands.Context, name: available_cryptos):
        """Get the current price of a crypto"""
        embed = discord.Embed(title=f"Current {name} price", color=discord.Color.blurple(),
                              description=f"${self.current_crypto_prices[name]: .5f}")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Crypto prices are updated every 5 minutes. Data provided by Alpaca.")
        await ctx.send(embed=embed)


async def setup(bot: StarCityBot):
    await bot.add_cog(Crypto(bot))
