from flask import Flask, request, redirect, render_template, session, flash
from functools import wraps
from database import db
from utils.roblox_api import roblox_api
from config import config
import os

app = Flask(__name__, 
    template_folder='dashboard/templates',
    static_folder='dashboard/static'
)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# Simple auth - password set via env or default
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return "AuthChecker Bot is running!"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    creds = db.get_credentials()
    return render_template('dashboard.html', creds=creds, config=config)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        discord_token = request.form.get('discord_token', '').strip()
        roblox_client_id = request.form.get('roblox_client_id', '').strip()
        roblox_client_secret = request.form.get('roblox_client_secret', '').strip()
        roblox_redirect_uri = request.form.get('roblox_redirect_uri', '').strip()
        
        blacklisted_groups_raw = request.form.get('blacklisted_groups', '').strip()
        blacklisted_groups = []
        if blacklisted_groups_raw:
            blacklisted_groups = [int(x.strip()) for x in blacklisted_groups_raw.split(',') if x.strip().isdigit()]
        
        if discord_token:
            db.save_credentials(discord_token, roblox_client_id, roblox_client_secret, roblox_redirect_uri)
            db.save_guild_settings(guild_id=0, blacklisted_groups=blacklisted_groups)
            flash('Settings saved successfully!', 'success')
        else:
            flash('Discord Token is required!', 'error')
        
        return redirect(url_for('settings'))
    
    creds = db.get_credentials()
    guild_settings = db.get_guild_settings(0)
    
    return render_template('settings.html',
                         creds=creds,
                         blacklisted_groups=guild_settings.get('blacklisted_groups', []))

@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        return "Invalid request", 400
    
    # Get credentials from database, fall back to environment variables
    creds = db.get_credentials()
    client_id = creds.get('roblox_client_id') or config.ROBLOX_CLIENT_ID
    client_secret = creds.get('roblox_client_secret') or config.ROBLOX_CLIENT_SECRET
    redirect_uri = creds.get('roblox_redirect_uri') or config.ROBLOX_REDIRECT_URI
    
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