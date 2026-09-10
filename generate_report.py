import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from forecast import run_forecast_pipeline

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
# SVG HISTORICAL TREND CHART (OPTIMIZED TUFTE DESIGN)
# =====================================================
def generate_svg_chart(history_df):
    if len(history_df) < 2:
        return "<p style='color:#64748b;font-size:0.8rem;'>Not enough data for trend chart yet.</p>"

    # Sample points to optimize SVG size while maintaining high visual fidelity
    stride = max(1, len(history_df) // 300)
    sampled_df = history_df.iloc[::stride].copy()
    if history_df.index[-1] not in sampled_df.index:
        sampled_df = pd.concat([sampled_df, history_df.iloc[[-1]]])

    width = 800
    height = 220
    padding_left = 45
    padding_right = 95
    padding_y_top = 25
    padding_y_bottom = 35
    
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_y_top - padding_y_bottom
    
    temps = sampled_df['temp_c'].tolist()
    ma_temps = sampled_df['ma_30d'].tolist()
    times = sampled_df['datetime']
    n = len(temps)
    x_indices = list(range(n))
    
    min_temp = min(temps)
    max_temp = max(temps)
    temp_range = max_temp - min_temp
    if temp_range == 0:
        temp_range = 1
    y_min = min_temp - (temp_range * 0.15)
    y_max = max_temp + (temp_range * 0.15)
    y_range = y_max - y_min
    
    # Linear Regression (y = ax + b)
    sum_x = sum(x_indices)
    sum_y = sum(temps)
    sum_xy = sum(xi * yi for xi, yi in zip(x_indices, temps))
    sum_xx = sum(xi * xi for xi in x_indices)
    
    denom = (n * sum_xx - sum_x**2)
    trendline_svg = ""
    if denom != 0:
        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n
        y1_val = a * 0 + b
        y2_val = a * (n - 1) + b
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
    
    last_ma = ma_temps[-1]
    last_ma_x = padding_left + chart_w
    last_ma_y = height - padding_y_bottom - ((last_ma - y_min) / y_range * chart_h)
    direct_label_svg = f"""
    <circle cx="{last_ma_x:.1f}" cy="{last_ma_y:.1f}" r="3" fill="#f59e0b" />
    <text x="{last_ma_x + 6:.1f}" y="{last_ma_y + 4:.1f}" fill="#f59e0b" font-size="11" font-weight="600" font-family="system-ui, sans-serif">30d MA {last_ma:.1f}°</text>
    """
    
    zero_line_svg = ""
    if y_min < 0 < y_max:
        y_zero = height - padding_y_bottom - ((0 - y_min) / y_range * chart_h)
        zero_line_svg = f'<line x1="{padding_left}" y1="{y_zero:.1f}" x2="{padding_left + chart_w}" y2="{y_zero:.1f}" stroke="rgba(255,255,255,0.1)" stroke-dasharray="2,2" /><text x="{padding_left - 6}" y="{y_zero + 3:.1f}" fill="#64748b" font-size="10" text-anchor="end">0°</text>'

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
        <line x1="{padding_left}" y1="{height - padding_y_bottom}" x2="{padding_left + chart_w}" y2="{height - padding_y_bottom}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
        <line x1="{padding_left}" y1="{padding_y_top}" x2="{padding_left + chart_w}" y2="{padding_y_top}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
        {zero_line_svg}
        
        <path d="{fill_d}" fill="url(#grad)" stroke="none" />
        <path d="{path_d}" fill="none" stroke="#60a5fa" stroke-width="1.5" stroke-opacity="0.45" stroke-linecap="round" stroke-linejoin="round" />
        {trendline_svg}
        <path d="{ma_path_d}" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
        {direct_label_svg}
        <text x="{padding_left - 6}" y="{height - padding_y_bottom + 4}" fill="#64748b" font-size="11" text-anchor="end">{min_temp:.1f}°</text>
        <text x="{padding_left - 6}" y="{padding_y_top + 4}" fill="#64748b" font-size="11" text-anchor="end">{max_temp:.1f}°</text>
        {date_labels_svg}
    </svg>
    """
    return svg

# =====================================================
# SVG FORECASTING DIAGRAM (REAL VS PREDICTION)
# =====================================================
def generate_forecast_svg_chart(bundle):
    past_df = bundle['past_eval_df']
    f_df = bundle['forecast_df']
    
    # Subsample hourly readings slightly for ultra-clean rendering (every 2h)
    p_step = 2
    f_step = 2
    p_sub = past_df.iloc[::p_step].copy()
    if past_df.index[-1] not in p_sub.index:
        p_sub = pd.concat([p_sub, past_df.iloc[[-1]]])
        
    f_sub = f_df.iloc[::f_step].copy()
    if f_df.index[-1] not in f_sub.index:
        f_sub = pd.concat([f_sub, f_df.iloc[[-1]]])

    # Settings
    width = 800
    height = 260
    padding_left = 45
    padding_right = 85
    padding_y_top = 35
    padding_y_bottom = 35
    
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_y_top - padding_y_bottom
    
    # Timeline coordinates
    n_past = len(p_sub)
    n_future = len(f_sub)
    total_points = n_past + n_future - 1  # Sharing the origin point
    
    # Range calculation
    all_vals = (
        p_sub['temp_actual_c'].tolist() +
        p_sub['temp_model_c'].tolist() +
        f_sub['temp_pred_c'].tolist() +
        f_sub['temp_lower_c'].tolist() +
        f_sub['temp_upper_c'].tolist()
    )
    min_temp = min(all_vals)
    max_temp = max(all_vals)
    t_range = max_temp - min_temp
    if t_range == 0:
        t_range = 1.0
    y_min = min_temp - (t_range * 0.14)
    y_max = max_temp + (t_range * 0.14)
    y_range = y_max - y_min

    def get_y(val):
        return height - padding_y_bottom - ((val - y_min) / y_range * chart_h)

    # Origin (Now / Today) X position
    x_origin = padding_left + ((n_past - 1) / (total_points - 1)) * chart_w
    y_origin_actual = get_y(p_sub['temp_actual_c'].iloc[-1])
    y_origin_pred = get_y(f_sub['temp_pred_c'].iloc[0])

    # 1. Past Actuals path
    past_actual_points = []
    for i, val in enumerate(p_sub['temp_actual_c']):
        x = padding_left + (i / (total_points - 1)) * chart_w
        y = get_y(val)
        past_actual_points.append(f"{x:.1f},{y:.1f}")
    past_actual_d = "M " + " L ".join(past_actual_points)

    # 2. Past Backtest path
    past_model_points = []
    for i, val in enumerate(p_sub['temp_model_c']):
        x = padding_left + (i / (total_points - 1)) * chart_w
        y = get_y(val)
        past_model_points.append(f"{x:.1f},{y:.1f}")
    past_model_d = "M " + " L ".join(past_model_points)

    # 3. Future Forecast path
    future_points = [f"{x_origin:.1f},{y_origin_actual:.1f}"]
    for i, val in enumerate(f_sub['temp_pred_c']):
        idx = (n_past - 1) + i
        x = padding_left + (idx / (total_points - 1)) * chart_w
        y = get_y(val)
        future_points.append(f"{x:.1f},{y:.1f}")
    future_d = "M " + " L ".join(future_points)

    # 4. Future Confidence Corridor (Upper & Lower Bands)
    upper_corridor = [f"{x_origin:.1f},{y_origin_actual:.1f}"]
    lower_corridor = []
    for i in range(len(f_sub)):
        idx = (n_past - 1) + i
        x = padding_left + (idx / (total_points - 1)) * chart_w
        y_u = get_y(f_sub['temp_upper_c'].iloc[i])
        y_l = get_y(f_sub['temp_lower_c'].iloc[i])
        upper_corridor.append(f"{x:.1f},{y_u:.1f}")
        lower_corridor.append(f"{x:.1f},{y_l:.1f}")

    # Form closed polygon
    corridor_d = "M " + " L ".join(upper_corridor) + " L " + " L ".join(reversed(lower_corridor)) + f" L {x_origin:.1f},{y_origin_actual:.1f} Z"

    # End point of 7-day forecast
    last_pred = f_sub['temp_pred_c'].iloc[-1]
    last_x = padding_left + chart_w
    last_y = get_y(last_pred)

    # Peak future max
    max_idx = f_sub['temp_pred_c'].values.argmax()
    max_val = f_sub['temp_pred_c'].iloc[max_idx]
    max_x = padding_left + (((n_past - 1) + max_idx) / (total_points - 1)) * chart_w
    max_y = get_y(max_val)

    # 0°C baseline
    zero_line_svg = ""
    if y_min < 0 < y_max:
        y_zero = get_y(0.0)
        zero_line_svg = f'<line x1="{padding_left}" y1="{y_zero:.1f}" x2="{padding_left + chart_w}" y2="{y_zero:.1f}" stroke="rgba(255,255,255,0.12)" stroke-dasharray="2,2" /><text x="{padding_left - 6}" y="{y_zero + 3:.1f}" fill="#64748b" font-size="10" text-anchor="end">0°</text>'

    # Timeline Date Labels
    dates_svg = ""
    # We display 7 markers: -6d, -4d, -2d, Today (0), +2d, +4d, +6d
    combined_dts = p_sub['datetime'].tolist() + f_sub['datetime'].iloc[1:].tolist()
    step_idx = max(1, (len(combined_dts) - 1) // 6)
    for i in range(0, len(combined_dts), step_idx):
        x = padding_left + (i / (len(combined_dts) - 1)) * chart_w
        dt_val = combined_dts[i]
        date_str = dt_val.strftime('%d %b')
        anchor = "middle"
        if i == 0: anchor = "start"
        elif i >= len(combined_dts) - step_idx: anchor = "end"
        
        is_today = abs(x - x_origin) < 15
        color = "#e2e8f0" if is_today else "#64748b"
        weight = "700" if is_today else "400"
        dates_svg += f'<text x="{x:.1f}" y="{height - 10}" fill="{color}" font-weight="{weight}" font-size="10" text-anchor="{anchor}">{date_str}</text>\n'

    svg = f"""
    <svg viewBox="0 0 {width} {height}" class="trend-chart" preserveAspectRatio="xMidYMid meet">
        <defs>
            <linearGradient id="forecastCorridorGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#f59e0b;stop-opacity:0.22" />
                <stop offset="50%" style="stop-color:#f59e0b;stop-opacity:0.08" />
                <stop offset="100%" style="stop-color:#f59e0b;stop-opacity:0.02" />
            </linearGradient>
        </defs>

        <!-- Shaded Sectors: Past vs Future Horizon -->
        <rect x="{padding_left}" y="{padding_y_top}" width="{x_origin - padding_left:.1f}" height="{chart_h}" fill="rgba(255,255,255,0.012)" rx="3" />
        <rect x="{x_origin:.1f}" y="{padding_y_top}" width="{padding_left + chart_w - x_origin:.1f}" height="{chart_h}" fill="rgba(245,158,11,0.025)" rx="3" />

        <!-- Grid Lines -->
        <line x1="{padding_left}" y1="{height - padding_y_bottom}" x2="{padding_left + chart_w}" y2="{height - padding_y_bottom}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
        <line x1="{padding_left}" y1="{padding_y_top}" x2="{padding_left + chart_w}" y2="{padding_y_top}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
        {zero_line_svg}

        <!-- Vertical Forecast Origin Divider -->
        <line x1="{x_origin:.1f}" y1="{padding_y_top - 5}" x2="{x_origin:.1f}" y2="{height - padding_y_bottom}" stroke="rgba(255,255,255,0.3)" stroke-width="1.5" stroke-dasharray="3,3" />
        <text x="{x_origin:.1f}" y="{padding_y_top - 12}" fill="#cbd5e1" font-size="9" font-weight="700" letter-spacing="0.08em" text-anchor="middle">TODAY (FORECAST ORIGIN)</text>

        <!-- Confidence Interval Corridor (80% Risk Band) -->
        <path d="{corridor_d}" fill="url(#forecastCorridorGrad)" stroke="none" />

        <!-- Historical Backtest Model Curve (Dashed Slate) -->
        <path d="{past_model_d}" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="1.5" stroke-dasharray="4,4" stroke-linecap="round" />

        <!-- Real Temperatures Observed (Cyan) -->
        <path d="{past_actual_d}" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />

        <!-- 7-Day Temperature Forecast (Amber) -->
        <path d="{future_d}" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />

        <!-- Direct Labels & Highlights (Edward Tufte principle) -->
        <circle cx="{x_origin:.1f}" cy="{y_origin_actual:.1f}" r="3.5" fill="#38bdf8" />
        <text x="{x_origin - 6:.1f}" y="{y_origin_actual - 6:.1f}" fill="#38bdf8" font-size="11" font-weight="700" text-anchor="end">{p_sub['temp_actual_c'].iloc[-1]:.1f}°</text>

        <!-- Peak Max Marker -->
        <circle cx="{max_x:.1f}" cy="{max_y:.1f}" r="3" fill="#f59e0b" />
        <text x="{max_x:.1f}" y="{max_y - 8:.1f}" fill="#f59e0b" font-size="10" font-weight="600" text-anchor="middle">Peak {max_val:.1f}°</text>

        <!-- Terminal Forecast Label -->
        <circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3" fill="#f59e0b" />
        <text x="{last_x + 6:.1f}" y="{last_y + 4:.1f}" fill="#f59e0b" font-size="11" font-weight="700">7d: {last_pred:.1f}°</text>

        <!-- Y-Axis Labels -->
        <text x="{padding_left - 6}" y="{height - padding_y_bottom + 4}" fill="#64748b" font-size="11" text-anchor="end">{min_temp:.1f}°</text>
        <text x="{padding_left - 6}" y="{padding_y_top + 4}" fill="#64748b" font-size="11" text-anchor="end">{max_temp:.1f}°</text>

        <!-- Timeline Dates -->
        {dates_svg}
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

history_df = history_df.dropna(subset=['temp_c', 'last_updated']).copy()

if df.empty or history_df.empty:
    print("[ERROR] No data found in database.")
    exit(1)

history_df['datetime'] = pd.to_datetime(history_df['last_updated'])
history_df = history_df.sort_values('datetime').reset_index(drop=True)
history_df['ma_30d'] = history_df.set_index('datetime')['temp_c'].rolling('30D', min_periods=1).mean().values

w = df.iloc[0]
wind_mps = w.wind_kph / 3.6
icon = get_icon(w.condition_text)
arrow = wind_arrow(w.wind_degree)

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
# RUN FORECAST PIPELINE & GENERATE FORECAST DIAGRAM
# =====================================================
print("[INFO] Running 7-day temperature forecasting engine...")
forecast_bundle = run_forecast_pipeline("weather.db")
forecast_svg = generate_forecast_svg_chart(forecast_bundle)

# Daily 7-Day Forecast Table Rows
daily_forecast_rows = []
for row in forecast_bundle['daily_summary']:
    # Trend arrow compared to current temp
    diff = row['mean_temp'] - w.temp_c
    diff_badge = f"{diff:+.1f}°C"
    diff_color = "#f87171" if diff > 0.5 else ("#38bdf8" if diff < -0.5 else "#94a3b8")
    
    daily_forecast_rows.append(f"""
        <tr>
            <td style="text-align: left; font-weight: 600;">{row['day_name']} <span style="color:#64748b;font-weight:400;font-size:0.75rem;">{row['date_str']}</span></td>
            <td style="text-align: right; color: #38bdf8;">{row['min_temp']:.1f} °C</td>
            <td style="text-align: right; color: #fbbf24;">{row['max_temp']:.1f} °C</td>
            <td style="text-align: right; font-weight: 600;">{row['mean_temp']:.1f} °C</td>
            <td style="text-align: right; color: {diff_color}; font-size: 0.78rem;">{diff_badge}</td>
        </tr>
    """)
daily_forecast_rows_html = "".join(daily_forecast_rows)

m = forecast_bundle['metrics']
info = forecast_bundle['model_info']

# =====================================================
# DASHBOARD TEMPLATE (EXTENDED WITH FORECAST CARD)
# =====================================================
dashboard = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kristiansand Weather & 7-Day Forecasting</title>
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
    flex-direction: column;
    align-items: center;
    padding: 1rem;
    gap: 1.8rem;
}}

