import sqlite3
import discord as ds
import discord.ext.commands as commands
import json


with open('config.json') as f:
    config = json.load(f)


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
        owner_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        is_cryo INTEGER NOT NULL
            CHECK (is_cryo = 1 OR is_cryo = -1)
    )
    ''')
    connection.commit()
    cursor.close()


@bot.slash_command(guild_ids=config['GUILDS'], description='Добавляет вселенную в базу данных и привязывает человека к ней')
async def create_universe(ctx: ds.ApplicationContext, name: str, id: int, owner: ds.Member, channel: ds.TextChannel, is_cryo: bool = False):
    global connection
    is_cryo = 1 if is_cryo else -1
    try:
        cursor = connection.cursor()
        cursor.execute('''
        INSERT INTO Universes
        (id, name, owner_id, channel_id, is_cryo)
        VALUES
        (?, ?, ?, ?, ?)
        ''', (id, name, owner.id, channel.id, is_cryo,))
        connection.commit()
        await wire_user_to_university(ctx, owner, id)
        await ctx.respond('Вселенная успешно была создана')
    except Exception as error:
        print(error.with_traceback(error.__traceback__))
        await ctx.respond('Произошла ошибка')
    finally:
        cursor.close()


@bot.slash_command(guild_ids=config['GUILDS'], description='Удаляет вселенную из базы данных')
async def delete_universe(ctx: ds.ApplicationContext, id: int):
    global connection

    try:
        cursor = connection.cursor()
        cursor.execute('''
        SELECT owner_id FROM Universes WHERE id = ?
        ''', (id,))
        connection.commit()
        owner = cursor.fetchone()
        print(owner)
        if owner[0] != ctx.user.id and not ctx.author.guild_permissions.administrator:
            await ctx.respond('В доступе отказано')
            return
        cursor.close()
        cursor = connection.cursor()
        cursor.execute('''
        DELETE FROM Universes
        WHERE id = ?
        ''', (id,))
        connection.commit()
        await ctx.respond(f'Вселенная под айди {id} была успешно удалена')
        cursor.execute('''
        SELECT id, univ_id_main, univ_id_add_1, univ_id_add_2 FROM Users WHERE univ_id_main = ? OR univ_id_add_1 = ? OR univ_id_add_2 = ?
        ''', (id, id, id,))
        connection.commit()
        users = cursor.fetchall()
        if users:
            await ctx.send('Удаление привязок к данной вселенной...')
            print(users)
            for i in users:
                print(i)
                keys = ['univ_id_main', 'univ_id_add_1', 'univ_id_add_2']
                for j in range(1, len(i)):
                    if i[j] == id:
                        print(keys[j - 1])
                        cursor.execute(f'''
                        UPDATE Users SET {keys[j - 1]} = NULL WHERE id = ?
                        ''', (i[0],))
                        connection.commit()
            await ctx.respond('Привязки успешно удалены')

    except Exception as error:
        print(error.with_traceback(error.__traceback__))
        await ctx.respond('Произошла ошибка')
    finally:
        cursor.close()


@bot.slash_command(guild_ids=config['GUILDS'], desctiption='Добавляет человека в базу данных')
async def register_user_data(ctx: ds.ApplicationContext, user: ds.Member, univ_id_main: int = None, univ_id_1: int = None, univ_id_2: int = None):
    global connection
    try:
        cursor = connection.cursor()

        async def check_if_exists(univ_id):
            if not univ_id:
                return True
            cursor_checker = connection.cursor()
            cursor_checker.execute('''
                SELECT id FROM Universes WHERE id = ?
            ''', (univ_id,))
            connection.commit()
            if cursor_checker.fetchone() is None:
                await ctx.respond(f'Нет вселенной под айди {univ_id}')
                cursor_checker.close()
                return False
            cursor_checker.close()
            return True

        if not await check_if_exists(univ_id_main) or not await check_if_exists(univ_id_1) or not await check_if_exists(univ_id_2):
            return

        cursor.execute('''
            INSERT INTO Users
            (id, univ_id_main, univ_id_add_1, univ_id_add_2)
            VALUES
            (?, ?, ?, ?)
        ''', (user.id, univ_id_main, univ_id_1, univ_id_2,))
        connection.commit()
        await ctx.respond('Успех!')
    except Exception as error:
        print(error.with_traceback(error.__traceback__))
        await ctx.respond('Произошла ошибка')
    finally:
        cursor.close()


@bot.slash_command(guild_ids=config['GUILDS'], desctiption='Привязывает человека к вселенной')
async def wire_user_to_university(ctx: ds.ApplicationContext, user: ds.Member, univ_id: int):
    global connection
    try:
        cursor = connection.cursor()
        cursor.execute('''
        SELECT id, univ_id_main, univ_id_add_1, univ_id_add_2 FROM Users WHERE id = ?
        ''', (user.id,))
        connection.commit()
        data = cursor.fetchone()
        if not data:
            await register_user_data(ctx, user, univ_id)
            cursor.close()
            return
        keys = ['univ_id_main', 'univ_id_add_1', 'univ_id_add_2']
        for i in range(1, len(data)):
            if not data[i]:
                cursor.execute(f'''
                UPDATE Users SET {keys[i - 1]} = ? WHERE id = ?
                ''', (univ_id, user.id))
                connection.commit()
                cursor.close()
                return
        await ctx.respond('Невозможно зарегистрировать более 3-х вселенных на одного человека')
    except Exception as error:
        print(error.with_traceback(error.__traceback__))
        await ctx.respond('Произошла ошибка')
    finally:
        cursor.close()


bot.run(config['TOKEN'])
