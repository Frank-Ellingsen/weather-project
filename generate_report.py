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
    'rain': '🌧️', 'light drizzle': '🌦️', 'moderate drizzle': '🌧️', 'light rain shower': '☁️🌧️',
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
    height = 220
    padding_left = 45
    padding_right = 95  # Space for direct label at the end of moving average line
    padding_y_top = 25
    padding_y_bottom = 35 # Space for date labels
    
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_y_top - padding_y_bottom
    
    # Chronological series
    temps = history_df['temp_c'].tolist()
    ma_temps = history_df['ma_30d'].tolist()
    times = history_df['datetime']
    n = len(temps)
    x_indices = list(range(n))
    
    min_temp = min(temps)
    max_temp = max(temps)
    temp_range = max_temp - min_temp
    
    # Buffer
    if temp_range == 0:
        temp_range = 1
    y_min = min_temp - (temp_range * 0.15)
    y_max = max_temp + (temp_range * 0.15)
    y_range = y_max - y_min
    
    # Calculate Linear Regression (y = ax + b)
    sum_x = sum(x_indices)
    sum_y = sum(temps)
    sum_xy = sum(xi * yi for xi, yi in zip(x_indices, temps))
    sum_xx = sum(xi * xi for xi in x_indices)
    
    denom = (n * sum_xx - sum_x**2)
    trendline_svg = ""
    if denom != 0:
        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n
        
        # Start and end points for trendline
        y1_val = a * 0 + b
        y2_val = a * (n - 1) + b
        
        # Scale to SVG
        x1 = padding_left
        y1 = height - padding_y_bottom - ((y1_val - y_min) / y_range * chart_h)
        x2 = padding_left + chart_w
        y2 = height - padding_y_bottom - ((y2_val - y_min) / y_range * chart_h)
        trendline_svg = f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(255, 255, 255, 0.25)" stroke-width="1.5" stroke-dasharray="4,4" />'

    # Raw Temperature points
    raw_points = []
    for i, t in enumerate(temps):
        x = (i / (n - 1)) * chart_w + padding_left
        y = height - padding_y_bottom - ((t - y_min) / y_range * chart_h)
        raw_points.append(f"{x:.1f},{y:.1f}")
    
    path_d = "M " + " L ".join(raw_points)
    fill_d = f"{path_d} L {padding_left + chart_w:.1f},{height - padding_y_bottom} L {padding_left:.1f},{height - padding_y_bottom} Z"
    
    # 30-Day Moving Average points
    ma_points = []
    for i, m in enumerate(ma_temps):
        x = (i / (n - 1)) * chart_w + padding_left
        y = height - padding_y_bottom - ((m - y_min) / y_range * chart_h)
        ma_points.append(f"{x:.1f},{y:.1f}")
    ma_path_d = "M " + " L ".join(ma_points)
    
    # Terminal point and direct label for 30d MA (Edward Tufte principle: direct labeling)
    last_ma = ma_temps[-1]
    last_ma_x = padding_left + chart_w
    last_ma_y = height - padding_y_bottom - ((last_ma - y_min) / y_range * chart_h)
    direct_label_svg = f"""
    <circle cx="{last_ma_x:.1f}" cy="{last_ma_y:.1f}" r="3" fill="#f59e0b" />
    <text x="{last_ma_x + 6:.1f}" y="{last_ma_y + 4:.1f}" fill="#f59e0b" font-size="11" font-weight="600" font-family="system-ui, sans-serif">30d MA {last_ma:.1f}°</text>
    """
    
    # 0°C baseline if within range
    zero_line_svg = ""
    if y_min < 0 < y_max:
        y_zero = height - padding_y_bottom - ((0 - y_min) / y_range * chart_h)
        zero_line_svg = f'<line x1="{padding_left}" y1="{y_zero:.1f}" x2="{padding_left + chart_w}" y2="{y_zero:.1f}" stroke="rgba(255,255,255,0.1)" stroke-dasharray="2,2" /><text x="{padding_left - 6}" y="{y_zero + 3:.1f}" fill="#64748b" font-size="10" text-anchor="end">0°</text>'

    # Date Labels (x-axis)
    num_labels = 5
    label_indices = [int(i * (n - 1) / (num_labels - 1)) for i in range(num_labels)]
    date_labels_svg = ""
    for idx in label_indices:
        x = (idx / (n - 1)) * chart_w + padding_left
        date_str = times.iloc[idx].strftime('%d %b')
        anchor = "middle"
        if idx == 0: anchor = "start"
        elif idx == n-1: anchor = "end"
        date_labels_svg += f'<text x="{x:.1f}" y="{height - 10}" fill="#64748b" font-size="10" text-anchor="{anchor}">{date_str}</text>\n'

    svg = f"""
    <svg viewBox="0 0 {width} {height}" class="trend-chart" preserveAspectRatio="xMidYMid meet">
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#60a5fa;stop-opacity:0.25" />
                <stop offset="100%" style="stop-color:#60a5fa;stop-opacity:0.0" />
            </linearGradient>
        </defs>
        <!-- Horizontal Guide Lines -->
        <line x1="{padding_left}" y1="{height - padding_y_bottom}" x2="{padding_left + chart_w}" y2="{height - padding_y_bottom}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
        <line x1="{padding_left}" y1="{padding_y_top}" x2="{padding_left + chart_w}" y2="{padding_y_top}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
        {zero_line_svg}
        
        <!-- Raw Data Fill & Line -->
        <path d="{fill_d}" fill="url(#grad)" stroke="none" />
        <path d="{path_d}" fill="none" stroke="#60a5fa" stroke-width="1.5" stroke-opacity="0.45" stroke-linecap="round" stroke-linejoin="round" />
        
        <!-- Mathematical Trendline (Dashed) -->
        {trendline_svg}
        
        <!-- 30-Day Moving Average Line -->
        <path d="{ma_path_d}" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
        
        <!-- Direct Label -->
        {direct_label_svg}
        
        <!-- Y-Axis Labels -->
        <text x="{padding_left - 6}" y="{height - padding_y_bottom + 4}" fill="#64748b" font-size="11" text-anchor="end">{min_temp:.1f}°</text>
        <text x="{padding_left - 6}" y="{padding_y_top + 4}" fill="#64748b" font-size="11" text-anchor="end">{max_temp:.1f}°</text>
        
        <!-- Date Indicators -->
        {date_labels_svg}
    </svg>
    """
    return svg

