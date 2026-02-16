import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Discord
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    
    # Roblox OAuth
    ROBLOX_CLIENT_ID = os.getenv('ROBLOX_CLIENT_ID')
    ROBLOX_CLIENT_SECRET = os.getenv('ROBLOX_CLIENT_SECRET')
    ROBLOX_REDIRECT_URI = os.getenv('ROBLOX_REDIRECT_URI', '')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///authchecker.db')
    
    # Default channels (can be overridden per guild)
    VERIFY_CHANNEL_ID = 1251815787123970049
    REPORT_CHANNEL_ID = 1467399827590484078
    
    # Verified role name (bot creates this if missing)
    VERIFIED_ROLE_NAME = "BotVerified"

config = Config()