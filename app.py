# Install Streamlit

import requests
from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st # Import streamlit after installation

# NASA API details
API_KEY = "WDr0ktTUCgGiudcYuywslCOFPlPgWMdW3D298cDd"  # Replace with actual API key
BASE_URL = "https://api.nasa.gov/neo/rest/v1/feed"

# Define initial parameters
start_date = "2024-01-01"
end_date = "2024-01-07"
params = {
    "start_date": start_date,
    "end_date": end_date,
    "api_key": API_KEY
}

# Storage for extracted asteroid records
asteroid_data = []
count = 0

def extract_asteroid_info(asteroid):
    """Extract relevant asteroid details."""
    return {
        "id": asteroid.get("id"),
        "neo_reference_id": asteroid.get("neo_reference_id"),
        "name": asteroid.get("name"),
        "absolute_magnitude_h": float(asteroid.get("absolute_magnitude_h", 0)),
        "estimated_diameter_min_km": float(asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_min"]),
        "estimated_diameter_max_km": float(asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_max"]),
        "is_potentially_hazardous_asteroid": asteroid.get("is_potentially_hazardous_asteroid", False),
        "close_approach_date": datetime.strptime(asteroid["close_approach_data"][0]["close_approach_date"], "%Y-%m-%d").date(),
        "relative_velocity_kmph": float(asteroid["close_approach_data"][0]["relative_velocity"]["kilometers_per_hour"]),
        "astronomical": float(asteroid["close_approach_data"][0]["miss_distance"]["astronomical"]),
        "miss_distance_km": float(asteroid["close_approach_data"][0]["miss_distance"]["kilometers"]),
        "miss_distance_lunar": float(asteroid["close_approach_data"][0]["miss_distance"]["lunar"]),
        "orbiting_body": asteroid["close_approach_data"][0].get("orbiting_body", "Unknown")
    }

while count <= 10000:
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if "near_earth_objects" in data:
        for date, objects in data["near_earth_objects"].items():
            for asteroid in objects:
                try:
                    asteroid_entry = extract_asteroid_info(asteroid)
                    asteroid_data.append(asteroid_entry)
                    count += 1
                except (KeyError, TypeError, ValueError):
                    pass  # Skip incomplete records

    # Pagination Handling: Get next 7-day
    if "links" in data and "next" in data["links"]:
        next_url = data["links"]["next"]
        params["start_date"] = next_url.split("start_date=")[-1].split("&")[0]
        params["end_date"] = next_url.split("end_date=")[-1].split("&")[0]
    else:
        break  # Exit when no more pages exist

print(f"✅ Successfully extracted {len(asteroid_data)} asteroid records!")



# Assuming asteroid_data is already populated (from your extraction code)
# If in a separate script, use pickle, JSON or DB to load

#from requests import asteroid_data  # replace with actual import

# Connect to SQLite DB
conn = sqlite3.connect("asteroids.db")
cursor = conn.cursor()

# Create asteroids table
cursor.execute("""
CREATE TABLE IF NOT EXISTS asteroids (
    id INTEGER,
    name TEXT,
    absolute_magnitude_h FLOAT,
    estimated_diameter_min_km FLOAT,
    estimated_diameter_max_km FLOAT,
    is_potentially_hazardous_asteroid BOOLEAN
)
""")

# Create close_approach table
cursor.execute("""
CREATE TABLE IF NOT EXISTS close_approach (
    neo_reference_id INTEGER,
    close_approach_date DATE,
    relative_velocity_kmph FLOAT,
    astronomical FLOAT,
    miss_distance_km FLOAT,
    miss_distance_lunar FLOAT,
    orbiting_body TEXT
)
""")

# Insert records
for entry in asteroid_data:
    try:
        cursor.execute("""
            INSERT INTO asteroids VALUES (?, ?, ?, ?, ?, ?)
        """, (
            int(entry["id"]), entry["name"], entry["absolute_magnitude_h"],
            entry["estimated_diameter_min_km"], entry["estimated_diameter_max_km"],
            entry["is_potentially_hazardous_asteroid"]
        ))

        cursor.execute("""
            INSERT INTO close_approach VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            int(entry["neo_reference_id"]), entry["close_approach_date"],
            entry["relative_velocity_kmph"], entry["astronomical"],
            entry["miss_distance_km"], entry["miss_distance_lunar"],
            entry["orbiting_body"]
        ))
    except Exception as e:
        print(f"Skipping due to error: {e}")

conn.commit()
conn.close()
print("✅ Database populated successfully!")


# Connect to database
conn = sqlite3.connect("asteroids.db")
cursor = conn.cursor()

st.title("🚀 NASA Asteroid Explorer")

# --- Sidebar for Queries ---
st.sidebar.header("📊 Predefined Queries")
query_option = st.sidebar.selectbox("Choose a Query", [
    "1. Count how many times each asteroid has approached Earth",
    "2. Average velocity of each asteroid",
    "3. Top 10 fastest asteroids",
    "4. Hazardous asteroids with >3 approaches",
    "5. Month with most approaches",
    "6. Fastest ever approach",
    "7. Sort by max estimated diameter",
    "8. Asteroid getting closer over time",
    "9. Closest approach date & distance",
    "10. Asteroids > 50,000 km/h",
    "11. Count approaches per month",
    "12. Highest brightness (lowest magnitude)",
    "13. Hazardous vs Non-Hazardous",
    "14. Asteroids closer than Moon (1 LD)",
    "15. Asteroids < 0.05 AU"
])

queries = {
    "1": """
        SELECT name, COUNT(*) as approaches
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        GROUP BY name ORDER BY approaches DESC
    """,
    "2": """
        SELECT name, AVG(relative_velocity_kmph) as avg_velocity
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        GROUP BY name ORDER BY avg_velocity DESC
    """,
    "3": """
        SELECT name, MAX(relative_velocity_kmph) as max_velocity
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        GROUP BY name ORDER BY max_velocity DESC LIMIT 10
    """,
    "4": """
        SELECT name, COUNT(*) as count
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        WHERE is_potentially_hazardous_asteroid = 1
        GROUP BY name HAVING count > 3
    """,
    "5": """
        SELECT strftime('%Y-%m', close_approach_date) as month, COUNT(*) as approaches
        FROM close_approach GROUP BY month ORDER BY approaches DESC
    """,
    "6": """
        SELECT name, MAX(relative_velocity_kmph) as speed
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        ORDER BY speed DESC LIMIT 1
    """,
    "7": """
        SELECT name, estimated_diameter_max_km FROM asteroids
        ORDER BY estimated_diameter_max_km DESC LIMIT 10
    """,
    "8": """
        SELECT name, MIN(miss_distance_km) as closest, COUNT(*) as approaches
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        GROUP BY name ORDER BY approaches DESC LIMIT 10
    """,
    "9": """
        SELECT name, close_approach_date, MIN(miss_distance_km) as distance
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        GROUP BY name
    """,
    "10": """
        SELECT name, relative_velocity_kmph
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        WHERE relative_velocity_kmph > 50000
    """,
    "11": """
        SELECT strftime('%Y-%m', close_approach_date) as month, COUNT(*) as total
        FROM close_approach GROUP BY month ORDER BY total DESC
    """,
    "12": """
        SELECT name, MIN(absolute_magnitude_h) as brightness
        FROM asteroids
    """,
    "13": """
        SELECT is_potentially_hazardous_asteroid, COUNT(*) as total
        FROM asteroids GROUP BY is_potentially_hazardous_asteroid
    """,
    "14": """
        SELECT name, close_approach_date, miss_distance_lunar
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        WHERE miss_distance_lunar < 1
    """,
    "15": """
        SELECT name, close_approach_date, astronomical
        FROM asteroids JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
        WHERE astronomical < 0.05
    """
}

selected_num = query_option.split(".")[0]
query = queries[selected_num]

df = pd.read_sql_query(query, conn)
st.dataframe(df)

# Optional: Add filters at the bottom
st.sidebar.markdown("---")
st.sidebar.header("🔎 Custom Filters")

min_velocity = st.sidebar.slider("Min Velocity (km/h)", 0, 100000, 0)
max_ld = st.sidebar.slider("Max Lunar Distance", 0.0, 10.0, 10.0)
start_date = st.sidebar.date_input("From Date")
end_date = st.sidebar.date_input("To Date")

filtered_df = pd.read_sql_query(f"""
    SELECT * FROM asteroids
    JOIN close_approach ON asteroids.id = close_approach.neo_reference_id
    WHERE relative_velocity_kmph >= {min_velocity}
    AND miss_distance_lunar <= {max_ld}
    AND close_approach_date BETWEEN '{start_date}' AND '{end_date}'
""", conn)

st.subheader("📌 Filtered Results")

# 📊 Apply Filters Section
st.sidebar.header("🔎 Apply Filters")

# User-selectable filters
min_velocity = st.sidebar.slider("Minimum Velocity (km/h)", 0, 100000, 5000)
max_ld = st.sidebar.slider("Max Lunar Distance (LD)", 0.0, 10.0, 5.0)
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2025-01-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("2025-06-01"))

# Convert selected dates to string format for SQL
start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

# Checkbox for hazardous asteroids
hazardous_only = st.sidebar.checkbox("Show Only Hazardous Asteroids")
st.dataframe(filtered_df)
