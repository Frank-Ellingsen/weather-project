import sqlite3
import pandas as pd
from pathlib import Path

# =====================================================
# ICONS + WIND ARROWS
# =====================================================
ICONS = {
    # Clear / Cloud
    'sunny': '☀️', 'clear': '☀️', 'partly cloudy': '⛅', 'cloudy': '☁️', 'overcast': '🌥️',
    # Fog / Mist
    'mist': '🌫️', 'fog': '🌫️',
    # Rain
    'patchy rain nearby': '🌦️', 'light rain': '🌦️', 'moderate rain': '🌧️', 'heavy rain': '🌧️💦',
    'rain': '🌧️', 'light drizzle': '🌦️', 'moderate drizzle': '🌧️',
    # Snow
    'light snow': '🌨️', 'snow': '❄️', 'heavy snow': '❄️❄️', 'patchy snow': '🌨️',
    # Sleet
    'sleet': '🌨️🌧️', 'light sleet': '🌨️🌦️', 'light sleet showers': '🌨️🌦️',
    'moderate sleet': '🌨️🌧️', 'moderate or heavy sleet': '🌨️🌧️💦', 'heavy sleet': '🌨️🌧️💦',
    # Freezing rain
    'light freezing rain': '🌧️🧊', 'freezing rain': '🌧️🧊',
    # Thunder / Wind
    'thunderstorm': '⛈️', 'windy': '🌬️'
}

def get_icon(cond):
    return ICONS.get(cond.lower(), "❓") if cond else "❓"

