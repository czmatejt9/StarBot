# run this before running the bot
import aiosqlite
import discord.utils


async def main():
    conn = await aiosqlite.connect("bot.db")
    cursor = await conn.cursor()
    await cursor.execute("CREATE TABLE IF NOT EXISTS guilds (guild_id INTEGER PRIMARY KEY, prefix TEXT,"
                         " system_channel_id INTEGER)")
    await cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, display_name TEXT, wallet INTEGER,"
                         "bank INTEGER, xp INTEGER, level INTEGER, daily_streak INTEGER, daily_today INTEGER)")
    await cursor.execute("CREATE TABLE IF NOT EXISTS items (item_id INTEGER PRIMARY KEY, name TEXT, price INTEGER,"
                         "description TEXT)")
    await cursor.execute("CREATE TABLE IF NOT EXISTS user_items (user_id INTEGER, item_id INTEGER, amount INTEGER,"
                         "FOREIGN KEY(user_id) REFERENCES users(user_id), FOREIGN KEY(item_id) REFERENCES items(item_id))")
    await cursor.execute("CREATE TABLE IF NOT EXISTS transactions (transaction_id INTEGER PRIMARY KEY, time TEXT,"
                         "description TEXT, sender_id INTEGER, receiver_id INTEGER, amount INTEGER, tax REAL,"
                         " FOREIGN KEY(sender_id)"
                         " REFERENCES users(user_id), FOREIGN KEY (receiver_id) REFERENCES users(user_id))")
    await cursor.execute("CREATE TABLE IF NOT EXISTS sessions (session_id INT, pid INT, started_at TEXT, ended_at TEXT)")
    await cursor.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)", (0, 0, "0", "0"))
    await cursor.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?)", (0, discord.utils.utcnow(),
                                                                                   "null transaction", 0, 0, 0, 0))
    await cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (1, "CENTRAL BANK", 0, 0, 0, 0, 0, 0))

    await conn.commit()
    await conn.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
