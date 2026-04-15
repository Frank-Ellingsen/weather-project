import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =====================================================
# ICONS + WIND ARROWS
# =====================================================
ICONS = {
    # Clear / Cloud
    'sunny': '☀️',
    'clear': '☀️',
    'partly cloudy': '⛅',
    'cloudy': '☁️',
    'overcast': '🌥️',

    # Fog / Mist
    'mist': '🌫️',
    'fog': '🌫️',

    # Rain
    'patchy rain nearby': '🌦️',
    'light rain': '🌦️',
    'moderate rain': '🌧️',
    'heavy rain': '🌧️💦',
    'rain': '🌧️',
    'light drizzle': '🌦️',
    'moderate drizzle': '🌧️',

    # Snow
    'light snow': '🌨️',
    'snow': '❄️',
    'heavy snow': '❄️❄️',
    'patchy snow': '🌨️',

    # Sleet
    'sleet': '🌨️🌧️',
    'light sleet': '🌨️🌦️',
    'light sleet showers': '🌨️🌦️',
    'moderate sleet': '🌨️🌧️',
    'moderate or heavy sleet': '🌨️🌧️💦',
    'heavy sleet': '🌨️🌧️💦',

    # Freezing rain
    'light freezing rain': '🌧️🧊',
    'freezing rain': '🌧️🧊',

    # Thunder / Wind
    'thunderstorm': '⛈️',
    'windy': '🌬️'
}


def get_icon(cond):
    return ICONS.get(cond.lower(), "❓") if cond else "❓"

def wind_arrow(deg):
    arrows = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"]
    return arrows[int((deg + 222.5) // 45) % 8]

# =====================================================
# LOAD DATA
# =====================================================
conn = sqlite3.connect("weather.db")
df = pd.read_sql(
    "SELECT * FROM weather_kristiansand ORDER BY last_updated DESC LIMIT 1",
    conn,
)
conn.close()

w = df.iloc[0]

wind_mps = w.wind_kph / 3.6
icon = get_icon(w.condition_text)
arrow = wind_arrow(w.wind_degree)

# =====================================================
# WIND VECTOR
# =====================================================
rad = np.deg2rad(w.wind_degree)
x, y = -np.sin(rad), -np.cos(rad)
scale = min(wind_mps / 8, 1.3)
x *= scale
y *= scale

# =====================================================
# FIGURE
# =====================================================
fig = make_subplots(
    rows=1,
    cols=2,
    column_widths=[0.55, 0.45],
    specs=[[{"type": "domain"}, {"type": "xy"}]],
)

LEFT_X_CENTER = 0.275  # exact center of left column (0.55 / 2)

# -----------------------
# LEFT PANEL
# -----------------------

# ICON
fig.add_annotation(
    text=icon,
    x=LEFT_X_CENTER, y=0.85,
    xref="paper", yref="paper",
    font=dict(size=70),
    showarrow=False,
)



# DETAILS
details = (
    f"<b>{w.temp_c} °C</b><br><br><br>"
    f"<b>{w.condition_text}</b><br><br><br>"
    f"{arrow} Wind: {wind_mps:.1f} m/s {w.wind_dir}<br>"
    f"Humidity: {w.humidity}%<br>"
    f"Pressure: {w.pressure_mb} mb<br><br>"
    f"{w.localtime}"
)

fig.add_annotation(
    text=details,
    x=LEFT_X_CENTER, y=0.40,
    xref="paper", yref="paper",
    align="left",
    showarrow=False,
    font=dict(size=14),
)



# -----------------------
# FINAL LAYOUT (Improved)
# -----------------------
fig.update_layout(
    title="🌤️ Kristiansand Weather",
    height=500,
    margin=dict(t=60, l=20, r=20, b=20),
    paper_bgcolor="#0f172a",
    plot_bgcolor="#0f172a",
    font=dict(color="#e2e8f0"),
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    xaxis2=dict(visible=False, range=[-1.5, 1.5]),
    yaxis2=dict(visible=False, range=[-1.5, 1.5]),
)

# -----------------------
# EXPORT CLEAN HTML
# -----------------------
html = fig.to_html(
    full_html=False,
    include_plotlyjs="cdn",   # 🚀 no giant inline JS
    config={"responsive": True}
)

# -----------------------
# DASHBOARD WRAPPER
# -----------------------
dashboard = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Live Weather Dashboard</title>

<!-- 🔄 Auto refresh every 5 minutes -->
<meta http-equiv="refresh" content="300">

<style>
body {{
    margin: 0;
    font-family: system-ui, sans-serif;
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: #e2e8f0;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}}

header {{
    text-align: center;
    padding: 1rem;
    font-size: 1.4rem;
    font-weight: 600;
}}

main {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 1rem;
}}

.card {{
    width: 100%;
    max-width: 900px;
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 1rem;
    backdrop-filter: blur(10px);
}}

footer {{
    text-align: center;
    font-size: 0.8rem;
    opacity: 0.7;
    padding: 0.5rem;
}}

</style>
</head>

<body>

<header>
    🌍 Live Weather Dashboard
</header>

<main>
    <section class="card">
        {html}
    </section>
</main>

<footer>
    Auto-updates every 5 minutes
</footer>

</body>
</html>
"""

# -----------------------
# SAVE
# -----------------------
out = Path("docs") / "index.html"
out.write_text(dashboard, encoding="utf-8")

print("✅ Live dashboard saved:", out)