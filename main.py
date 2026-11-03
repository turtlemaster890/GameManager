import os

import discord
from dotenv import load_dotenv

from bot import GameBot

intents = discord.Intents.default()
bot = GameBot(intents=intents)


load_dotenv()
bot.bot.run(os.getenv("TOKEN"))
