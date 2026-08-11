import sqlite3
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = "lifeline-dev-secret"
DB_PATH = "lifeline.db"

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
ELIGIBILITY_GAP_DAYS = 90  # standard minimum gap between whole-blood donations

# Compatibility chart: who each blood group CAN donate to (recipient groups)
DONATION_COMPATIBILITY = {
    "O-":  ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+":  ["O+", "A+", "B+", "AB+"],
    "A-":  ["A-", "A+", "AB-", "AB+"],
    "A+":  ["A+", "AB+"],
    "B-":  ["B-", "B+", "AB-", "AB+"],
    "B+":  ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            area TEXT,
            last_donation_date TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            hospital TEXT NOT NULL,
            city TEXT NOT NULL,
            units_needed INTEGER NOT NULL DEFAULT 1,
            urgency TEXT NOT NULL DEFAULT 'Normal',
            contact_phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            donor_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Notified',
            responded_at TEXT NOT NULL,
            FOREIGN KEY (request_id) REFERENCES requests (id),
            FOREIGN KEY (donor_id) REFERENCES donors (id)
        );
        """
    )
    db.commit()
    db.close()


def is_eligible(last_donation_date_str):
    """A donor is eligible if it's been >= ELIGIBILITY_GAP_DAYS since last donation,
    or they have never donated before."""
    if not last_donation_date_str:
        return True, None
    last = datetime.strptime(last_donation_date_str, "%Y-%m-%d").date()
    next_eligible = last + timedelta(days=ELIGIBILITY_GAP_DAYS)
    return date.today() >= next_eligible, next_eligible


def days_until_eligible(last_donation_date_str):
    eligible, next_date = is_eligible(last_donation_date_str)
    if eligible:
        return 0
    return (next_date - date.today()).days


@app.route("/")
def home():
    db = get_db()
    donor_count = db.execute("SELECT COUNT(*) c FROM donors").fetchone()["c"]
    open_requests = db.execute(
        "SELECT COUNT(*) c FROM requests WHERE status = 'Open'"
    ).fetchone()["c"]
    recent_requests = db.execute(
        "SELECT * FROM requests ORDER BY created_at DESC LIMIT 4"
    ).fetchall()
    return render_template(
        "home.html",
        donor_count=donor_count,
        open_requests=open_requests,
        recent_requests=recent_requests,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        blood_group = request.form["blood_group"]
        phone = request.form["phone"].strip()
        city = request.form["city"].strip()
        area = request.form.get("area", "").strip()
        last_donation = request.form.get("last_donation_date") or None

        if not name or not phone or not city or blood_group not in BLOOD_GROUPS:
            flash("Please fill in all required fields correctly.", "error")
            return render_template(
                "register.html", blood_groups=BLOOD_GROUPS, form=request.form
            )

        db = get_db()
        db.execute(
            """INSERT INTO donors (name, blood_group, phone, city, area, last_donation_date, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, blood_group, phone, city, area, last_donation, datetime.now().isoformat()),
        )
        db.commit()
        flash(f"Thank you, {name}. You're registered as a {blood_group} donor.", "success")
        return redirect(url_for("donors_list"))

    return render_template("register.html", blood_groups=BLOOD_GROUPS, form={})


@app.route("/donors")
def donors_list():
    db = get_db()
    blood_group = request.args.get("blood_group", "")
    city = request.args.get("city", "")

    query = "SELECT * FROM donors WHERE 1=1"
    params = []
    if blood_group:
        query += " AND blood_group = ?"
        params.append(blood_group)
    if city:
        query += " AND city LIKE ?"
        params.append(f"%{city}%")
    query += " ORDER BY created_at DESC"

    rows = db.execute(query, params).fetchall()
    donors = []
    for r in rows:
        eligible, next_date = is_eligible(r["last_donation_date"])
        donors.append(
            {
                **dict(r),
                "eligible": eligible,
                "next_eligible_date": next_date.isoformat() if next_date else None,
                "days_left": days_until_eligible(r["last_donation_date"]),
            }
        )

    return render_template(
        "donors.html",
        donors=donors,
        blood_groups=BLOOD_GROUPS,
        selected_group=blood_group,
        selected_city=city,
    )


