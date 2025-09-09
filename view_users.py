import sqlite3

# Connect to your test.db
conn = sqlite3.connect("")
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("📋 Tables in your test.db:")
for table in tables:
    print("-", table[0])

# Show all users (if table exists)
try:
    cursor.execute("SELECT id, username, is_admin FROM users")
    users = cursor.fetchall()
    print("\n👥 Users:")
    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Is Admin: {user[2]}")
except Exception as e:
    print("❌ Error reading users table:", e)

conn.close()
