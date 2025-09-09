# kill_db_lock.py
import psutil

DB_NAME = ""

found = False

for proc in psutil.process_iter(['pid', 'name', 'open_files']):
    try:
        files = proc.info['open_files']
        if files:
            for f in files:
                if DB_NAME in f.path:
                    print(f"🔴 Found lock: PID {proc.pid} - {proc.name()}")
                    proc.kill()
                    print(f"✅ Killed process {proc.pid}")
                    found = True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

if not found:
    print("✅ No processes locking test.db found.")
else:
    print("🔁 Now try deleting test.db again.")

