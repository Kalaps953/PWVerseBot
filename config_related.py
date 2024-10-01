import json
import discord as ds
import discord.ext.commands as commands


class Config(ds.Cog):
    config_path = 'config.json'

    def __init__(self, bot: ds.Bot):
        self.bot = bot
        self.keys = [
            'DOBRYAK',
            'MEMES',
            'DOBRYAK-ENABLED',
            'ADMIN-REACTIONS-ENABLED',
            'FIRE-ENABLED',
            'ENTER-EXIT-REACTIONS'
        ]
        self.human_readable = [
            'Каналы добряк-страйков',
            'Каналы с реакциями и комментариями',
            'Подсчет добряк-страйка',
            'Реакции :BASED: под админами',
            'Поджигание Эчпочмака',
            'Реакции входа/выхода'
        ]

    @staticmethod
    def get_config():
        with open(Config.config_path) as f:
            return json.load(f)

    @staticmethod
    def set_config(config: hash):
        with open(Config.config_path, 'w') as f:
            f.write(json.dumps(config, indent=4))

    @commands.slash_command()
    @commands.has_permissions(administator=True)
    async def set_conf(self,
                       ctx: ds.ApplicationContext,
                       dobryak_channels: list[int] = None,
                       react_channels: list[int] = None,
                       dobryak_strike: bool = None,
                       admin_reactions: bool = None,
                       fire: bool = None,
                       enter_exit_reactions: bool = None):
        config = self.get_config()
        params = [dobryak_channels, react_channels, dobryak_strike, admin_reactions, fire, enter_exit_reactions]
        for i in range(len(params)):
            if params[i] is not None:
                config[self.keys[i]] = params[i]
        self.set_config(config)
        await self.print_conf(ctx)

    @commands.slash_command()
    async def print_conf(self, ctx: ds.ApplicationContext):
        config = self.get_config()
        embed = ds.Embed(title='Конфиг:')
        for i in range(len(self.keys)):
            if isinstance(config[self.keys[i]], bool):
                embed.add_field(name=self.human_readable[i], value='✅' if config[self.keys[i]] else '❌')
            else:
                channels = ''
                for j in config[self.keys[i]]:
                    channels += f'<#{j}>\n'
                embed.add_field(name=self.human_readable[i], value=channels)
        await ctx.respond(embed=embed)
