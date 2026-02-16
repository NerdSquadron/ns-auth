import secrets
from datetime import datetime

def generate_state_code() -> str:
    """Generate secure random state for OAuth"""
    return secrets.token_urlsafe(32)

def format_account_age(days: int) -> str:
    """Format account age nicely"""
    years = days // 365
    months = (days % 365) // 30
    if years > 0:
        return f"{years}y {months}m ({days} days)"
    elif months > 0:
        return f"{months}m ({days} days)"
    else:
        return f"{days} days"

def create_report_embed(user_data: dict, blacklisted_groups: list) -> dict:
    """Create report data structure"""
    return {
        'user_id': user_data['discord_id'],
        'username': user_data['roblox_username'],
        'roblox_id': user_data['roblox_id'],
        'account_age': format_account_age(user_data['account_age_days']),
        'blacklisted_groups': blacklisted_groups,
        'checked_at': datetime.utcnow().isoformat()
    }