# =====================================================
# LOAD & PROCESS DATA
# =====================================================
conn = sqlite3.connect("weather.db")
df = pd.read_sql("SELECT * FROM weather_kristiansand ORDER BY last_updated DESC LIMIT 1", conn)
history_df = pd.read_sql("SELECT temp_c, last_updated FROM weather_kristiansand ORDER BY last_updated ASC", conn)
conn.close()

# Drop rows where critical data is missing
history_df = history_df.dropna(subset=['temp_c', 'last_updated']).copy()

if df.empty or history_df.empty:
    print("[ERROR] No data found in database.")
    exit(1)

# Chronological sorting & datetime index
history_df['datetime'] = pd.to_datetime(history_df['last_updated'])
history_df = history_df.sort_values('datetime').reset_index(drop=True)

# 30-day continuous rolling moving average
history_df['ma_30d'] = history_df.set_index('datetime')['temp_c'].rolling('30D', min_periods=1).mean().values

w = df.iloc[0]
wind_mps = w.wind_kph / 3.6
icon = get_icon(w.condition_text)
arrow = wind_arrow(w.wind_degree)

# Moving average KPI metrics
latest_ma_30d = history_df['ma_30d'].iloc[-1]
variance_vs_ma = w.temp_c - latest_ma_30d
var_color = "#38bdf8" if variance_vs_ma < 0 else "#f87171"

# Monthly aggregated statistics
history_df['month_period'] = history_df['datetime'].dt.to_period('M')
monthly_stats = history_df.groupby('month_period').agg(
    month_label=('datetime', lambda s: s.iloc[0].strftime('%B %Y')),
    mean_temp=('temp_c', 'mean'),
    min_temp=('temp_c', 'min'),
    max_temp=('temp_c', 'max'),
    readings=('temp_c', 'count')
).reset_index()

monthly_rows = []
for _, row in monthly_stats.iterrows():
    monthly_rows.append(f"""
        <tr>
            <td style="text-align: left;">{row['month_label']}</td>
            <td style="text-align: right;">{row['mean_temp']:.1f} °C</td>
            <td style="text-align: right;">{row['min_temp']:.1f} °C</td>
            <td style="text-align: right;">{row['max_temp']:.1f} °C</td>
            <td style="text-align: right; color: #64748b;">{int(row['readings']):,}</td>
        </tr>
    """)
monthly_rows_html = "".join(monthly_rows)

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
<title>Kristiansand Weather & Trend Analysis</title>
<meta http-equiv="refresh" content="300">

