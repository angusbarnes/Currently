import sqlite3
import csv

# Connect to the database
conn = sqlite3.connect('../sensitive/modbus_data.db')
cursor = conn.cursor()

# Execute the query
cursor.execute("SELECT * FROM modbus_logs LIMIT 25")

# Get column names
columns = [description[0] for description in cursor.description]

# Write to CSV
with open('top25.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(columns)
    writer.writerows(cursor.fetchall())

conn.close()
