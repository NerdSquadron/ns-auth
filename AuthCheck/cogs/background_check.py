import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from database import db
from utils.roblox_api import roblox_api

class BackgroundCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def assign_verified_role(self, member: discord.Member):
        """Assign BotVerified role if verified in database"""
        bot_verified_role = discord.utils.get(member.guild.roles, name="BotVerified")
        if not bot_verified_role:
            return False
        
        if await db.is_verified(member.id):
            if bot_verified_role not in member.roles:
                try:
                    await member.add_roles(bot_verified_role)
                    return True
                except:
                    pass
        return False
    
    @app_commands.command(name="check", description="Run background check on a user (Admin only)")
    @app_commands.describe(user="The user to check")
    @app_commands.checks.has_permissions(administrator=True)
    async def check_command(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is verified
        verified_data = await db.get_verified_user(user.id)
        
        if not verified_data:
            await interaction.followup.send(f"❌ {user.mention} is not verified. They must use `!verify_me` first.", ephemeral=True)
            return
        
        # Assign role if missing
        role_assigned = await self.assign_verified_role(user)
        
        roblox_id = verified_data['roblox_id']
        roblox_username = verified_data['roblox_username']
        
        # Get guild settings
        settings = db.get_guild_settings(interaction.guild_id)
        blacklisted_ids = settings.get('blacklisted_groups', [])
        report_channel_id = settings.get('report_channel_id')
        
        try:
            # Fetch Roblox data
            user_info = await roblox_api.get_user_info(roblox_id)
            groups = await roblox_api.get_user_groups(roblox_id)
            account_age_days = await roblox_api.get_account_age_days(roblox_id)
            
            # Check blacklisted groups
            blacklisted_found = []
            for group in groups:
                if group['id'] in blacklisted_ids:
                    blacklisted_found.append({
                        'name': group['name'],
                        'rank': group['rank']
                    })
            
            # Build report embed
            report_embed = discord.Embed(
                title="🔍 Background Check Report",
                description=f"Target: {user.mention}",
                color=0xff0000 if blacklisted_found else 0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            report_embed.add_field(name="User ID", value=str(user.id), inline=True)
            report_embed.add_field(name="Username", value=roblox_username, inline=True)
            report_embed.add_field(name="Roblox ID", value=str(roblox_id), inline=True)
            
            # Account age formatting
            years = account_age_days // 365
            months = (account_age_days % 365) // 30
            age_str = f"{years}y {months}m ({account_age_days} days)"
            report_embed.add_field(name="Account Age", value=age_str, inline=False)
            
            # Blacklisted groups
            if blacklisted_found:
                blacklist_text = "\n".join([f"• **{g['name']}** - Rank: `{g['rank']}`" for g in blacklisted_found])
                report_embed.add_field(
                    name=f"⚠️ Blacklisted Groups ({len(blacklisted_found)})",
                    value=blacklist_text,
                    inline=False
                )
            else:
                report_embed.add_field(name="Blacklisted Groups", value="✅ None found", inline=False)
            
            # Add role status
            if role_assigned:
                report_embed.add_field(name="Role Status", value="✅ BotVerified role assigned", inline=False)
            
            report_embed.set_footer(text=f"Checked by {interaction.user} | AuthChecker")
            
            # Send to report channel
            if report_channel_id:
                report_channel = self.bot.get_channel(report_channel_id)
                if report_channel:
                    await report_channel.send(embed=report_embed)
            
            await interaction.followup.send(f"✅ Report generated and sent to <#{report_channel_id}>", ephemeral=True)
            
        except Exception as e:
            print(f"Error in check command: {e}")
            await interaction.followup.send("❌ An error occurred while checking the user.", ephemeral=True)
    
    @check_command.error
    async def check_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need Administrator permission to use this.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BackgroundCheck(bot))