<style>
body {{
    margin: 0;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: #e2e8f0;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}}

header {{
    text-align: center;
    padding: 2rem 1rem 1.2rem;
    font-size: 1.8rem;
    font-weight: 700;
    letter-spacing: -0.02em;
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
    max-width: 640px;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 20px;
    padding: 2rem;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
}}

.current-weather {{
    text-align: center;
    margin-bottom: 2rem;
}}

.icon {{ font-size: 4.8rem; margin-bottom: 0.25rem; }}
.temp {{ font-size: 3.5rem; font-weight: 800; margin: 0.25rem 0; background: linear-gradient(to bottom, #fff, #cbd5e1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.condition {{ font-size: 1.25rem; color: #94a3b8; text-transform: capitalize; margin-bottom: 1.5rem; }}

.details {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.85rem;
    background: rgba(0, 0, 0, 0.22);
    padding: 1.1rem;
    border-radius: 14px;
}}

.detail-item {{ display: flex; flex-direction: column; gap: 0.2rem; }}
.detail-label {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }}
.detail-value {{ font-size: 0.95rem; font-weight: 600; font-variant-numeric: tabular-nums; }}

.section-divider {{
    margin-top: 1.8rem;
    padding-top: 1.4rem;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
}}

.section-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.75rem;
}}

.section-title {{
    font-size: 0.78rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 700;
}}

.chart-legend {{
    display: flex;
    gap: 1rem;
    font-size: 0.72rem;
    color: #94a3b8;
}}

.legend-item {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}}

.legend-bar {{
    display: inline-block;
    width: 12px;
    height: 2.5px;
    border-radius: 1px;
}}

.trend-chart {{
    width: 100%;
    height: auto;
    overflow: visible;
    display: block;
}}

/* Edward Tufte-compliant summary table */
.tufte-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.84rem;
    color: #cbd5e1;
    margin-top: 0.5rem;
}}

.tufte-table th {{
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    padding: 0.5rem 0.6rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.18);
}}

.tufte-table td {{
    padding: 0.5rem 0.6rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    font-variant-numeric: tabular-nums;
}}

.tufte-table tbody tr:hover {{
    background: rgba(255, 255, 255, 0.02);
}}

.time {{ text-align: center; font-size: 0.78rem; color: #64748b; margin-top: 1.8rem; }}

footer {{ text-align: center; font-size: 0.78rem; color: #64748b; padding: 1.5rem; }}

@media (max-width: 540px) {{
    .card {{ padding: 1.4rem; }}
    .details {{ grid-template-columns: repeat(2, 1fr); }}
    .chart-legend {{ font-size: 0.68rem; gap: 0.6rem; }}
    .tufte-table th, .tufte-table td {{ padding: 0.4rem 0.35rem; font-size: 0.76rem; }}
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
                <div class="detail-item"><span class="detail-label">30-Day Moving Avg</span><span class="detail-value" style="color: #f59e0b;">{latest_ma_30d:.1f} °C</span></div>
                <div class="detail-item"><span class="detail-label">Variance vs 30d</span><span class="detail-value" style="color: {var_color};">{variance_vs_ma:+.1f} °C</span></div>
                <div class="detail-item"><span class="detail-label">Region</span><span class="detail-value">Kristiansand</span></div>
            </div>
        </div>

        <!-- Trend Chart Section -->
        <div class="section-divider">
            <div class="section-header">
                <div class="section-title">Temperature Trend & Moving Average</div>
                <div class="chart-legend">
                    <span class="legend-item"><span class="legend-bar" style="background: #60a5fa; opacity: 0.6;"></span> Hourly</span>
                    <span class="legend-item"><span class="legend-bar" style="background: #f59e0b;"></span> 30d MA</span>
                    <span class="legend-item"><span class="legend-bar" style="border-top: 1.5px dashed rgba(255,255,255,0.4); height: 0;"></span> Trend</span>
                </div>
            </div>
            {svg_chart}
        </div>

        <!-- Monthly Summary Section (Edward Tufte data-ink ratio principles) -->
        <div class="section-divider">
            <div class="section-header">
                <div class="section-title">Monthly Temperature Summary</div>
            </div>
            <table class="tufte-table">
                <thead>
                    <tr>
                        <th style="text-align: left;">Month</th>
                        <th style="text-align: right;">Mean</th>
                        <th style="text-align: right;">Min</th>
                        <th style="text-align: right;">Max</th>
                        <th style="text-align: right;">Readings</th>
                    </tr>
                </thead>
                <tbody>
                    {monthly_rows_html}
                </tbody>
            </table>
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
out_path = Path(__file__).parent / "docs" / "index.html"
out_path.write_text(dashboard, encoding="utf-8")
print("[SUCCESS] Dashboard with monthly moving average saved:", out_path)

