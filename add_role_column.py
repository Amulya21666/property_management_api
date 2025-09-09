# add_role_column.py

import sqlite3

DB_PATH = ""  # Update if your DB is in a different path

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Try adding the 'role' column
    cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'owner'")
    conn.commit()
    print("✅ 'role' column added to users table.")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("⚠️ 'role' column already exists.")
    else:
        print("❌ Error adding role column:", e)

# Optional: Show updated columns
cursor.execute("PRAGMA table_info(users);")
columns = cursor.fetchall()
print("📋 Columns in users table:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

conn.close()
