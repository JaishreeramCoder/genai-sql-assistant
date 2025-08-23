# pip install sqlitecloud
import sqlitecloud

# Connect to SQLite Cloud
conn = sqlitecloud.connect("sqlitecloud://cbwb6jhxhk.g1.sqlite.cloud:8860/auth.sqlitecloud?apikey=tzKSY69TJgit4JxRZqGYxSSSXXn5EWfmoYezjolRdn8")

# List all tables in uploaded_db.sqlite
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables in uploaded_db.sqlite:", tables)

# Example: fetch 5 rows from the first table
if tables:
    table_name = tables[0][0]  # take first table
    cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 5;")
    rows = cursor.fetchall()
    print(f"\nFirst 5 rows from table '{table_name}':")
    for row in rows:
        print(row)