def wind_arrow(deg):
    arrows = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"]
    return arrows[int((deg + 222.5) // 45) % 8]

# =====================================================
# SVG CHART GENERATOR
# =====================================================
def generate_svg_chart(history_df):
    if len(history_df) < 2:
        return "<p style='color:#64748b;font-size:0.8rem;'>Not enough data for trend chart yet.</p>"

    # Settings
    width = 800
    height = 200
    padding_x = 40
    padding_y = 30
    
    # Extract and reverse to get chronological order (DESC in query)
    temps = history_df['temp_c'].tolist()[::-1]
    n = len(temps)
    x_indices = list(range(n))
    
    min_temp = min(temps)
    max_temp = max(temps)
    temp_range = max_temp - min_temp
    
    # Buffer
    if temp_range == 0: temp_range = 1
    y_min = min_temp - (temp_range * 0.2)
    y_max = max_temp + (temp_range * 0.2)
    y_range = y_max - y_min
    
    # Calculate Linear Regression (y = ax + b)
    sum_x = sum(x_indices)
    sum_y = sum(temps)
    sum_xy = sum(xi * yi for xi, yi in zip(x_indices, temps))
    sum_xx = sum(xi * xi for xi in x_indices)
    
    denom = (n * sum_xx - sum_x**2)
    if denom != 0:
        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n
        
        # Start and end points for trendline
        y1_val = a * 0 + b
        y2_val = a * (n - 1) + b
        
        # Scale to SVG
        x1 = padding_x
        y1 = height - ((y1_val - y_min) / y_range * (height - 2 * padding_y) + padding_y)
        x2 = width - padding_x
        y2 = height - ((y2_val - y_min) / y_range * (height - 2 * padding_y) + padding_y)
        trendline_svg = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(255, 255, 255, 0.4)" stroke-width="2" stroke-dasharray="5,5" />'
    else:
        trendline_svg = ""

    # Generate data points
    points = []
    for i, t in enumerate(temps):
        x = (i / (n - 1)) * (width - 2 * padding_x) + padding_x
        y = height - ((t - y_min) / y_range * (height - 2 * padding_y) + padding_y)
        points.append(f"{x:.1f},{y:.1f}")
    
    path_d = "M " + " L ".join(points)
    fill_d = f"{path_d} L {width-padding_x},{height-padding_y} L {padding_x},{height-padding_y} Z"
    
    svg = f"""
    <svg viewBox="0 0 {width} {height}" class="trend-chart" preserveAspectRatio="none">
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#60a5fa;stop-opacity:0.4" />
                <stop offset="100%" style="stop-color:#60a5fa;stop-opacity:0" />
            </linearGradient>
        </defs>
        <!-- Horizontal Guide Lines -->
        <line x1="{padding_x}" y1="{height-padding_y}" x2="{width-padding_x}" y2="{height-padding_y}" stroke="rgba(255,255,255,0.05)" stroke-width="1" />
        <line x1="{padding_x}" y1="{padding_y}" x2="{width-padding_x}" y2="{padding_y}" stroke="rgba(255,255,255,0.05)" stroke-width="1" />
        
        <!-- Data Line -->
        <path d="{fill_d}" fill="url(#grad)" stroke="none" />
        <path d="{path_d}" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
        
        <!-- Mathematical Trendline (Dashed) -->
        {trendline_svg}
        
        <!-- Labels -->
        <text x="{padding_x-5}" y="{height-padding_y+5}" fill="#64748b" font-size="12" text-anchor="end">{min_temp:.1f}°</text>
        <text x="{padding_x-5}" y="{padding_y+5}" fill="#64748b" font-size="12" text-anchor="end">{max_temp:.1f}°</text>
    </svg>
    """
    return svg

# =====================================================
# LOAD DATA
# =====================================================
conn = sqlite3.connect("weather.db")
df = pd.read_sql("SELECT * FROM weather_kristiansand ORDER BY last_updated DESC LIMIT 1", conn)
history_df = pd.read_sql("SELECT temp_c, last_updated FROM weather_kristiansand ORDER BY last_updated DESC LIMIT 336", conn)
conn.close()

if df.empty:
    print("❌ No data found in database.")
    exit(1)

w = df.iloc[0]
wind_mps = w.wind_kph / 3.6
icon = get_icon(w.condition_text)
arrow = wind_arrow(w.wind_degree)
svg_chart = generate_svg_chart(history_df)

# =====================================================
# DASHBOARD TEMPLATE
# =====================================================
dashboard = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Live Weather Dashboard</title>
<meta http-equiv="refresh" content="300">

<style>
body {{
    margin: 0;
    font-family: system-ui, -apple-system, sans-serif;
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: #e2e8f0;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}}

header {{
    text-align: center;
    padding: 2rem 1rem;
    font-size: 1.8rem;
    font-weight: 700;
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
    max-width: 600px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 24px;
    padding: 2rem;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}}

.current-weather {{
    text-align: center;
    margin-bottom: 2rem;
}}

.icon {{ font-size: 5rem; margin-bottom: 0.5rem; filter: drop-shadow(0 0 15px rgba(255,255,255,0.1)); }}
.temp {{ font-size: 3.5rem; font-weight: 800; margin: 0.5rem 0; background: linear-gradient(to bottom, #fff, #cbd5e1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.condition {{ font-size: 1.3rem; color: #94a3b8; text-transform: capitalize; margin-bottom: 1.5rem; }}

.details {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    background: rgba(0, 0, 0, 0.2);
    padding: 1.2rem;
    border-radius: 16px;
}}

.detail-item {{ display: flex; flex-direction: column; }}
.detail-label {{ font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }}
.detail-value {{ font-size: 1rem; font-weight: 600; }}

.trend-section {{
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}}

.trend-title {{ font-size: 0.8rem; color: #64748b; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }}
.trend-chart {{ width: 100%; height: 120px; overflow: visible; }}

.time {{ text-align: center; font-size: 0.8rem; opacity: 0.4; margin-top: 2rem; }}

footer {{ text-align: center; font-size: 0.8rem; opacity: 0.6; padding: 1.5rem; }}

@media (max-width: 480px) {{
    .card {{ padding: 1.5rem; }}
    .details {{ grid-template-columns: 1fr; }}
    .trend-chart {{ height: 80px; }}
}}
</style>
</head>

<body>
<header>🌍 Kristiansand Weather</header>
<main>
    <section class="card">
        <div class="current-weather">
            <div class="icon">{icon}</div>
            <div class="temp">{w.temp_c} °C</div>
            <div class="condition">{w.condition_text}</div>
            
            <div class="details">
                <div class="detail-item"><span class="detail-label">Wind</span><span class="detail-value">{arrow} {wind_mps:.1f} m/s {w.wind_dir}</span></div>
                <div class="detail-item"><span class="detail-label">Humidity</span><span class="detail-value">{w.humidity}%</span></div>
                <div class="detail-item"><span class="detail-label">Pressure</span><span class="detail-value">{w.pressure_mb} mb</span></div>
                <div class="detail-item"><span class="detail-label">Region</span><span class="detail-value">Kristiansand</span></div>
            </div>
        </div>

        <div class="trend-section">
            <div class="trend-title">Temperature Trend + Trendline (Last 14 Days)</div>
            {svg_chart}
        </div>

        <div class="time">Last updated: {w.localtime}</div>
    </section>
</main>
<footer>Auto-updates every 15 minutes • Data via WeatherAPI</footer>
</body>
</html>
"""

# =====================================================
# SAVE
# =====================================================
out = Path("docs") / "index.html"
out.write_text(dashboard, encoding="utf-8")
print("✅ Dashboard with trendline saved:", out)
