import sqlite3

# Connect to database
connection = sqlite3.connect("data/database/spam_database.db")

cursor = connection.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS spam_numbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mobile_number TEXT UNIQUE NOT NULL,
    spam_reports INTEGER DEFAULT 0,
    genuine_reports INTEGER DEFAULT 0,
    trust_score REAL DEFAULT 50,
    status TEXT DEFAULT 'Unknown'
)
""")

connection.commit()
connection.close()

print("Database created successfully!")


# Add demo data
connection = sqlite3.connect("data/database/spam_database.db")

cursor = connection.cursor()

# 1. Genuine Number
cursor.execute("""
INSERT OR IGNORE INTO spam_numbers
(mobile_number, spam_reports, genuine_reports, trust_score, status)
VALUES
('9876543210', 2, 8, 80, 'Genuine')
""")


# 2. Spam Number
cursor.execute("""
INSERT OR IGNORE INTO spam_numbers
(mobile_number, spam_reports, genuine_reports, trust_score, status)
VALUES
('9123456789', 15, 1, 20, 'Spam')
""")


# 3. Suspicious Number
cursor.execute("""
INSERT OR IGNORE INTO spam_numbers
(mobile_number, spam_reports, genuine_reports, trust_score, status)
VALUES
('9000000001', 5, 5, 50, 'Suspicious')
""")


connection.commit()
connection.close()

print("Sample data added successfully!")