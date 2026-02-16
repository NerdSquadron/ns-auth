from flask import Flask, request, redirect, render_template, session, flash
from database import db
from utils.roblox_api import roblox_api
from config import config
import os
import asyncio
import sqlite3

app = Flask(__name__, 
    template_folder='dashboard/templates',
    static_folder='dashboard/static'
)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# Initialize DB on startup
def init_db():
    try:
        # Run async init in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db.init())
        loop.close()
    except Exception as e:
        print(f"DB Init error (may already exist): {e}")

init_db()

@app.route('/')
def home():
    if 'logged_in' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/dashboard')
        flash('Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'logged_in' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        try:
            blacklisted_groups_raw = request.form.get('blacklisted_groups', '').strip()
            blacklisted_groups = []
            if blacklisted_groups_raw:
                blacklisted_groups = [int(x.strip()) for x in blacklisted_groups_raw.split(',') if x.strip().isdigit()]
            
            db.save_guild_settings(guild_id=0, blacklisted_groups=blacklisted_groups)
            flash('Blacklisted groups updated!', 'success')
        except Exception as e:
            flash(f'Error saving: {str(e)}', 'error')
        
        return redirect('/dashboard')
    
    try:
        guild_settings = db.get_guild_settings(0)
        blacklisted_groups = guild_settings.get('blacklisted_groups', [])
    except Exception as e:
        flash(f'Error loading settings: {str(e)}', 'error')
        blacklisted_groups = []
    
    return render_template('dashboard.html', 
                         blacklisted_groups=blacklisted_groups)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        return "Invalid request", 400
    
    client_id = config.ROBLOX_CLIENT_ID
    client_secret = config.ROBLOX_CLIENT_SECRET
    redirect_uri = config.ROBLOX_REDIRECT_URI
    
    if not all([client_id, client_secret, redirect_uri]):
        return "Bot not configured", 500
    
    token_info = roblox_api.exchange_code_for_token(code, client_id, client_secret, redirect_uri)
    
    if not token_info:
        return "Authentication failed", 400
    
    access_token = token_info['access_token']
    user_info = roblox_api.get_user_info_from_token(access_token)
    
    if not user_info:
        return "Failed to get user info", 400
    
    roblox_id = user_info['roblox_id']
    roblox_username = user_info['username']
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    pending = loop.run_until_complete(db.get_pending_verification(state))
    
    if not pending:
        loop.close()
        return "Verification session expired", 400
    
    discord_id, guild_id = pending
    
    loop.run_until_complete(db.verify_user(discord_id, roblox_id, roblox_username, guild_id))
    loop.run_until_complete(db.remove_pending_verification(discord_id))
    loop.close()
    
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