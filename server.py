from datetime import datetime, timedelta, timezone

import pandas as pd
from fastmcp import FastMCP

from strava_api import StravaClient

mcp = FastMCP(
    "Strava",
    instructions=(
        "Access the user's Strava running and fitness data. "
        "Use get_recent_activities for an overview, "
        "get_activity_details for a deep dive on a specific run, "
        "get_weekly_summary for training trends."
    ),
)

client = StravaClient()


def _format_distance(meters):
    miles = meters / 1609.34
    return f"{miles:.1f} mi"


def _format_pace(meters, seconds):
    if meters == 0:
        return "N/A"
    pace_secs = seconds / (meters / 1609.34)
    mins = int(pace_secs // 60)
    secs = int(pace_secs % 60)
    return f"{mins}:{secs:02d}/mi"


def _format_time(seconds):
    if seconds >= 3600:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h}:{m:02d}:{s:02d}"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


def _format_date(iso_str):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.strftime("%b %d, %Y")


def _format_date_short(iso_str):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.strftime("%b %d")


@mcp.tool
def get_athlete_profile() -> str:
    """Get the athlete's Strava profile including weight and location."""
    a = client.get_athlete()
    stats = client.get_athlete_stats(a["id"])
    recent = stats.get("recent_run_totals", {})
    all_time = stats.get("all_run_totals", {})
    return (
        f"Athlete: {a['firstname']} {a['lastname']}\n"
        f"Location: {a.get('city', '?')}, {a.get('state', '?')}\n"
        f"Weight: {a.get('weight', 0):.1f} kg ({a.get('weight', 0) * 2.205:.0f} lbs)\n"
        f"Premium: {a.get('premium', False)}\n\n"
        f"Recent runs (4 weeks): {recent.get('count', 0)} runs, "
        f"{_format_distance(recent.get('distance', 0))}, "
        f"{_format_time(recent.get('moving_time', 0))}\n"
        f"All-time runs: {all_time.get('count', 0)} runs, "
        f"{_format_distance(all_time.get('distance', 0))}"
    )


@mcp.tool
def get_recent_activities(count: int = 10) -> str:
    """Get recent Strava activities with distance, time, pace, and heart rate."""
    activities = client.get_activities(per_page=count)
    if not activities:
        return "No recent activities found."
    lines = []
    for a in activities:
        hr = a.get("average_heartrate")
        hr_str = f" | HR {hr:.0f}" if hr else ""
        lines.append(
            f"{_format_date_short(a['start_date_local'])} | "
            f"{a['name']} | "
            f"{_format_distance(a['distance'])} | "
            f"{_format_time(a['moving_time'])} | "
            f"Pace {_format_pace(a['distance'], a['moving_time'], a.get('type', 'Run'))}"
            f"{hr_str} | "
            f"{a['type']} | ID: {a['id']}"
        )
    return "\n".join(lines)


