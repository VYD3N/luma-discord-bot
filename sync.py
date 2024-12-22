import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from lumadisc import bot

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    
    # Sync commands
    try:
        print("Starting global command sync...")
        await bot.tree.sync()
        print("Commands synced successfully!")
        
        # Print all registered commands
        commands = [cmd.name for cmd in bot.tree.get_commands()]
        print(f'Registered commands: {commands}')
        
    except Exception as e:
        print(f"Error syncing commands: {e}")
    
    await bot.close()

bot.run(DISCORD_TOKEN) 