.card {{
    width: 100%;
    max-width: 680px;
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
    font-size: 0.82rem;
    color: #cbd5e1;
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

/* Scorecard Grid for Model Evaluation */
.scorecard-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin-top: 1rem;
    margin-bottom: 1.2rem;
}}

.scorecard-box {{
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    padding: 0.75rem;
    text-align: center;
}}

.scorecard-val {{
    font-size: 1.25rem;
    font-weight: 700;
    color: #f8fafc;
    font-variant-numeric: tabular-nums;
}}

.scorecard-label {{
    font-size: 0.65rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.2rem;
}}

/* Explainer Text Block */
.explainer-block {{
    background: rgba(0, 0, 0, 0.16);
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
    margin-top: 1rem;
    font-size: 0.8rem;
    line-height: 1.6;
    color: #94a3b8;
}}

.explainer-block h4 {{
    margin: 0 0 0.4rem 0;
    font-size: 0.85rem;
    color: #e2e8f0;
    font-weight: 600;
}}

.explainer-block p {{
    margin: 0 0 0.75rem 0;
}}

.explainer-block p:last-child {{
    margin-bottom: 0;
}}

.tag {{
    display: inline-block;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    font-size: 0.68rem;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.08);
    color: #cbd5e1;
}}

.time {{ text-align: center; font-size: 0.78rem; color: #64748b; margin-top: 1.8rem; }}

footer {{ text-align: center; font-size: 0.78rem; color: #64748b; padding: 1.5rem; }}

@media (max-width: 600px) {{
    .card {{ padding: 1.4rem; }}
    .details {{ grid-template-columns: repeat(2, 1fr); }}
    .scorecard-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .chart-legend {{ font-size: 0.65rem; gap: 0.5rem; }}
    .tufte-table th, .tufte-table td {{ padding: 0.4rem 0.35rem; font-size: 0.76rem; }}
}}
</style>
</head>

<body>
<header>🌍 Kristiansand Weather & Forecasting</header>
<main>

    <!-- CARD 1: CURRENT OBSERVATION & LONG-TERM TREND -->
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
                <div class="section-title">Macro Temperature Trend & 30d Moving Average</div>
                <div class="chart-legend">
                    <span class="legend-item"><span class="legend-bar" style="background: #60a5fa; opacity: 0.6;"></span> Actual</span>
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

        <div class="time">Observation recorded: {w.localtime}</div>
    </section>

    <!-- CARD 2: 7-DAY PREDICTIVE FORECAST & MODEL EVALUATION -->
    <section class="card" id="forecasting-section">
        <div class="section-header">
            <div>
                <div class="section-title" style="font-size: 1.1rem; color: #f8fafc;">7-Day Temperature Forecast & Evaluation</div>
                <div style="font-size: 0.74rem; color: #94a3b8; margin-top: 0.2rem;">Historical Real vs Backtest • 168-Hour Forward Trajectory • 80% Risk Corridor</div>
            </div>
            <div class="chart-legend">
                <span class="legend-item"><span class="legend-bar" style="background: #38bdf8;"></span> Real</span>
                <span class="legend-item"><span class="legend-bar" style="border-top: 1.5px dashed rgba(255,255,255,0.4); height: 0;"></span> Backtest</span>
                <span class="legend-item"><span class="legend-bar" style="background: #f59e0b;"></span> 7d Forecast</span>
            </div>
        </div>

        <!-- Dedicated Forecasting SVG Diagram -->
        <div style="margin-top: 1.2rem;">
            {forecast_svg}
        </div>

        <!-- Daily 7-Day Forecast Breakdown -->
        <div class="section-divider">
            <div class="section-header">
                <div class="section-title">Daily Temperature Projections (Next 7 Days)</div>
            </div>
            <table class="tufte-table">
                <thead>
                    <tr>
                        <th style="text-align: left;">Day & Date</th>
                        <th style="text-align: right;">Projected Min</th>
                        <th style="text-align: right;">Projected Max</th>
                        <th style="text-align: right;">Expected Mean</th>
                        <th style="text-align: right;">Variance vs Today</th>
                    </tr>
                </thead>
                <tbody>
                    {daily_forecast_rows_html}
                </tbody>
            </table>
        </div>

        <!-- Quantitative Evaluation Scorecard -->
        <div class="section-divider">
            <div class="section-header">
                <div class="section-title">Historical Backtesting Evaluation Scorecard</div>
                <span class="tag">Out-of-Sample Rolling 7-Day Windows</span>
            </div>
            <div class="scorecard-grid">
                <div class="scorecard-box">
                    <div class="scorecard-val">{m['mae']:.2f} °C</div>
                    <div class="scorecard-label">Mean Absolute Error (MAE)</div>
                </div>
                <div class="scorecard-box">
                    <div class="scorecard-val">{m['rmse']:.2f} °C</div>
                    <div class="scorecard-label">Root Mean Sq. Error (RMSE)</div>
                </div>
                <div class="scorecard-box">
                    <div class="scorecard-val" style="color: {'#38bdf8' if m['bias'] < 0 else '#fbbf24'};">{m['bias']:+.2f} °C</div>
                    <div class="scorecard-label">Mean Bias Error (MBE)</div>
                </div>
                <div class="scorecard-box">
                    <div class="scorecard-val">{m['within_2c_pct']:.1f}%</div>
                    <div class="scorecard-label">Accuracy within ±2.0°C</div>
                </div>
            </div>
        </div>

        <!-- Model Explainer & Methodology -->
        <div class="explainer-block">
            <h4>📐 Model Architecture & Forecasting Methodology</h4>
            <p>
                The 7-day temperature trajectory is projected using a hybrid <strong>Harmonic Fourier Decomposition with Synoptic Autoregressive Decay</strong>, fitted across all {info['train_points']:,} historical hourly readings from {info['train_start']} to {info['train_end']}:
            </p>
            <p>
                <strong>1. Diurnal Solar Insolation (Fourier Harmonics):</strong> Captures the cyclical 24-hour day/night solar heating and nocturnal radiative cooling using primary ($k=1$) and semi-diurnal ($k=2$) trigonometric basis functions (&omega; = 2&pi;h/24).
            </p>
            <p>
                <strong>2. Macro Seasonal Drift:</strong> A second-order polynomial component accounts for seasonal transition (summer to autumn solar elevation changes in Kristiansand).
            </p>
            <p>
                <strong>3. Synoptic Air Mass Persistence (AR Inertia):</strong> The current real-time deviation from baseline ({info['current_anomaly']:+.2f} °C) represents transient pressure systems. This variance decays with an autoregressive half-life of ~48 hours (&phi;<sup>h/24</sup> with &phi; = 0.70), guiding the forecast smoothly back toward the climatological baseline.
            </p>
            <p>
                <strong>4. Project Controlling & EAC Analogy:</strong> In project controlling (EAC/ETC forecasting), performance separates baseline planned rhythms from transient cost variances. Similarly, this model separates recurring diurnal cycles from transient air-mass variances, projecting an expected estimate to completion with an expanding 80% risk corridor.
            </p>
        </div>

        <div class="time">Continuous Weekly Automation • Model Calibrated on SQLite DB</div>
    </section>

</main>
<footer>Auto-updates every 15 minutes • Continuous weekly forecast automation via Windows Task Scheduler</footer>
</body>
</html>
"""

# =====================================================
# SAVE
# =====================================================
out_path = Path(__file__).parent / "docs" / "index.html"
out_path.write_text(dashboard, encoding="utf-8")
print("[SUCCESS] Complete dashboard with 7-day forecasting diagram saved:", out_path)
