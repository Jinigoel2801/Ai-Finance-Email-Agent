"""Clean all old audit records to start fresh with the new CSV data."""
import sqlite3

conn = sqlite3.connect('audit_log.db')
deleted = conn.execute("DELETE FROM email_audit").rowcount
conn.commit()
print(f"Cleaned {deleted} old records from audit_log.db. Database is now empty.")
conn.close()