import requests
import sqlite3
import os
from dotenv import load_dotenv

# =====================================================
# CONFIGURATION
# =====================================================
load_dotenv()
DB_PATH = "weather.db"
API_KEY = os.getenv("WEATHER_API_KEY")

if not API_KEY:
    raise ValueError("Missing WEATHER_API_KEY environment variable.")

LOCATION = "Kristiansand"
URL = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={LOCATION}&aqi=yes"

# =====================================================
# FETCH DATA
# =====================================================
try:
    response = requests.get(URL, timeout=15)
    response.raise_for_status()
    data = response.json()
except Exception as e:
    print(f"❌ Failed to fetch weather data: {e}")
    exit(1)

# =====================================================
# PREPARE DATA
# =====================================================
loc = data["location"]
cur = data["current"]
aq = cur.get("air_quality", {})

row = (
    loc.get("name"),
    loc.get("region"),
    loc.get("country"),
    loc.get("lat"),
    loc.get("lon"),
    loc.get("tz_id"),
    loc.get("localtime"),

    cur.get("last_updated"),
    cur.get("temp_c"),
    cur.get("temp_f"),
    cur.get("is_day"),
    cur.get("condition", {}).get("text"),
    cur.get("wind_mph"),
    cur.get("wind_kph"),
    cur.get("wind_degree"),
    cur.get("wind_dir"),
    cur.get("pressure_mb"),
    cur.get("precip_mm"),
    cur.get("humidity"),
    cur.get("cloud"),
    cur.get("feelslike_c"),
    cur.get("feelslike_f"),
    cur.get("windchill_c"),
    cur.get("windchill_f"),
    cur.get("heatindex_c"),
    cur.get("heatindex_f"),
    cur.get("dewpoint_c"),
    cur.get("dewpoint_f"),
    cur.get("vis_km"),
    cur.get("uv"),
    cur.get("gust_kph"),

    aq.get("co"),
    aq.get("no2"),
    aq.get("o3"),
    aq.get("so2"),
    aq.get("pm2_5"),
    aq.get("pm10"),
    aq.get("us-epa-index"),
    aq.get("gb-defra-index")
)

# =====================================================
# SAVE TO DATABASE
# =====================================================
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather_kristiansand (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, region TEXT, country TEXT, lat REAL, lon REAL, tz_id TEXT, localtime TEXT,
        last_updated TEXT, temp_c REAL, temp_f REAL, is_day INTEGER, condition_text TEXT,
        wind_mph REAL, wind_kph REAL, wind_degree INTEGER, wind_dir TEXT,
        pressure_mb REAL, precip_mm REAL, humidity INTEGER, cloud INTEGER,
        feelslike_c REAL, feelslike_f REAL, windchill_c REAL, windchill_f REAL,
        heatindex_c REAL, heatindex_f REAL, dewpoint_c REAL, dewpoint_f REAL,
        vis_km REAL, uv REAL, gust_kph REAL,
        co REAL, no2 REAL, o3 REAL, so2 REAL, pm2_5 REAL, pm10 REAL,
        us_epa_index INTEGER, gb_defra_index INTEGER
    )
    """)

    cursor.execute("""
    INSERT INTO weather_kristiansand (
        name, region, country, lat, lon, tz_id, localtime,
        last_updated, temp_c, temp_f, is_day, condition_text,
        wind_mph, wind_kph, wind_degree, wind_dir,
        pressure_mb, precip_mm, humidity, cloud,
        feelslike_c, feelslike_f,
        windchill_c, windchill_f,
        heatindex_c, heatindex_f,
        dewpoint_c, dewpoint_f,
        vis_km, uv, gust_kph,
        co, no2, o3, so2, pm2_5, pm10,
        us_epa_index, gb_defra_index
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, row)

    conn.commit()
    conn.close()
    print(f"✅ Weather data for {LOCATION} saved successfully.")

except Exception as e:
    print(f"❌ Failed to save data to database: {e}")
    exit(1)
