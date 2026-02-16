from flask import Flask, request, redirect
from database import db
from utils.roblox_api import roblox_api
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "AuthChecker Bot is running!"

@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        return "Invalid request", 400
    
    # Get credentials
    creds = db.get_credentials()
    client_id = creds.get('roblox_client_id')
    client_secret = creds.get('roblox_client_secret')
    redirect_uri = creds.get('roblox_redirect_uri')
    
    if not all([client_id, client_secret, redirect_uri]):
        return "Bot not configured", 500
    
    # Exchange code for token
    token_info = roblox_api.exchange_code_for_token(code, client_id, client_secret, redirect_uri)
    
    if not token_info:
        return "Authentication failed", 400
    
    access_token = token_info['access_token']
    
    # Get Roblox user info
    user_info = roblox_api.get_user_info_from_token(access_token)
    
    if not user_info:
        return "Failed to get user info", 400
    
    roblox_id = user_info['roblox_id']
    roblox_username = user_info['username']
    
    # Get discord_id from state
    import asyncio
    pending = asyncio.run(db.get_pending_verification(state))
    
    if not pending:
        return "Verification session expired", 400
    
    discord_id, guild_id = pending
    
    # Save to database
    asyncio.run(db.verify_user(discord_id, roblox_id, roblox_username, guild_id))
    asyncio.run(db.remove_pending_verification(discord_id))
    
    return """
    <html>
        <head>
            <style>
                body { background: #0a0a0a; color: #00ffff; font-family: Arial; text-align: center; padding-top: 100px; }
                h1 { font-size: 48px; margin-bottom: 20px; }
                p { font-size: 18px; color: #ccc; }
                .success { color: #00ff00; font-size: 72px; }
            </style>
        </head>
        <body>
            <div class="success">✓</div>
            <h1>Verification Successful!</h1>
            <p>Your Roblox account (@""" + roblox_username + """) has been linked.</p>
            <p>Return to Discord and use <code>!verify_me</code> again to get your role.</p>
            <p><small>(Or an admin can run /check on you)</small></p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "ok"}

def run_web_server():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    run_web_server()