import discord
from discord.ext import commands, tasks
from bot import StarCityBot, MY_GUILD_ID
from alpaca_trade_api import REST
from bot import ALPACA_BASE_URL, ALPACA_KEY_ID, ALPACA_SECRET_KEY


def get_latest_bar(alpaca: REST, symbol):
    """
    Get the latest bar of stock data from Alpaca API.
    """
    bar = alpaca.get_latest_crypto_bar(symbol, "FTXU")
    return bar.t, bar.c


class Crypto(commands.Cog):
    def __init__(self, bot):
        self.bot: StarCityBot = bot
        self.crypto_symbols = self.bot.alpaca.list_assets(status='active', asset_class='crypto')
        self.crypto_symbols = sorted([(asset.symbol.replace("/", ""), asset.name) for asset in self.crypto_symbols
                                      if asset.tradable and "/USDT" not in asset.symbol and "/USD" in asset.symbol],
                                     key=lambda x: x[0])
        self.current_crypto_prices = {}
        self.update_crypto_prices.start()

    def cog_unload(self):
        self.update_crypto_prices.cancel()
        self.bot.alpaca.close()
        self.bot.alpaca = None

    @tasks.loop(minutes=5)
    async def update_crypto_prices(self):
        if self.bot.alpaca is None:
            self.bot.alpaca = REST(ALPACA_KEY_ID, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
        for symbol, name in self.crypto_symbols:
            c_time, close = get_latest_bar(self.bot.alpaca, symbol)
            self.current_crypto_prices[(name.split("/")[0][:-1], symbol[:-3])] = close

    @commands.hybrid_group(name="crypto", invoke_without_command=False, with_app_command=True)
    async def crypto(self, ctx: commands.Context):
        """Crypto commands"""
        pass

    @crypto.command(name="prices", with_app_command=True)
    async def crypto_prices(self, ctx: commands.Context):
        """Get the current price of all cryptos"""
        embed = discord.Embed(title="Current crypto Prices", color=discord.Color.blurple())
        for (name, symbol), price in self.current_crypto_prices.items():
            embed.add_field(name=f"{name} ({symbol})", value=f"${price: .2f}", inline=False)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        embed.set_footer(text="Crypto prices are updated every 5 minutes. Data provided by Alpaca.")
        await ctx.send(embed=embed)


async def setup(bot: StarCityBot):
    bot.alpaca = REST(ALPACA_KEY_ID, ALPACA_SECRET_KEY, ALPACA_BASE_URL)
    await bot.add_cog(Crypto(bot))
