"""
XP Bot Quest Dashboard
Flask web application for visualizing quests, participants, and DMs
"""
import os
import asyncio
import secrets
import requests
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, render_template_string
from db import Database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
db = Database()

# Discord OAuth configuration
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:5001/callback')
GUILD_ID = os.getenv('GUILD_ID')
DISCORD_API_ENDPOINT = 'https://discord.com/api/v10'

# Global event loop for async operations
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


# CR to XP conversion table (D&D 5e)
CR_TO_XP = {
    '0': 10,
    '1/8': 25,
    '1/4': 50,
    '1/2': 100,
    '1': 200,
    '2': 450,
    '3': 700,
    '4': 1100,
    '5': 1800,
    '6': 2300,
    '7': 2900,
    '8': 3900,
    '9': 5000,
    '10': 5900,
    '11': 7200,
    '12': 8400,
    '13': 10000,
    '14': 11500,
    '15': 13000,
    '16': 15000,
    '17': 18000,
    '18': 20000,
    '19': 22000,
    '20': 25000,
    '21': 33000,
    '22': 41000,
    '23': 50000,
    '24': 62000,
    '25': 75000,
    '26': 90000,
    '27': 105000,
    '28': 120000,
    '29': 135000,
    '30': 155000,
}


def cr_to_xp(cr):
    """Convert CR to XP value"""
    return CR_TO_XP.get(str(cr), 0)


# Register template filter
app.jinja_env.filters['cr_to_xp'] = cr_to_xp


def run_async(coro):
    """Helper to run async functions in Flask routes"""
    return loop.run_until_complete(coro)


# Discord OAuth helper functions
def get_user_guild_member(access_token, user_id):
    """Get user's guild membership"""
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(
        f'{DISCORD_API_ENDPOINT}/users/@me/guilds/{GUILD_ID}/member',
        headers=headers
    )
    if response.status_code == 200:
        return response.json()
    return None


def has_required_role(member_data, db_sync):
    """Check if user has admin or DM role"""
    if not member_data:
        return False

    user_roles = member_data.get('roles', [])

    # Get DM roles from database (character creation roles)
    try:
        dm_role_ids = run_async(db_sync.get_character_creation_roles(int(GUILD_ID)))

        # Check if user has any DM role
        if any(role_id in dm_role_ids for role_id in [int(r) for r in user_roles]):
            return True
    except:
        pass

    # Check for administrator permission
    permissions = int(member_data.get('permissions', 0))
    has_admin = (permissions & 0x8) == 0x8  # Administrator permission

    return has_admin


def require_auth(f):
    """Decorator to require Discord authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_request():
    """Ensure database is connected"""
    if db.pool is None:
        run_async(db.connect())


# Authentication routes
@app.route('/login')
def login():
    """Redirect to Discord OAuth"""
    discord_login_url = (
        f'https://discord.com/api/oauth2/authorize'
        f'?client_id={DISCORD_CLIENT_ID}'
        f'&redirect_uri={DISCORD_REDIRECT_URI}'
        f'&response_type=code'
        f'&scope=identify guilds.members.read'
    )
    return redirect(discord_login_url)


@app.route('/callback')
def callback():
    """Handle Discord OAuth callback"""
    code = request.args.get('code')
    if not code:
        return "Error: No code provided", 400

    # Exchange code for access token
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(f'{DISCORD_API_ENDPOINT}/oauth2/token', data=data, headers=headers)

    if response.status_code != 200:
        return "Error: Failed to get access token", 400

    token_data = response.json()
    access_token = token_data['access_token']

    # Get user info
    headers = {'Authorization': f'Bearer {access_token}'}
    user_response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me', headers=headers)

    if user_response.status_code != 200:
        return "Error: Failed to get user info", 400

    user_data = user_response.json()
    user_id = user_data['id']

    # Check guild membership and roles
    member_data = get_user_guild_member(access_token, user_id)

    if not member_data:
        return render_template_string('''
            <h1>Access Denied</h1>
            <p>You must be a member of the Discord server to access this dashboard.</p>
            <a href="/">Go back</a>
        '''), 403

    if not has_required_role(member_data, db):
        return render_template_string('''
            <h1>Access Denied</h1>
            <p>You need to have an Admin or DM role to access this dashboard.</p>
            <a href="/">Go back</a>
        '''), 403

    # Store user in session
    session['user'] = {
        'id': user_id,
        'username': user_data['username'],
        'discriminator': user_data.get('discriminator', '0'),
        'avatar': user_data.get('avatar')
    }

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Log out user"""
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/')
@require_auth
def index():
    """Home page with statistics dashboard"""
    stats = run_async(db.get_quest_stats())
    dm_stats = run_async(db.get_dm_stats())
    level_brackets = run_async(db.get_level_brackets())

    return render_template('index.html',
                         stats=stats,
                         dm_stats=dm_stats,
                         level_brackets=level_brackets)


@app.route('/quests')
@require_auth
def quests():
    """Quest list page with filters"""
    # Get filter parameters
    status = request.args.get('status', None)
    level_bracket = request.args.get('level_bracket', None)
    limit = int(request.args.get('limit', 100))

    # Get data
    quests_list = run_async(db.get_all_quests(status, level_bracket, limit))
    level_brackets = run_async(db.get_level_brackets())
    quest_types = run_async(db.get_quest_types())

    return render_template('quests.html',
                         quests=quests_list,
                         level_brackets=level_brackets,
                         quest_types=quest_types,
                         current_status=status,
                         current_level_bracket=level_bracket)


@app.route('/quest/<int:quest_id>')
@require_auth
def quest_detail(quest_id):
    """Individual quest detail page"""
    quest = run_async(db.get_quest_by_id(quest_id))

    if not quest:
        return "Quest not found", 404

    return render_template('quest_detail.html', quest=quest)


@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics (for charts/graphs)"""
    stats = run_async(db.get_quest_stats())
    return jsonify(stats)


@app.route('/api/quests')
def api_quests():
    """API endpoint for quest list"""
    status = request.args.get('status', None)
    level_bracket = request.args.get('level_bracket', None)
    limit = int(request.args.get('limit', 100))

    quests_list = run_async(db.get_all_quests(status, level_bracket, limit))
    return jsonify(quests_list)


@app.route('/api/quest/<int:quest_id>')
def api_quest_detail(quest_id):
    """API endpoint for quest details"""
    quest = run_async(db.get_quest_by_id(quest_id))

    if not quest:
        return jsonify({"error": "Quest not found"}), 404

    return jsonify(quest)


@app.route('/api/quest/<int:quest_id>/dm/<int:user_id>/update_name', methods=['POST'])
@require_auth
def update_dm_name(quest_id, user_id):
    """API endpoint to update a DM's name for a specific quest"""
    data = request.get_json()
    new_name = data.get('name', '').strip()

    if not new_name:
        return jsonify({"error": "Name cannot be empty"}), 400

    if len(new_name) > 255:
        return jsonify({"error": "Name must be 255 characters or less"}), 400

    try:
        run_async(db.update_quest_dm_name(quest_id, user_id, new_name))
        return jsonify({"success": True, "name": new_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Clean up resources on shutdown"""
    pass  # Connection pool will be closed on app shutdown


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('ENV', 'dev') == 'dev'

    app.run(host='0.0.0.0', port=port, debug=debug)
