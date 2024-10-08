import random
import sqlite3
import discord as ds
import discord.ext.commands as commands
import json


def reload_config():
    global config
    with open('config.json') as f:
        config = json.load(f)


reload_config()

intents = ds.Intents.all()
bot = ds.Bot(intents=intents)


@bot.slash_command(guild_ids=config['GUILDS'], desctiption='Привязывает человека к вселенной')
@commands.has_permissions(administrator=True)
async def config_change(ctx: ds.ApplicationContext, dobryak_enabled: bool = None, admin_reactions_enabled: bool = None,
                 fire_enabled: bool = None, enter_exit_reactions: bool = None):
    names = ['Добряк-страйк', 'Реакция :BASED:', 'Поджиг эчпочмака', 'Реакции захода/ухода']
    keys = ['DOBRYAK-ENABLED', 'ADMIN-REACTIONS-ENABLED', 'FIRE-ENABLED', 'ENTER-EXIT-REACTIONS']
    if dobryak_enabled is not None:
        config[keys[0]] = dobryak_enabled
    if admin_reactions_enabled is not None:
        config[keys[1]] = admin_reactions_enabled
    if fire_enabled is not None:
        config[keys[2]] = fire_enabled
    if enter_exit_reactions is not None:
        config[keys[3]] = enter_exit_reactions
    embed = ds.Embed(title='Новые/текущие настройки:')
    for i in range(len(keys)):
        embed.add_field(name=names[i], value='✅' if config[keys[i]] else '❌', inline=True)
    await ctx.respond(embed=embed)
    with open('config.json', mode='w') as f:
        f.write(json.dumps(config, indent=4))


@bot.event
async def on_ready():
    global connection, ignore_next, dobryak
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
    ignore_next = False
    dobryak = 0
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
        await wire_user_to_universe(ctx, owner, id)
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
async def register_user_data(ctx: ds.ApplicationContext, user: ds.Member, univ_id_main: int = None,
                             univ_id_1: int = None, univ_id_2: int = None):
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

        if not await check_if_exists(univ_id_main) or not await check_if_exists(univ_id_1) or not await check_if_exists(
                univ_id_2):
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
async def wire_user_to_universe(ctx: ds.ApplicationContext, user: ds.Member, univ_id: int):
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


@bot.slash_command(guild_ids=config['GUILDS'], desctiption='Привязывает человека к вселенной')
@commands.has_permissions(administrator=True)
async def unwire_user_from_universe(ctx: ds.ApplicationContext, user: ds.Member, univ_id: int):
    global connection
    try:
        cursor = connection.cursor()
        cursor.execute('''
        SELECT id, univ_id_main, univ_id_add_1, univ_id_add_2 FROM Users WHERE id = ?
        ''', (user.id,))
        connection.commit()
        data = cursor.fetchone()
        if not data:
            await register_user_data(ctx, user)
            cursor.close()
            return
        keys = ['univ_id_main', 'univ_id_add_1', 'univ_id_add_2']
        for i in range(1, len(data)):
            if data[i] == univ_id:
                cursor.execute(f'''
                UPDATE Users SET {keys[i - 1]} = 0 WHERE id = ?
                ''', (user.id,))
                connection.commit()
        await ctx.respond('Успешно отвязан от вселенной')
    except Exception as error:
        print(error.with_traceback(error.__traceback__))
        await ctx.respond('Произошла ошибка')
    finally:
        cursor.close()


