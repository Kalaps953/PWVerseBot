import sqlite3
import discord as ds
import discord.ext.commands as commands
import config_related as conf

db = 'database.db'


class RegisteredUniverse:
    def __init__(self, univ_id: int, name: str, owner: int | ds.Member, channel: int | ds.TextChannel, state: int):
        self.univ_id = univ_id
        self.name = name
        if isinstance(owner, int):
            self.owner_id = owner
        elif isinstance(owner, ds.Member):
            self.owner_id = owner.id
        else:
            assert TypeError('Must be discord.Member or int')

        if isinstance(channel, int):
            self.channel_id = channel
        elif isinstance(channel, ds.TextChannel):
            self.channel_id = channel.id
        else:
            assert TypeError('Must be discord.TextChannel or int')


class Universes(ds.Cog, name='Database'):
    def __init__(self, bot: ds.Bot):
        self.bot = bot
        self.conn = sqlite3.connect(db)
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS Universes (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        state INTEGER NOT NULL
            CHECK (state = 1 OR state = 2 OR state = -1)
        )
        ''')
        self.conn.commit()
        self.users = self.bot.get_cog('Users')
        self.config = self.bot.get_cog('Config')

    @commands.slash_command(description='Добавляет вселенную в базу данных и привязывает человека к ней',
                            name='create universe')
    @commands.has_permissions(administrator=True)
    async def create_universe(self, ctx: ds.ApplicationContext, name: str, id: int, owner: ds.Member,
                              channel: ds.TextChannel,
                              state: ds.Option(int, choices=[
                                  ds.OptionChoice('в процессе', -1),
                                  ds.OptionChoice('в криокамере', 1),
                                  ds.OptionChoice('готова', 2)])):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            INSERT INTO Universes
            (id, name, owner_id, channel_id, state)
            VALUES
            (?, ?, ?, ?, ?)
            ''', (id, name, owner.id, channel.id, state,))
            self.conn.commit()
            if self.users is not None:
                await self.users.wire_user_to_universe(ctx, owner, id)
            else:
                print('Критический ащипка')
            await ctx.respond('Вселенная успешно была создана')
        except Exception as error:
            print(error.with_traceback(error.__traceback__))
            await ctx.respond('Произошла ошибка')
        finally:
            cursor.close()

    @commands.slash_command(guild_ids=conf['GUILDS'], description='Удаляет вселенную из базы данных')
    async def delete_universe(self, ctx: ds.ApplicationContext, id: int):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT owner_id FROM Universes WHERE id = ?
            ''', (id,))
            self.conn.commit()
            owner = cursor.fetchone()
            if owner[0] != ctx.user.id and not ctx.author.guild_permissions.administrator:
                await ctx.respond('В доступе отказано')
                return
            cursor.close()
            cursor = self.conn.cursor()
            cursor.execute('''
            DELETE FROM Universes
            WHERE id = ?
            ''', (id,))
            self.conn.commit()
            await ctx.respond(f'Вселенная под айди {id} была успешно удалена')
            cursor.execute('''
            SELECT id, univ_id_main, univ_id_add_1, univ_id_add_2 FROM Users WHERE univ_id_main = ? OR univ_id_add_1 = ? OR univ_id_add_2 = ?
            ''', (id, id, id,))
            self.conn.commit()
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
                            self.conn.commit()
                await ctx.respond('Привязки успешно удалены')

        except Exception as error:
            print(error.with_traceback(error.__traceback__))
            await ctx.respond('Произошла ошибка')
        finally:
            cursor.close()


class RegisteredUser:
    keys = []
    def __init__(self, user_id: int, univ_id_main: int = None, univ_id_add_1: int = None, univ_id_add_2: int = None):
        self.user_id = user_id
        self.univ_ids = [univ_id_main, univ_id_add_1, univ_id_add_2]

    @staticmethod
    def get_db_user(user_id):
        try:
            conn = sqlite3.connect(db)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id, univ_id_main, univ_id_add_1, univ_id_add_2 FROM Users WHERE id = ?
            ''', (user_id,))
            conn.commit()
            data = cursor.fetchone()
            if data:
                return RegisteredUser(data[0], data[1], data[2], data[3])
        finally:
            cursor.close()
            conn.close()
        return None

    def user_to_list(self) -> list:
        return [self.user_id, self.univ_ids[0], self.univ_ids[1], self.univ_ids[2]]


class Users(ds.Cog):
    def __init__(self, bot: ds.Bot):
        self.bot = bot
        self.conn = sqlite3.connect(db)
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY,
            univ_id_main INTEGER,
            univ_id_add_1 INTEGER,
            univ_id_add_2 INTEGER
        )
        ''')
        self.conn.commit()

    def set_user_to(self, user: RegisteredUser):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT id FROM Users WHERE id = ?
            ''', (user.user_id,))
            self.conn.commit()
            if cursor.fetchone():
                cursor.execute('''
                UPDATE Users SET univ_id_main = ? WHERE id = ?
                ''', (user.univ_ids[0], user.user_id))
                cursor.execute('''
                UPDATE Users SET univ_id_add_1 = ? WHERE id = ?
                ''', (user.univ_ids[1], user.user_id))
                cursor.execute('''
                UPDATE Users SET univ_id_add_2 = ? WHERE id = ?
                ''', (user.univ_ids[2], user.user_id))
            else:
                cursor.execute('''
                INSERT INTO Users
                (id, univ_id_main, univ_id_add_1, univ_id_add_2)
                VALUES
                (?, ?, ?, ?)
                ''', (user.user_id, user.univ_ids[0], user.univ_ids[1], user.univ_ids[2]))
            self.conn.commit()
        finally:
            cursor.close()

    @commands.slash_command()
    async def wire_user_to_university(self, user_id, univ_id):
        try:
            user = RegisteredUser.get_db_user(user_id)
            if not user:
                data = RegisteredUser.get_db_user(user_id).user_to_list()
            else:
                self.set_user_to(RegisteredUser(user_id))
                data = [user_id, None, None, None]

            for i in range(1, len(data)):

