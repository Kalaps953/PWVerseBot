import sqlite3

import discord
import discord as ds
import json

global connection, cursor

intents = discord.Intents.DEFAULT_VALUE

bot = ds.Client()


@bot.event
async def on_ready():
    print('Bot logged')
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        univ_id TEXT NOT NULL,
        age INTEGER
    )
    ''')


with open('config.json') as f:
    bot.run(json.load(f)['TOKEN'])