@app.route("/request/new", methods=["GET", "POST"])
def new_request():
    if request.method == "POST":
        patient_name = request.form["patient_name"].strip()
        blood_group = request.form["blood_group"]
        hospital = request.form["hospital"].strip()
        city = request.form["city"].strip()
        units_needed = request.form.get("units_needed", 1)
        urgency = request.form.get("urgency", "Normal")
        contact_phone = request.form["contact_phone"].strip()

        if not patient_name or not hospital or not city or not contact_phone or blood_group not in BLOOD_GROUPS:
            flash("Please fill in all required fields correctly.", "error")
            return render_template("new_request.html", blood_groups=BLOOD_GROUPS, form=request.form)

        db = get_db()
        cur = db.execute(
            """INSERT INTO requests (patient_name, blood_group, hospital, city, units_needed,
                                      urgency, contact_phone, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', ?)""",
            (patient_name, blood_group, hospital, city, units_needed, urgency, contact_phone,
             datetime.now().isoformat()),
        )
        db.commit()
        request_id = cur.lastrowid
        return redirect(url_for("request_detail", request_id=request_id))

    return render_template("new_request.html", blood_groups=BLOOD_GROUPS, form={})


@app.route("/request/<int:request_id>")
def request_detail(request_id):
    db = get_db()
    req = db.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
    if req is None:
        flash("Request not found.", "error")
        return redirect(url_for("home"))

    compatible_groups = DONATION_COMPATIBILITY_REVERSE.get(req["blood_group"], [req["blood_group"]])

    placeholders = ",".join("?" for _ in compatible_groups)
    donor_rows = db.execute(
        f"""SELECT * FROM donors
            WHERE blood_group IN ({placeholders}) AND city LIKE ?
            ORDER BY created_at DESC""",
        (*compatible_groups, f"%{req['city']}%"),
    ).fetchall()

    matches = []
    for r in donor_rows:
        eligible, next_date = is_eligible(r["last_donation_date"])
        if eligible:
            matches.append({**dict(r), "next_eligible_date": None})

    responded = db.execute(
        "SELECT donor_id, status FROM responses WHERE request_id = ?", (request_id,)
    ).fetchall()
    responded_ids = {row["donor_id"]: row["status"] for row in responded}

    return render_template(
        "request_detail.html",
        req=req,
        matches=matches,
        responded_ids=responded_ids,
        match_count=len(matches),
    )


@app.route("/request/<int:request_id>/notify/<int:donor_id>", methods=["POST"])
def notify_donor(request_id, donor_id):
    db = get_db()
    existing = db.execute(
        "SELECT id FROM responses WHERE request_id = ? AND donor_id = ?",
        (request_id, donor_id),
    ).fetchone()
    if not existing:
        db.execute(
            "INSERT INTO responses (request_id, donor_id, status, responded_at) VALUES (?, ?, 'Notified', ?)",
            (request_id, donor_id, datetime.now().isoformat()),
        )
        db.commit()
    flash("Donor notified. In a live deployment this would trigger an SMS/call.", "success")
    return redirect(url_for("request_detail", request_id=request_id))


@app.route("/request/<int:request_id>/resolve", methods=["POST"])
def resolve_request(request_id):
    db = get_db()
    db.execute("UPDATE requests SET status = 'Fulfilled' WHERE id = ?", (request_id,))
    db.commit()
    flash("Request marked as fulfilled. Thank you for updating the record.", "success")
    return redirect(url_for("request_detail", request_id=request_id))


# Build reverse compatibility: for a patient needing blood group X, which donor
# groups CAN donate TO them.
DONATION_COMPATIBILITY_REVERSE = {}
for donor_group, recipients in DONATION_COMPATIBILITY.items():
    for recipient_group in recipients:
        DONATION_COMPATIBILITY_REVERSE.setdefault(recipient_group, []).append(donor_group)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
