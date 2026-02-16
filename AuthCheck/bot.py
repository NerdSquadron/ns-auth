import discord
from discord.ext import commands
import asyncio
import os
import threading
from database import db
from config import config

# Setup intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class AuthChecker(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
    
    async def setup_hook(self):
        # Load cogs
        await self.load_extension('cogs.verification')
        await self.load_extension('cogs.background_check')
        
        # Sync commands
        await self.tree.sync()
        print("Commands synced")
    
    async def on_ready(self):
        print(f'Bot logged in as {self.user}')
        print(f'In {len(self.guilds)} guilds')

def run_flask_app():
    """Run Flask in background thread"""
    from web_server import app
    import os
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def main():
    # Initialize database
    asyncio.run(db.init())
    
    # Check if credentials exist
    creds = db.get_credentials()
    token = creds.get('discord_token') or config.DISCORD_TOKEN
    
    if not token:
        print("ERROR: No Discord token configured!")
        print("Please set up the bot via the dashboard first.")
        return
    
    # Start Flask web server in background
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    print("Web server started")
    
    # Start bot
    bot = AuthChecker()
    bot.run(token)

if __name__ == "__main__":
    main()