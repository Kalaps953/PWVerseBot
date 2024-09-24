import datetime
import random
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
        state INTEGER NOT NULL
            CHECK (state = 1 OR state = 2 OR state = -1)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS EverydayKauchook (
        days INTEGER,
        channel_id INTEGER PRIMARY KEY,
        last_date TEXT
    )
    ''')
    connection.commit()
    cursor.close()


@bot.slash_command(guild_ids=config['GUILDS'], description='Добавляет вселенную в базу данных и привязывает человека к ней')
@commands.has_permissions(administrator=True)
async def create_universe(ctx: ds.ApplicationContext, name: str, id: int, owner: ds.Member, channel: ds.TextChannel,
                          state: ds.Option(int, choices=[
                            ds.OptionChoice('в процессе', -1),
                            ds.OptionChoice('в криокамере', 1),
                            ds.OptionChoice('готова', 2)])):
    global connection
    try:
        cursor = connection.cursor()
        cursor.execute('''
        INSERT INTO Universes
        (id, name, owner_id, channel_id, state)
        VALUES
        (?, ?, ?, ?, ?)
        ''', (id, name, owner.id, channel.id, state,))
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
            for i in users:
                keys = ['univ_id_main', 'univ_id_add_1', 'univ_id_add_2']
                for j in range(1, len(i)):
                    if i[j] == id:
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
@commands.has_permissions(administrator=True)
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
@commands.has_permissions(administrator=True)
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


@bot.slash_command(guild_ids=config['GUILDS'], description='Пишет все вселенные с привязанными к ним каналами и владельцами')
async def get_universes(ctx: ds.ApplicationContext,
                        user: ds.Member = None,
                        state: ds.Option(int, choices=[
                            ds.OptionChoice('в процессе', -1),
                            ds.OptionChoice('в криокамере', 1),
                            ds.OptionChoice('все', 0),
                            ds.OptionChoice('готова', 2)
                        ]) = 0,
                        id: int = None):
    global connection
    try:
        cursor = connection.cursor()
        if id:
            cursor.execute('''
            SELECT id, name, owner_id, channel_id, state FROM Universes WHERE id = ?
            ''', (id,))
        elif user:
            if state == 0:
                cursor.execute('''
                SELECT id, name, owner_id, channel_id, state FROM Universes WHERE owner_id = ?
                ''', (user.id,))
            else:
                cursor.execute('''
                SELECT id, name, owner_id, channel_id, state FROM Universes WHERE state = ? AND owner_id = ? 
                ''', (state, user.id,))
        else:
            if state == 0:
                cursor.execute('''
                SELECT id, name, owner_id, channel_id, state FROM Universes
                ''')
            else:
                cursor.execute('''
                SELECT id, name, owner_id, channel_id, state FROM Universes WHERE state = ?
                ''', (state,))
        data = cursor.fetchall()
        for i in range(len(data)):
            univ = data[i]
            title = f'{univ[1]}-{univ[0]}'
            if univ[4] == 1:
                title = '❄️-' + title
            if univ[4] == -1:
                title = '🛠️-' + title
            embed = ds.Embed(
                title=title,
                description=f'<#{univ[3]}>'
            ).set_author(name=ctx.guild.get_member(univ[2]).name, icon_url=ctx.guild.get_member(univ[2]).display_avatar.url)
            if i == 0:
                await ctx.respond(embed=embed)
            else:
                await ctx.send(embed=embed)
        if not data:
            await ctx.respond('Вселенных с таким параметром не найдено')
    except Exception as error:
        print(error.with_traceback(error.__traceback__))
        await ctx.respond('Произошла ошибка')
    finally:
        cursor.close()


@bot.event
async def on_message(message: ds.Message):
    global connection
    if message.author.id == 1018952778191745074:
        await message.add_reaction('🔥')
    if message.channel.id == 1283033501456666634:
        if message.content != ':dobryak:':
            try:
                cursor = connection.cursor()
                cursor.execute('''
                SELECT univ_id_main, univ_id_add_1, univ_id_add_2 FROM Users WHERE id = ?
                ''', (message.author.id,))
                connection.commit()
                if data := cursor.fetchone():
                    for i in data:
                        cursor.execute('''
                        SELECT days, channel_id, last_date FROM EverydayKauchook WHERE channel_id = ?
                        ''', (i,))
                        connection.commit()
                        if kauchook_data := cursor.fetchone():
                            cursor.execute('''
                            UPDATE EverydayKauchook SET days = ? WHERE channel_id = ?
                            ''', (kauchook_data[0] + random.randint(0, 3), i,))
                            connection.commit()
                            continue
                        cursor.execute('''
                        INSERT INTO EverydayKauchook
                        (days, channel_id, last_date)
                        VALUES
                        (?, ?, ?)
                        ''', (random.randint(0, 3), i, datetime.date.strftime(datetime.date.today(), '%d.%m'),))
            except Exception as error:
                print('Не получилось(')
            finally:
                cursor.close()


@bot.event
async def on_member_join(member: ds.Member):
    global connection
    try:
        cursor = connection.cursor()
        cursor.execute('''
        SELECT id FROM Users WHERE id = ?
        ''', (member.id,))
        connection.commit()
        if not cursor.fetchone():
            cursor.execute('''
                        INSERT INTO Users
                        (id, univ_id_main, univ_id_add_1, univ_id_add_2)
                        VALUES
                        (?, NULL, NULL, NULL)
                    ''', (member.id,))
            connection.commit()
    except Exception as error:
        print(error.with_traceback(error.__traceback__))
        print('Добавление человека в датабазу неуспешно')
    finally:
        cursor.close()


bot.run(config['TOKEN'])
