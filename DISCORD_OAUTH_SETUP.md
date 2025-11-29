# Discord OAuth Setup for Dashboard

## 1. Create Discord OAuth Application

1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Name it "XP Bot Dashboard" (or your preferred name)
4. Click "Create"

## 2. Configure OAuth2

1. In your application, go to "OAuth2" in the left sidebar
2. Click "Add Redirect" under "Redirects"
3. Add your redirect URIs:
   - **Local Development:** `http://localhost:5001/callback`
   - **Production:** `https://your-dashboard-domain.com/callback`
4. Click "Save Changes"

## 3. Get Your Credentials

1. Still in the OAuth2 section, copy your:
   - **Client ID** - shown at the top
   - **Client Secret** - click "Reset Secret" if you need a new one, then copy it

## 4. Configure Environment Variables

Add these to your `.env` file or environment:

```bash
# Discord OAuth for Dashboard
DISCORD_CLIENT_ID=your_client_id_here
DISCORD_CLIENT_SECRET=your_client_secret_here
DISCORD_REDIRECT_URI=http://localhost:5001/callback  # Change for production

# Existing variables
GUILD_ID=your_guild_id_here
FLASK_SECRET_KEY=generate_a_random_secret_key  # Optional, auto-generates if not set
```

## 5. Test Locally

1. Restart the dashboard: `docker-compose restart dashboard`
2. Visit http://localhost:5001
3. You should be redirected to Discord login
4. After logging in, you'll be redirected back to the dashboard
5. You must:
   - Be a member of the Discord server (GUILD_ID)
   - Have an Admin role OR a DM role (character creation role)

## 6. Production Setup

For Fly.io deployment:

```bash
# Set secrets
flyctl secrets set DISCORD_CLIENT_ID="your_client_id" -a your-dashboard-app-name
flyctl secrets set DISCORD_CLIENT_SECRET="your_client_secret" -a your-dashboard-app-name
flyctl secrets set DISCORD_REDIRECT_URI="https://your-dashboard.fly.dev/callback" -a your-dashboard-app-name
flyctl secrets set FLASK_SECRET_KEY="$(openssl rand -hex 32)" -a your-dashboard-app-name

# Deploy
flyctl deploy -a your-dashboard-app-name
```

## Required Scopes

The dashboard requests these OAuth2 scopes:
- `identify` - To get user information
- `guilds.members.read` - To check guild membership and roles

## Access Control

Users can access the dashboard if they:
1. Are members of your Discord server (GUILD_ID)
2. Have EITHER:
   - Administrator permission in the server, OR
   - A "DM role" (any role configured as a character creation role in the bot)

## Troubleshooting

**"Access Denied - Not a member"**
- User is not in the Discord server specified by GUILD_ID

**"Access Denied - Need Admin or DM role"**
- User doesn't have administrator permission
- User doesn't have any of the character creation roles
- Make sure you've configured character creation roles with `/xp_set_character_creation_roles`

**"Failed to get access token"**
- Check that DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET are correct
- Check that redirect URI in Discord app matches DISCORD_REDIRECT_URI

**"Failed to get user info"**
- OAuth token exchange succeeded but getting user data failed
- This is usually a temporary Discord API issue - try again
