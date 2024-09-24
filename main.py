import sqlite3
import discord as ds
import discord.ext.commands as commands
import json


with open('config.json') as f:
    config = json.load(f)

intents = ds.Intents.DEFAULT_VALUE

bot = ds.Bot()


@bot.event
async def on_ready():
    global connection
    print('Bot logged')
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY,
        univ_id_main INTEGER,
        univ_id_add_1 INTEGER,
        univ_id_add_2 INTEGER
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Universes (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        channel_id INTEGER NOT NULL,
        is_cryo INTEGER NOT NULL
            CHECK (is_cryo = 1 OR is_cryo = -1)
    )
    ''')
    connection.commit()
    cursor.close()

# @bot.slash_command(guild_ids=config['GUILDS'])
# async def create_universe(ctx: commands.Context, name: str, id: int, channel: ds.TextChannel, is_cryo: bool = False):
#     global connection
#     is_cryo = 1 if is_cryo else -1
#     try:
#         cursor = connection.cursor()


@bot.slash_command(guild_ids=config['GUILDS'])
async def put_data_to_db(ctx: commands.Context, user: ds.Member, univ_id_main: int = None, univ_id_1: int = None, univ_id_2: int = None):
    global connection
    try:
        async def check_if_exists(univ_id):
            if not univ_id:
                return True
            cursor = connection.cursor()
            cursor.execute('''
                SELECT id FROM Universes WHERE id = ?
            ''', (univ_id,))
            connection.commit()
            if cursor.fetchone() is None:
                await ctx.respond(f'Нет вселенной под айди {univ_id}')
                cursor.close()
                return False
            return True

        if not await check_if_exists(univ_id_main) or not await check_if_exists(univ_id_1) or not await check_if_exists(univ_id_2):
            return

        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO Users
            (id, univ_id_main, univ_id_add_1, univ_id_add_1)
            VALUES
            (?, ?, ?, ?)
        ''', (user.id, univ_id_main, univ_id_1, univ_id_2,))
        cursor.close()
        connection.commit()
        await ctx.respond('Успех!')
    except Exception as error:
        await error_handler(ctx, error, univ_id_main, univ_id_1, univ_id_2)
    finally:
        cursor.close()


async def error_handler(ctx: commands.Context, error: Exception, *args):
    if isinstance(error, sqlite3.IntegrityError):
        print(args)
        print(error)
        await ctx.respond('Ошибка: неуникальный ключ (id)')
    else:
        await ctx.respond('Команда не была выполнена полностью, ошибка не идентифицированна, ошибка: ' + str(
            error) + ' обратитесь к разработчику бота')


bot.run(config['TOKEN'])
