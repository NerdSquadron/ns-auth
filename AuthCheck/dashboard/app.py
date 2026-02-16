from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from database import db
from config import config
import os
import secrets

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Simple auth - password set via env or default
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/')
@login_required
def dashboard():
    # Get current settings
    creds = db.get_credentials()
    
    # Get first guild settings or defaults
    all_settings = []
    # Note: In production, you'd iterate through guilds properly
    
    return render_template('dashboard.html', 
                         creds=creds,
                         config=config)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Save Discord Bot Token
        discord_token = request.form.get('discord_token', '').strip()
        
        # Save Roblox OAuth
        roblox_client_id = request.form.get('roblox_client_id', '').strip()
        roblox_client_secret = request.form.get('roblox_client_secret', '').strip()
        roblox_redirect_uri = request.form.get('roblox_redirect_uri', '').strip()
        
        # Save blacklisted groups
        blacklisted_groups_raw = request.form.get('blacklisted_groups', '').strip()
        blacklisted_groups = []
        if blacklisted_groups_raw:
            # Parse comma-separated group IDs
            blacklisted_groups = [int(x.strip()) for x in blacklisted_groups_raw.split(',') if x.strip().isdigit()]
        
        # Save to database
        if discord_token:
            db.save_credentials(discord_token, roblox_client_id, roblox_client_secret, roblox_redirect_uri)
            
            # Save blacklisted groups to default guild (ID 0 or first guild)
            db.save_guild_settings(
                guild_id=0,  # Default/global
                blacklisted_groups=blacklisted_groups
            )
            
            flash('Settings saved successfully!', 'success')
        else:
            flash('Discord Token is required!', 'error')
        
        return redirect(url_for('settings'))
    
    # Get current settings
    creds = db.get_credentials()
    guild_settings = db.get_guild_settings(0)
    
    return render_template('settings.html',
                         creds=creds,
                         blacklisted_groups=guild_settings.get('blacklisted_groups', []))

@app.route('/health')
def health():
    return {"status": "ok", "service": "authchecker-dashboard"}

if __name__ == '__main__':
    # Initialize database
    import asyncio
    asyncio.run(db.init())
    
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)