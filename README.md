# 🏃 Strava MCP Server

Turn Claude (or any MCP-compatible AI) into your personal running and cycling coach. 

While most Strava integrations just fetch a basic list of your recent workouts, this server is built from the ground up for **Deep Analytics**. Powered by Python and `pandas`, it gives your AI agent the ability to analyze your heart rate zones (for running, cycling, and swimming), track your shoe mileage, detect your macro-training phases (Build vs. Taper), and even identify mid-run fatigue.

## �� Why no OAuth or Webhooks? (The Local Advantage)

This server is intentionally designed as a **Local Edge-Compute MCP**. Unlike other Strava MCPs that force you to deploy a Cloudflare Worker and route your private health data through a third-party server, this runs entirely on your own machine. By keeping it local and using a simple `.env` key, we eliminate cloud hosting complexity, ensure your data never leaves your device, and allow the server to directly leverage Python's powerful `pandas` library (which cannot run on V8 isolates like Cloudflare).

## ✂ Why use this one?

- **Multi-Sport, Python & Pandas Native:** Written in Python using `fastmcp`. It's incredibly easy to fork and extend if you want to pipe your running/cycling data into custom data science models or generate `matplotlib` graphs.
- **Deep Time-Series Streams:** Instead of just average pace, it exposes raw, second-by-second heart rate and altitude arrays so Claude can analyze exactly when you peaked on a hill.
- **Smart Filtering:** Your AI doesn't have to read 200 activities to find your last marathon. It can search and slice your history by date, distance, or keyword.
- **Ambient Agent Ready:** Includes tools specifically designed for always-on background agents (like OpenClaw) to summarize your daily training load and weekly goals without blowing up token limits.
- **Auto-Refreshing Auth:** Set it and forget it. It manages Strava OAuth token refreshing seamlessly in the background.

## 🛦 The Tools

- `search_activities` - Filter and slice activities by date, type, distance, or keywords.
- `analyze_activity_zones_pandas` - Pandas-powered breakdown of time-in-zones, cardiac drift (fatigue), and 1-minute rolling peak pace/HR.
- `get_daily_briefing` - Ideal for ambient agents: a quick summary of yesterday's workouts and current weekly progress (supports Run, Ride, etc.).
- `get_training_trends` - Analyzes the last 12 weeks of data to detect if you are in a Build, Maintain, or Recovery phase.
- `get_starred_segments` - **[NEW]** View your starred Strava segments.
- `explore_segments` - **[NEW]** Find new segments to ride or run in a specific map area.
- `get_athlete_routes` - **[NEW]** Pull your saved maps and routes.
- `get_recent_activities` - Quick overview of recent workouts(distance, pace, HR).
- `get_activity_details` - Deep dive on a specific activity, including mile splits.
- `get_activity_streams` - Raw time-series data (downsampled to save LLM tokens).
- `get_athlete_stats` - All-time and recent totals.
- `get_gear_stats` - Shoe mileage tracker to proactively warn you when it's time for new shoes.

## 🚀 Quickstart

1. Create a Strava API app at https://www.strava.com/settings/api
2. Authorize it and ensure you have the scopes: `read_all,activity:read_all,profile:read_all`
3. Clone this repository and create a `.env` file:
   ```text
   STRAVA_CLIENT_ID=your_client_id
   STRAVA_CLIENT_SECRET=your_client_secret
   STRAVA_REFRESH_TOKEN=your_refresh_token
   ```
4. Install dependencies: `uv sync`
5. Add it to Claude Code: `claude mcp add strava -- uv run server.py`
