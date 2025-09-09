import sqlite3

conn = sqlite3.connect("test.db")
cursor = conn.cursor()

# Add the 'image' column if it doesn't exist
try:
    cursor.execute("""
    ALTER TABLE appliances
    ADD COLUMN image TEXT DEFAULT 'default_appliance.png';
    """)
    print("Column 'image' added successfully!")
except sqlite3.OperationalError as e:
    print("Column already exists or error:", e)

conn.commit()
conn.close()
