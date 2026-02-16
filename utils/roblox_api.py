import aiohttp
import requests
from typing import Dict, List, Optional

class RobloxAPI:
    def __init__(self):
        self.base_url = "https://api.roblox.com"
        self.users_url = "https://users.roblox.com"
        self.groups_url = "https://groups.roblox.com"
    
    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Get Roblox user info including account age"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.users_url}/v1/users/{user_id}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        'id': data['id'],
                        'username': data['name'],
                        'display_name': data.get('displayName', data['name']),
                        'created': data['created'],
                        'description': data.get('description', '')
                    }
                return None
    
    async def get_user_groups(self, user_id: int) -> List[Dict]:
        """Get all groups a user is in with their ranks"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.groups_url}/v2/users/{user_id}/groups/roles") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    groups = []
                    for group_data in data.get('data', []):
                        group = group_data['group']
                        role = group_data['role']
                        groups.append({
                            'id': group['id'],
                            'name': group['name'],
                            'rank': role['name'],
                            'rank_id': role['id']
                        })
                    return groups
                return []
    
    async def get_account_age_days(self, user_id: int) -> int:
        """Calculate account age in days"""
        from datetime import datetime
        user_info = await self.get_user_info(user_id)
        if user_info:
            created = datetime.fromisoformat(user_info['created'].replace('Z', '+00:00'))
            return (datetime.utcnow() - created.replace(tzinfo=None)).days
        return 0
    
    def exchange_code_for_token(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> Optional[Dict]:
        """Exchange OAuth code for access token (sync - called from web server)"""
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        response = requests.post('https://apis.roblox.com/oauth/v1/token', data=token_data)
        
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_user_info_from_token(self, access_token: str) -> Optional[Dict]:
        """Get user info using OAuth token (sync - called from web server)"""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://apis.roblox.com/oauth/v1/userinfo', headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'roblox_id': int(data['sub']),
                'username': data['name']
            }
        return None

roblox_api = RobloxAPI()