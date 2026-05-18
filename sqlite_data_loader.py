import sqlite3
import pandas as pd
import numpy as np # Ensure numpy is imported for general data handling

# --- SQLite Data Loading Tool ---
def load_data_from_sqlite(db_path: str, table_name_or_query: str):
    """
    Loads data from a SQLite database into a pandas DataFrame.

    Args:
        db_path (str): The path to the SQLite database file (e.g., 'path/to/your/database.db').
        table_name_or_query (str): The name of the table to load, or a full SQL SELECT query.

    Returns:
        pd.DataFrame: A DataFrame containing the data, or None if an error occurs.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        print(f"Successfully connected to SQLite database: {db_path}")

        # Check if it's a table name or a query
        if "SELECT" not in table_name_or_query.upper():
            # Assume it's a table name, construct a simple SELECT * query
            query = f"SELECT * FROM {table_name_or_query}"
            print(f"Loading data from table: {table_name_or_query}")
        else:
            query = table_name_or_query
            print(f"Executing custom query: {query}")

        df = pd.read_sql(query, conn)
        print(f"Successfully loaded {len(df)} rows. DataFrame shape: {df.shape}")
        return df
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    finally:
        if conn:
            conn.close()
            print("SQLite connection closed.")

# --- Example Usage (outside the agent for now) ---
if __name__ == '__main__':
    # Your selected database path
    DB_PATH = r"c:\Users\frank\Desktop\github\weather-project\weather.db" # Using raw string for backslashes

    # --- First, let's list tables in the database to see what's available ---
    print("
--- Listing tables in the database ---")
    list_tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
    tables_df = load_data_from_sqlite(DB_PATH, list_tables_query)
    if tables_df is not None:
        print("Tables found:")
        print(tables_df)
    else:
        print("Could not list tables. Check database path or permissions.")

    # --- Example 1: Loading a specific table (replace 'your_table_name' with an actual table from above) ---
    print("\n--- Loading data from 'weather_kristiansand' table ---")
    weather_data_df = load_data_from_sqlite(DB_PATH, "weather_kristiansand")
    if weather_data_df is not None:
        print("\nWeather Data (first 5 rows):")
        print(weather_data_df.head())
        print("\nWeather Data Info:")
        weather_data_df.info()

    print("\n--- Loading data using a custom SQL query from 'weather_kristiansand' ---")
    custom_query = "SELECT date, temperature FROM weather_kristiansand WHERE city = 'Kristiansand' ORDER BY date DESC LIMIT 10;"
    kristiansand_weather_df = load_data_from_sqlite(DB_PATH, custom_query)
    if kristiansand_weather_df is not None:
        print("\nKristiansand Weather Data (first 5 rows):")
        print(kristiansand_weather_df.head())

