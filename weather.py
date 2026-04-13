import requests
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "weather.db"

# API key
API_KEY = os.getenv("WEATHER_API_KEY")

if not API_KEY:
    raise ValueError("Missing WEATHER_API_KEY")


import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "weather.db"
API_KEY = os.getenv("WEATHER_API_KEY")

if not API_KEY:
    raise ValueError("Missing WEATHER_API_KEY")

# ONLY Kristiansand (as requested)
LOCATION = "Kristiansand"


url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={LOCATION}&aqi=yes"

# -------------------------
# FETCH DATA
# -------------------------
response = requests.get(url, timeout=10)

if response.status_code != 200:
    raise Exception(f"API error: {response.status_code} - {response.text}")

data = response.json()

# -------------------------
# CONNECT DB
# -------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -------------------------
# CREATE TABLE (FULL FLAT STRUCTURE)
# -------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS weather_kristiansand (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- location
    name TEXT,
    region TEXT,
    country TEXT,
    lat REAL,
    lon REAL,
    tz_id TEXT,
    localtime TEXT,

    -- current weather
    last_updated TEXT,
    temp_c REAL,
    temp_f REAL,
    is_day INTEGER,
    condition_text TEXT,
    wind_mph REAL,
    wind_kph REAL,
    wind_degree INTEGER,
    wind_dir TEXT,
    pressure_mb REAL,
    precip_mm REAL,
    humidity INTEGER,
    cloud INTEGER,
    feelslike_c REAL,
    feelslike_f REAL,
    windchill_c REAL,
    windchill_f REAL,
    heatindex_c REAL,
    heatindex_f REAL,
    dewpoint_c REAL,
    dewpoint_f REAL,
    vis_km REAL,
    uv REAL,
    gust_kph REAL,

    -- air quality
    co REAL,
    no2 REAL,
    o3 REAL,
    so2 REAL,
    pm2_5 REAL,
    pm10 REAL,
    us_epa_index INTEGER,
    gb_defra_index INTEGER
)
""")

# -------------------------
# EXTRACT VALUES SAFELY
# -------------------------
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

# -------------------------
# INSERT
# -------------------------

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

print(f"✅ Full Kristiansand weather data saved")

# ✅ FETCH DATA (THIS WAS MISSING)
response = requests.get(url)

if response.status_code != 200:
    raise Exception(f"API error: {response.status_code} - {response.text}")

data = response.json()

# Extract
weather_info = (
    data['location']['name'],
    data['location']['localtime'],
    data['current']['temp_c'],
    data['current']['humidity'],
    data['current']['condition']['text'],
    data['current']['wind_kph'],
    data['current']['pressure_mb']
)

# Connect SQLite
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS weather_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT,
    time_stamp TEXT,
    temp_c REAL,
    humidity INTEGER,
    cond TEXT,
    wind_kph REAL,
    pressure_mb REAL
)
""")

# Insert
cursor.execute("""
INSERT INTO weather_data (
    location, time_stamp, temp_c, humidity, cond, wind_kph, pressure_mb
) VALUES (?, ?, ?, ?, ?, ?, ?)
""", weather_info)

conn.commit()
conn.close()

print("✅ Weather data saved to SQLite")