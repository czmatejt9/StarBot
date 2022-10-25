# run this before running the bot
import aiosqlite
import discord.utils
import datetime


async def main():
    conn = await aiosqlite.connect("bot.db")
    cursor = await conn.cursor()
    await cursor.execute("CREATE TABLE IF NOT EXISTS guilds (guild_id INTEGER PRIMARY KEY, prefix TEXT,"
                         " system_channel_id INTEGER)")
    await cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, display_name TEXT, wallet INTEGER,"
                         "bank INTEGER, xp INTEGER, level INTEGER, daily_streak INTEGER, daily_today INTEGER)")
    await cursor.execute("CREATE TABLE IF NOT EXISTS items (item_id INTEGER PRIMARY KEY, name TEXT, price INTEGER,"
                         "sell_price INTEGER, description TEXT)")
    await cursor.execute("CREATE TABLE IF NOT EXISTS user_items (user_id INTEGER, item_id INTEGER, amount INTEGER,"
                         "FOREIGN KEY(user_id) REFERENCES users(user_id), FOREIGN KEY(item_id) REFERENCES items(item_id))")
    await cursor.execute("CREATE TABLE IF NOT EXISTS transactions (transaction_id INTEGER PRIMARY KEY, time TEXT,"
                         "description TEXT, sender_id INTEGER, receiver_id INTEGER, amount INTEGER, tax REAL,"
                         " FOREIGN KEY(sender_id)"
                         " REFERENCES users(user_id), FOREIGN KEY (receiver_id) REFERENCES users(user_id))")
    await cursor.execute("CREATE TABLE IF NOT EXISTS lottery (lottery_id INTEGER PRIMARY KEY, date TEXT, winner_id INTEGER)")

    await cursor.execute("CREATE TABLE IF NOT EXISTS sessions (session_id INT, pid INT, started_at TEXT, ended_at TEXT)")
    # initial insertions
    #await cursor.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)", (0, 0, "0", "0"))
    #await cursor.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?)", (0, discord.utils.utcnow(),
    #                                                                              "null transaction", 0, 0, 0, 0))
    #await cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (1, "CENTRAL BANK", 0, 0, 0, 0, 0, 0))
    await cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (2, "LOTTO BANK", 0, 0, 0, 0, 0, 0))
    await cursor.execute("INSERT INTO lottery VALUES (?, ?, ?)", (0, datetime.datetime.now().strftime("%Y-%m-%d"), 0))
    # items
    await cursor.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)", (0, "apple", 100, 70, "a delicious apple"))
    await cursor.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)", (1, "Spjáťa's bulletproof vest", 1_000_000,
                                                                      None, "protects you from bullets (and robbers)"))
    await cursor.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)", (2, "lotto ticket", 500, None, "a lotto ticket"))

    await conn.commit()
    await conn.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
