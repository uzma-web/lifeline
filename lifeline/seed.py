"""Populate the database with sample donors and a sample request so the app
is demo-ready immediately after setup. Safe to re-run (clears old data first)."""
import sqlite3
from datetime import datetime, timedelta

from app import init_db, DB_PATH

init_db()

donors = [
    ("Ayesha Khan", "O+", "9845011122", "Chikkamagaluru", "MG Road", None),
    ("Ravi Shetty", "O-", "9845011123", "Chikkamagaluru", "Kalasa Road", None),
    ("Meera Iyer", "A+", "9845011124", "Chikkamagaluru", "Coffee Board Layout", (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")),
    ("Junaid Ahmed", "B+", "9845011125", "Chikkamagaluru", "Birur Road", (datetime.now() - timedelta(days=20)).strftime("%Y-%m-%d")),
    ("Divya Prasad", "AB+", "9845011126", "Chikkamagaluru", "M G Road", None),
    ("Suhail Rahman", "O+", "9845011127", "Chikkamagaluru", "Rugvedapura", None),
    ("Kavya Nair", "A-", "9845011128", "Chikkamagaluru", "Balehonnur Road", None),
    ("Prakash Gowda", "B-", "9845011129", "Chikkamagaluru", "IG Road", (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")),
    ("Fathima Sheikh", "O+", "9845011130", "Bengaluru", "BTM Layout", None),
    ("Naveen Kumar", "AB-", "9845011131", "Bengaluru", "Jayanagar", None),
]

requests = [
    ("Abdul Rasheed", "O+", "District Hospital", "Chikkamagaluru", 2, "Critical", "9845099999"),
]

db = sqlite3.connect(DB_PATH)
db.execute("DELETE FROM responses")
db.execute("DELETE FROM requests")
db.execute("DELETE FROM donors")

for name, bg, phone, city, area, last_donation in donors:
    db.execute(
        """INSERT INTO donors (name, blood_group, phone, city, area, last_donation_date, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, bg, phone, city, area, last_donation, datetime.now().isoformat()),
    )

for patient, bg, hospital, city, units, urgency, phone in requests:
    db.execute(
        """INSERT INTO requests (patient_name, blood_group, hospital, city, units_needed,
                                  urgency, contact_phone, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', ?)""",
        (patient, bg, hospital, city, units, urgency, phone, datetime.now().isoformat()),
    )

db.commit()
db.close()
print(f"Seeded {len(donors)} donors and {len(requests)} request(s).")
