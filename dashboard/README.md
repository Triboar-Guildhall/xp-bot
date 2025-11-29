# XP Bot Quest Dashboard

A web-based visualization dashboard for viewing quests, participants, DMs, and statistics from the XP Bot Discord bot.

## Features

- **Statistics Dashboard**: Overview of quest statistics, participant counts, and DM activity
- **Quest List**: Searchable and filterable list of all quests
- **Quest Details**: Detailed view of individual quests with participants, DMs, and encounters
- **Charts & Graphs**: Visual representation of quest distribution by level bracket
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Backend**: Flask (Python web framework)
- **Database**: PostgreSQL (shared with Discord bot)
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Charts**: Chart.js

## Setup

### Local Development

1. **Install dependencies**:
   ```bash
   cd web-dashboard
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and set your DATABASE_URL
   ```

3. **Run the development server**:
   ```bash
   python app.py
   ```

4. **Open in browser**:
   Navigate to `http://localhost:5000`

### Production Deployment on Fly.io

1. **Create a new Fly.io app**:
   ```bash
   fly apps create xp-bot-dashboard
   ```

2. **Attach to the same database** as your bot:
   ```bash
   fly postgres attach xp-bot-db --app xp-bot-dashboard
   ```

3. **Create a `Dockerfile`** (see below)

4. **Deploy**:
   ```bash
   fly deploy
   ```

5. **Open the dashboard**:
   ```bash
   fly open
   ```

### Sample Dockerfile for Production

Create a `Dockerfile` in the `web-dashboard` directory:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Set environment
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]
```

### Sample fly.toml for Production

Create a `fly.toml` in the `web-dashboard` directory:

```toml
app = 'xp-bot-dashboard'
primary_region = 'ord'

[build]
  dockerfile = "Dockerfile"

[env]
  ENV = "prod"
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = '256mb'
  cpu_kind = 'shared'
  cpus = 1
```

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (automatically set by Fly.io when you attach the database)
- `ENV`: Set to `dev` for development or `prod` for production
- `PORT`: Port to run the server on (default: 5000)

## API Endpoints

The dashboard also provides JSON API endpoints:

- `GET /api/stats` - Overall quest statistics
- `GET /api/quests?status=active&level_bracket=3-4` - Quest list with filters
- `GET /api/quest/<id>` - Individual quest details

## Pages

### Dashboard (/)
- Overview statistics
- Quest distribution chart
- Top DMs table
- Quick links

### Quest List (/quests)
- Filterable table of all quests
- Filter by status (active/completed)
- Filter by level bracket
- View quest details

### Quest Detail (/quest/<id>)
- Quest information
- Participant list with starting levels
- DM list
- Encounters and monsters

## Database Schema

This dashboard reads from the following tables created by the bot:

- `quests` - Main quest information
- `quest_participants` - PCs in each quest
- `quest_dms` - DMs for each quest
- `quest_monsters` - Encounters/monsters in quests
- `characters` - Character names and info

## Development

### Project Structure

```
web-dashboard/
├── app.py              # Main Flask application
├── db.py               # Database layer
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── quests.html
│   └── quest_detail.html
└── static/             # Static assets
    ├── css/
    │   └── style.css
    └── js/
```

### Adding New Features

1. Add database queries to `db.py`
2. Add routes to `app.py`
3. Create templates in `templates/`
4. Add styles to `static/css/style.css`

## Troubleshooting

**Dashboard not connecting to database**:
- Verify `DATABASE_URL` is set correctly in `.env`
- Ensure you can connect to the database directly
- Check that the database contains the required tables

**No data showing**:
- Verify quests exist in the database
- Check browser console for JavaScript errors
- Ensure the bot has created quests using `/quest_start`

**Charts not rendering**:
- Verify Chart.js is loading (check browser console)
- Ensure there is data to display

## License

Same as XP Bot (AGPL-3.0)