@bot.slash_command(guild_ids=config['GUILDS'],
                   description='Пишет все вселенные с привязанными к ним каналами и владельцами')
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

        if not data:
            await ctx.respond('Вселенных с таким параметром не найдено')
        else:
            await ctx.respond(embed=ds.Embed(title='Вселенные'))
            print(len(data))
            for i in range(len(data) // 24):
                embed = ds.Embed(
                )
                for j in range(i * 24, (i + 1) * 24):
                    univ = data[j]
                    title = f'{univ[1]}-{num_to_str(univ[0])}'
                    if univ[4] == 1:
                        title = '❄️ ' + title
                    if univ[4] == -1:
                        title = '🛠️ ' + title
                    print(len(f'Канал: <#{univ[3]}> \nВладелец: <@{univ[2]}>'))
                    embed.add_field(name=title, value=f'Канал: <#{univ[3]}> \nВладелец: <@{univ[2]}>', inline=False)
                await ctx.respond(embed=embed)
            embed = ds.Embed()
            for i in range((len(data) // 24) * 24, len(data) % 24 + (len(data) // 24) * 24):
                univ = data[i]
                title = f'{univ[1]}-{num_to_str(univ[0])}'
                if univ[4] == 1:
                    title = '❄️ ' + title
                if univ[4] == -1:
                    title = '🛠️ ' + title
                print(len(f'Канал: <#{univ[3]}> \nВладелец: <@{univ[2]}>'))
                embed.add_field(name=title, value=f'Канал: <#{univ[3]}> \nВладелец: <@{univ[2]}>', inline=False)
            await ctx.respond(embed=embed)
    except Exception as error:
        print(error.with_traceback(error.__traceback__))
        await ctx.respond('Произошла ошибка')
    finally:
        cursor.close()


@bot.event
async def on_message(message: ds.Message):
    global connection, dobryak
    if message.channel.id == 1276452159495340086 and config['ENTER-EXIT-REACTIONS']:
        await message.add_reaction('<:SAJ:1276288176780218460>')
    elif message.channel.id == 1276219202272886935 and config['ENTER-EXIT-REACTIONS']:
        await message.add_reaction('<:nyehehe:1276290044470104137>')
    if message.channel.id in config['DOBRYAK'] and config['DOBRYAK-ENABLED']:
        emojis = [['0️⃣', '⭕'], ['1️⃣', '🇮', '🕐'], ['2️⃣', '🥈'], ['3️⃣', '🥉'], ['4️⃣', '🍀'], ['5️⃣', '✋'], ['6️⃣', '🕕'],
                  ['7️⃣', '🕖'], ['8️⃣', '🎱'], ['9️⃣', '🕘']]

        def num_to_emoji(num):
            used = []
            result = []
            for i in range(10):
                used.append(0)
            for i in str(num):
                i = int(i)
                result.append(emojis[i][used[i]])
                used[i] += 1
            return result

        history = await message.channel.history(limit=4).flatten()
        if message.content == '<:dobryak:1276304647497449523>' and not message.author.bot:
            if history[1].content != '<:dobryak:1276304647497449523>' and not history[1].author.bot:
                await message.add_reaction('1️⃣')
                dobryak = 1
            elif history[1].author.bot:
                if history[2].content != '<:dobryak:1276304647497449523>':
                    await message.add_reaction('1️⃣')
                    dobryak = 1
            else:
                dobryak += 1
                reactions = num_to_emoji(dobryak)
                for i in reactions:
                    await message.add_reaction(i)
        else:
            if history[1].content == '<:dobryak:1276304647497449523>':
                r = random.randint(1, 3)
                content = ''
                if r == 1:
                    content += 'https://media.discordapp.net/attachments/1283033501456666634/1288229715697598635/f52e9ab170c301e8.png?ex=66f515aa&is=66f3c42a&hm=f51861245951ad7ee29b06ba70acce4c8c538e13865b1dc88b4921eb411d4b72&=&format=webp&quality=lossless&width=350&height=350'
                elif r == 2:
                    content += 'https://media.discordapp.net/attachments/1283033501456666634/1287035125057458226/9_20240920220017.png?ex=66f55a5d&is=66f408dd&hm=ce5fa1bdf36e023fbdf25c2acdc955d5ae04ac709fc0da8833420deb52db6140&=&format=webp&quality=lossless&width=550&height=309'
                else:
                    content += 'https://cdn.discordapp.com/attachments/1283033501456666634/1285574066073374741/2024-09-10-17-22-26.mp4?ex=66f54fa6&is=66f3fe26&hm=8603267df98ab9d1174c6f6c309621d895ae8eea421800c7289514f851994542&'
                await message.channel.send('# Страйк УКРАЛИ на числе ' + str(dobryak) + ' ' + content)
                dobryak = 0
    elif message.channel.id in config['MEMES']:
        if message.attachments or 'https://' in message.content:
            await message.create_thread(name='Обсуждение')
            await message.add_reaction('👍')
            await message.add_reaction('👎')
        else:
            await message.delete()
    if message.author.id == 1018952778191745074 and config['FIRE-ENABLED']:
        await message.add_reaction('🔥')
    if (message.author.top_role.id == 1271043123492950036 or message.author.top_role.id == 1280889101175885969) and config['ADMIN-REACTIONS-ENABLED']:
        await message.add_reaction('<:BASED:1285582754410533008>')


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


@bot.event
async def on_member_update(before: ds.Member, after: ds.Member):
    global connection, ignore_next
    if before.nick != after.nick and not ignore_next:
        cursor = connection.cursor()
        cursor.execute('''
        SELECT id, univ_id_main, univ_id_add_1, univ_id_add_2 FROM Users WHERE id = ?
        ''', (after.id,))
        connection.commit()
        data = cursor.fetchone()
        nick = after.display_name
        print(nick)
        for i in range(1, len(data)):
            if data[i]:
                nick += f' [{num_to_str(data[i])}]'
        await after.edit(nick=nick)
        ignore_next = True
    if ignore_next:
        ignore_next = False


def num_to_str(num: int):
    num = str(num)
    while len(num) < 3:
        num = '0' + num
    return num


bot.run(config['TOKEN'])
