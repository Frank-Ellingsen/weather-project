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
    "sunny": "☀️", "clear": "☀️",
    "partly cloudy": "⛅",
    "cloudy": "☁️",
    "overcast": "🌥️",
    "mist": "🌫️", "fog": "🌫️",
    "light rain": "🌦️", "moderate rain": "🌧️",
    "rain": "🌧️",
    "heavy rain": "🌧️💦",
    "snow": "❄️", "light snow": "🌨️",
    "sleet": "🌨️🌧️",
    "thunderstorm": "⛈️",
    "windy": "🌬️",
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
# FINAL LAYOUT
# -----------------------
fig.update_layout(
    title="Kristiansand Weather Report",
    height=460,
    margin=dict(t=50, l=10),
    paper_bgcolor="white",
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    xaxis2=dict(visible=False, range=[-1.5, 1.5]),
    yaxis2=dict(visible=False, range=[-1.5, 1.5]),
)

# -----------------------
# SAVE
# -----------------------
out = Path("docs") / "index.html"
fig.write_html(out)
print("✅ Saved:", out)