@mcp.tool
def search_activities(
    activity_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_distance_miles: float | None = None,
    keyword: str | None = None,
    limit: int = 15,
) -> str:
    """Search and filter activities by type (Run, Ride), date (YYYY-MM-DD), distance, or title keyword."""
    kwargs = {}
    if start_date:
        kwargs["after"] = int(
            datetime.strptime(start_date, "%Y-%m-%d")
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
    if end_date:
        kwargs["before"] = int(
            datetime.strptime(end_date, "%Y-%m-%d")
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )

    activities = client.get_activities(per_page=200, **kwargs)
    if not activities:
        return "No activities found in that range."

    df = pd.DataFrame(activities)

    # Apply filters
    if activity_type:
        df = df[df["type"].str.lower() == activity_type.lower()]
    if min_distance_miles:
        df = df[df["distance"] >= (min_distance_miles * 1609.34)]
    if keyword:
        df = df[df["name"].str.contains(keyword, case=False, na=False)]

    if df.empty:
        return "No activities matched the filters."

    # Format output
    df = df.head(limit)
    lines = ["Filtered Activities Found:\n"]
    for _, a in df.iterrows():
        hr = a.get("average_heartrate")
        hr_str = f" | HR {hr:.0f}" if pd.notna(hr) else ""
        lines.append(
            f"{_format_date_short(a['start_date_local'])} | "
            f"{a['name']} | "
            f"{_format_distance(a['distance'])} | "
            f"{_format_time(a['moving_time'])}"
            f"{hr_str} | "
            f"{a['type']} | ID: {a['id']}"
        )
    return "\n".join(lines)


@mcp.tool
def get_activity_details(activity_id: int) -> str:
    """Get full details for a specific activity including splits and HR zones."""
    a = client.get_activity(activity_id)
    lines = [
        f"Name: {a['name']}",
        f"Date: {_format_date(a['start_date_local'])}",
        f"Type: {a['type']}",
        f"Distance: {_format_distance(a['distance'])}",
        f"Moving Time: {_format_time(a['moving_time'])}",
        f"Elapsed Time: {_format_time(a['elapsed_time'])}",
        f"Pace: {_format_pace(a['distance'], a['moving_time'], a.get('type', 'Run'))}",
        f"Elevation Gain: {a.get('total_elevation_gain', 0):.0f} m ({a.get('total_elevation_gain', 0) * 3.281:.0f} ft)",
        f"Calories: {a.get('calories', 'N/A')}",
    ]
    if a.get("average_heartrate"):
        lines.append(f"Avg HR: {a['average_heartrate']:.0f} bpm")
        lines.append(f"Max HR: {a.get('max_heartrate', 'N/A')} bpm")
    if a.get("average_cadence"):
        lines.append(f"Avg Cadence: {a['average_cadence'] * 2:.0f} spm")
    if a.get("gear_id"):
        lines.append(f"Gear ID: {a['gear_id']}")
    if a.get("description"):
        lines.append(f"Description: {a['description']}")

    # Splits
    splits = a.get("splits_standard", [])
    if splits:
        lines.append("\nMile Splits:")
        for i, s in enumerate(splits, 1):
            split_pace = _format_pace(
                s["distance"], s["moving_time"], a.get("type", "Run")
            )
            hr = (
                f" | HR {s['average_heartrate']:.0f}"
                if s.get("average_heartrate")
                else ""
            )
            lines.append(f"  Mile {i}: {split_pace}{hr}")

    return "\n".join(lines)


@mcp.tool
def get_activity_streams(
    activity_id: int,
    keys: str = "heartrate,time,distance,altitude",
    downsample_sec: int = 60,
) -> str:
    """Get time-series data for an activity. Uses downsample_sec (default 60s) to reduce LLM token usage while preserving shape."""
    streams = client.get_activity_streams(activity_id, keys)
    if not streams or "time" not in streams:
        return "No stream data available for this activity."

    df = pd.DataFrame({"time": streams["time"]["data"]})
    for k in keys.split(","):
        if k in streams and k != "time":
            df[k] = streams[k]["data"]

    if df.empty:
        return "No data."

    # Group by downsample_sec chunks
    df["time_bin"] = (df["time"] // downsample_sec) * downsample_sec
    agg_dict = {}
    if "heartrate" in df.columns:
        agg_dict["heartrate"] = "mean"
    if "altitude" in df.columns:
        agg_dict["altitude"] = "mean"
    if "distance" in df.columns:
        agg_dict["distance"] = "max"

    downsampled = df.groupby("time_bin").agg(agg_dict).reset_index()

    lines = [
        f"Stream data for activity {activity_id} (Downsampled to {downsample_sec}s bins to save tokens):\n"
    ]
    lines.append(downsampled.to_markdown(index=False))
    return "\n".join(lines)


@mcp.tool
def get_athlete_stats() -> str:
    """Get all-time and recent running stats."""
    athlete = client.get_athlete()
    stats = client.get_athlete_stats(athlete["id"])
    sections = []
    for label, key in [
        ("Recent (4 weeks)", "recent_run_totals"),
        ("Year to Date", "ytd_run_totals"),
        ("All Time", "all_run_totals"),
    ]:
        s = stats.get(key, {})
        sections.append(
            f"{label}:\n"
            f"  Runs: {s.get('count', 0)}\n"
            f"  Distance: {_format_distance(s.get('distance', 0))}\n"
            f"  Time: {_format_time(s.get('moving_time', 0))}\n"
            f"  Elevation: {s.get('elevation_gain', 0):.0f} m"
        )
    return "\n\n".join(sections)


@mcp.tool
def get_weekly_summary(weeks_back: int = 4, activity_type: str = "Run") -> str:
    """Get weekly mileage, run count, and average pace for recent weeks."""
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks_back)
    epoch = int(cutoff.timestamp())
    activities = client.get_activities(per_page=100, after=epoch)
    runs = [a for a in activities if a["type"].lower() == activity_type.lower()]
    if not runs:
        return f"No {activity_type}s in the last {weeks_back} weeks."

    weeks = {}
    for r in runs:
        dt = datetime.fromisoformat(r["start_date_local"].replace("Z", "+00:00"))
        week_start = dt - timedelta(days=dt.weekday())
        week_key = week_start.strftime("%b %d")
        if week_key not in weeks:
            weeks[week_key] = {"count": 0, "distance": 0, "time": 0}
        weeks[week_key]["count"] += 1
        weeks[week_key]["distance"] += r["distance"]
        weeks[week_key]["time"] += r["moving_time"]

    lines = [f"Weekly {activity_type} summary (last {weeks_back} weeks):\n"]
    for week, data in sorted(weeks.items(), reverse=True):
        pace = _format_pace(data["distance"], data["time"], activity_type)
        lines.append(
            f"Week of {week}: {data['count']} runs, "
            f"{_format_distance(data['distance'])}, "
            f"avg pace {pace}"
        )
    return "\n".join(lines)


@mcp.tool
def get_gear_stats() -> str:
    """Get shoe/gear mileage — useful for knowing when to replace shoes."""
    activities = client.get_activities(per_page=50)
    gear_ids = set()
    for a in activities:
        if a.get("gear_id"):
            gear_ids.add(a["gear_id"])
    if not gear_ids:
        return "No gear found in recent activities."
    lines = ["Gear stats:\n"]
    for gid in gear_ids:
        g = client.get_gear(gid)
        dist = _format_distance(g.get("distance", 0))
        lines.append(
            f"{g['name']}: {dist} total ({g.get('brand_name', '')} {g.get('model_name', '')})"
        )
    return "\n".join(lines)


@mcp.tool
def analyze_activity_zones_pandas(activity_id: int) -> str:
    """Use Pandas to analyze an activity's data streams and calculate heart rate zones and rolling pace metrics."""
    streams = client.get_activity_streams(
        activity_id, "heartrate,time,distance,altitude"
    )
    if not streams or "time" not in streams:
        return "Insufficient stream data for pandas analysis."

    # Convert streams to a Pandas DataFrame
    df = pd.DataFrame(
        {
            "time": streams.get("time", {}).get("data", []),
        }
    )
    if "heartrate" in streams:
        df["hr"] = streams["heartrate"]["data"]
    if "distance" in streams:
        df["distance"] = streams["distance"]["data"]

    if df.empty:
        return "No data to analyze."

    lines = [f"Pandas Data Science Analysis for Activity {activity_id}:"]

    if "hr" in df.columns:
        # Calculate time in basic HR zones
        df["hr_zone"] = pd.cut(
            df["hr"],
            bins=[0, 130, 150, 170, 190, 250],
            labels=[
                "Zone 1 (Recovery)",
                "Zone 2 (Aerobic)",
                "Zone 3 (Tempo)",
                "Zone 4 (Threshold)",
                "Zone 5 (Anaerobic)",
            ],
        )
        zone_counts = df["hr_zone"].value_counts(sort=False)
        lines.append("\nHeart Rate Zone Distribution (Seconds):")
        for zone, count in zone_counts.items():
            if count > 0:
                lines.append(f"  {zone}: {count} seconds")

        # 1-minute rolling average max HR
        rolling_hr = df["hr"].rolling(window=60).mean()
        lines.append(f"\nPeak 1-Minute Rolling HR: {rolling_hr.max():.1f} bpm")

    if "distance" in df.columns:
        # Calculate rolling 1-minute pace (distance difference over 60 seconds)
        df["dist_diff"] = df["distance"].diff(periods=60)
        # Pace in seconds per mile: 60 seconds / (dist_diff / 1609.34)
        df["rolling_pace_sec_per_mi"] = 60 / (df["dist_diff"] / 1609.34)
        best_rolling_pace = df["rolling_pace_sec_per_mi"].min()
        act = client.get_activity(activity_id)
        if pd.notna(best_rolling_pace) and best_rolling_pace > 0:
            lines.append(
                f"Best 1-Minute Rolling Pace: {_format_pace(1609.34, best_rolling_pace, act.get('type', 'Run'))}"
            )

    if "hr" in df.columns and "distance" in df.columns and len(df) > 120:
        # Cardiac Drift (Aerobic Decoupling)
        # Split run into first half and second half by time
        midpoint = len(df) // 2
        half1 = df.iloc[:midpoint].copy()
        half2 = df.iloc[midpoint:].copy()

        # Filter out zeroes or non-moving time if possible, but for simplicity:
        h1_dist = half1["distance"].max() - half1["distance"].min()
        h2_dist = half2["distance"].max() - half2["distance"].min()

        h1_time = half1["time"].max() - half1["time"].min()
        h2_time = half2["time"].max() - half2["time"].min()

        if h1_dist > 0 and h2_dist > 0:
            h1_pace = h1_time / (h1_dist / 1609.34)
            h2_pace = h2_time / (h2_dist / 1609.34)

            h1_hr = half1["hr"].mean()
            h2_hr = half2["hr"].mean()

            # Ratio of HR to Pace
            ratio1 = h1_hr / h1_pace
            ratio2 = h2_hr / h2_pace

            if ratio1 > 0:
                drift = ((ratio2 - ratio1) / ratio1) * 100
                lines.append(f"\nCardiac Drift (Aerobic Decoupling): {drift:.1f}%")
                if drift > 5.0:
                    lines.append(
                        "  (>5% indicates significant fatigue, dehydration, or heat stress)"
                    )
                else:
                    lines.append(
                        "  (<5% indicates excellent aerobic endurance and pacing)"
                    )

    return "\n".join(lines)


@mcp.tool
def get_daily_briefing(activity_type: str = "Run") -> str:
    """Get a daily Strava briefing (yesterday's workouts, today's workouts, and week-to-date mileage) for ambient agent routines."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    activities = client.get_activities(per_page=50, after=int(cutoff.timestamp()))

    if not activities:
        return "No activities in the last two weeks. Rest mode!"

    df = pd.DataFrame(activities)
    df["date"] = pd.to_datetime(df["start_date_local"]).dt.date

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    lines = ["🏃 **Strava Daily Briefing**\n"]

    # Yesterday
    yest_df = df[df["date"] == yesterday]
    if yest_df.empty:
        lines.append("- **Yesterday:** Rest day (No activities recorded).")
    else:
        names = yest_df["name"].tolist()
        dists = [_format_distance(d) for d in yest_df["distance"]]
        lines.append(f"- **Yesterday:** {len(yest_df)} activity/activities recorded.")
        for n, d in zip(names, dists):
            lines.append(f"  - {n} ({d})")

    # Today
    today_df = df[df["date"] == today]
    if not today_df.empty:
        lines.append(f"\n- **Today so far:** {len(today_df)} activities.")
        for _, a in today_df.iterrows():
            lines.append(f"  - {a['name']} ({_format_distance(a['distance'])})")

    # Weekly progress (Monday to Sunday)
    monday = today - timedelta(days=today.weekday())
    this_week_df = df[
        (df["date"] >= monday) & (df["type"].str.lower() == activity_type.lower())
    ]
    this_week_dist = this_week_df["distance"].sum() if not this_week_df.empty else 0

    lines.append(
        f"\n- **Week-to-Date ({activity_type}):** {_format_distance(this_week_dist)}"
    )

    return "\n".join(lines)


@mcp.tool
def get_training_trends(activity_type: str = "Run") -> str:
    """Analyzes the last 12 weeks of data to determine if the user is in a build, maintain, or taper phase."""
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=12)
    activities = client.get_activities(per_page=200, after=int(cutoff.timestamp()))

    df = pd.DataFrame(
        [a for a in activities if a["type"].lower() == activity_type.lower()]
    )
    if df.empty:
        return f"Not enough {activity_type} data to calculate trends."

    df["date"] = pd.to_datetime(df["start_date_local"])
    df.set_index("date", inplace=True)

    # Resample to weekly distance
    weekly = df["distance"].resample("W").sum() / 1609.34  # miles

    if len(weekly) < 4:
        return "Need at least 4 weeks of data to establish a trend."

    recent_4_wks = weekly.iloc[-4:].mean()
    prev_4_wks = weekly.iloc[-8:-4].mean() if len(weekly) >= 8 else None

    lines = ["📈 **Training Trend Analysis**\n"]
    lines.append(f"- **Recent 4-Week Average:** {recent_4_wks:.1f} mi/week")

    if prev_4_wks and prev_4_wks > 0:
        lines.append(f"- **Previous 4-Week Average:** {prev_4_wks:.1f} mi/week")
        diff = ((recent_4_wks - prev_4_wks) / prev_4_wks) * 100
        if diff > 10:
            lines.append(
                f"- **Phase:** 🔴 Build Phase (+{diff:.1f}% volume increase). Watch for overtraining."
            )
        elif diff < -10:
            lines.append(
                f"- **Phase:** 🟢 Recovery/Taper Phase ({diff:.1f}% volume decrease)."
            )
        else:
            lines.append("- **Phase:** 🟡 Maintenance Phase (Steady volume).")

    return "\n".join(lines)


@mcp.tool
def get_starred_segments() -> str:
    """Get the authenticated athlete's starred segments."""
    segments = client.get_starred_segments()
    if not segments:
        return "No starred segments found."
    lines = ["Starred Segments:\n"]
    for s in segments:
        lines.append(
            f"- {s['name']} (ID: {s['id']}) | {_format_distance(s['distance'])} | {s.get('city', '')}, {s.get('state', '')}"
        )
    return "\n".join(lines)


@mcp.tool
def explore_segments(bounds: str, activity_type: str = "running") -> str:
    """Explore segments in a specific rectangular area. Bounds must be comma separated: sw_lat,sw_lng,ne_lat,ne_lng. activity_type can be 'running' or 'riding'."""
    try:
        data = client.explore_segments(bounds, activity_type)
        segments = data.get("segments", [])
        if not segments:
            return "No segments found in this area."
        lines = [f"Segments found ({activity_type}):\n"]
        for s in segments:
            lines.append(
                f"- {s['name']} (ID: {s['id']}) | Cat: {s.get('climb_category', 0)}"
            )
        return "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return f"Error exploring segments: {e!s}"


@mcp.tool
def get_athlete_routes() -> str:
    """Get the authenticated athlete's saved routes."""
    athlete = client.get_athlete()
    routes = client.get_routes(athlete["id"])
    if not routes:
        return "No saved routes found."
    lines = ["Saved Routes:\n"]
    for r in routes:
        lines.append(
            f"- {r['name']} (ID: {r['id']}) | {_format_distance(r['distance'])} | Elev Gain: {r.get('elevation_gain', 0):.0f}m"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
