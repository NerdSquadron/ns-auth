import discord
from discord.ext import commands
from discord.ui import Button, View
import secrets
from database import db
from config import config

class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="verify_me")
    async def verify_me(self, ctx: commands.Context):
        """Get Roblox verification link"""
        discord_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Check if already verified (has BotVerified role)
        bot_verified_role = discord.utils.get(ctx.guild.roles, name="BotVerified")
        if bot_verified_role and bot_verified_role in ctx.author.roles:
            await ctx.send("✅ You're already verified!", delete_after=10)
            return
        
        # Check if already verified in database too
        if await db.is_verified(discord_id):
            # Give role if missing
            if bot_verified_role and bot_verified_role not in ctx.author.roles:
                try:
                    await ctx.author.add_roles(bot_verified_role)
                    await ctx.send("✅ You're verified! Role assigned.", delete_after=10)
                except:
                    await ctx.send("✅ You're verified! (Could not assign role, contact admin)", delete_after=10)
            else:
                await ctx.send("✅ You're already verified!", delete_after=10)
            return
        
        # Generate state code
        state_code = secrets.token_urlsafe(32)
        await db.create_pending_verification(discord_id, state_code, guild_id)
        
        # Get credentials from database
        creds = db.get_credentials()
        client_id = creds.get('roblox_client_id', '')
        redirect_uri = creds.get('roblox_redirect_uri', '')
        
        if not client_id or not redirect_uri:
            await ctx.send("❌ Bot not fully configured yet. Contact admin.", delete_after=10)
            return
        
        # Create OAuth URL
        auth_url = (
            f"https://apis.roblox.com/oauth/v1/authorize?"
            f"client_id={client_id}&"
            f"response_type=code&"
            f"redirect_uri={redirect_uri}&"
            f"scope=openid profile&"
            f"state={state_code}"
        )
        
        # Create link button
        view = View()
        link_button = Button(label="🔗 Click to Verify", url=auth_url, style=discord.ButtonStyle.link)
        view.add_item(link_button)
        
        embed = discord.Embed(
            title="Roblox Verification",
            description="Click the button below to verify your Roblox account.\n\nThis link is unique to you and expires in 10 minutes.",
            color=0x00ffff
        )
        embed.set_footer(text="AuthChecker System")
        
        # Send DM for privacy
        try:
            await ctx.author.send(embed=embed, view=view)
            await ctx.send("📩 Check your DMs for the verification link!", delete_after=10)
        except discord.Forbidden:
            # Can't DM, send in channel but delete quickly
            msg = await ctx.send(f"{ctx.author.mention}", embed=embed, view=view)
            await msg.delete(delay=30)
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Verification cog ready")

async def setup(bot):
    await bot.add_cog(Verification(bot))