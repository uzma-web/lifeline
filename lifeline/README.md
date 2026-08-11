# LifeLine — Blood Donor Emergency Network

A working Flask + SQLite web app that connects people who urgently need blood
with nearby, medically-eligible, compatible donors.

## What makes this more than a CRUD list

- **Blood-group compatibility engine** — a patient requesting O+ isn't just
  matched to O+ donors; the app applies real donor→recipient compatibility
  rules (e.g. O- is a universal donor, AB+ is a universal recipient).
- **90-day eligibility enforcement** — donors who gave blood recently are
  automatically hidden from results until they're medically eligible again,
  with a live countdown shown in the directory.
- **Privacy-respecting contact flow** — a requester sees compatible donors,
  but a donor's phone number is only revealed after the requester explicitly
  clicks "Notify donor" — donors aren't broadcast to the world by default.
- **Request lifecycle** — requests are `Open` until manually marked
  `Fulfilled`, so old emergencies don't clutter the active list.

## Tech stack

- **Backend:** Python 3, Flask
- **Database:** SQLite (single file, zero setup — swap for Postgres/MySQL
  later with almost no code change since it's plain SQL)
- **Frontend:** Server-rendered HTML templates (Jinja2) + hand-written CSS,
  no JS framework required

## Project structure

```
lifeline/
├── app.py              # Routes, matching logic, eligibility logic
├── seed.py             # Populates sample donors + a demo request
├── requirements.txt
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── home.html
    ├── register.html
    ├── donors.html
    ├── new_request.html
    └── request_detail.html
```

## Running it locally

```bash
cd lifeline
pip install -r requirements.txt

# first run only — creates lifeline.db and tables
python3 -c "from app import init_db; init_db()"

# optional — adds 10 sample donors + 1 sample request so the app
# isn't empty on first look
python3 seed.py

python3 app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Walking through the demo

1. Go to **Find donors** — see the seeded donor list; note one donor
   (Junaid Ahmed) shows "Eligible in ~70d" because he donated recently —
   he's automatically excluded from being contacted.
2. Go to the **home page** — click the seeded "Abdul Rasheed" request
   (O+, Critical). You'll see only compatible, eligible donors listed
   (O+ and O- donors in Chikkamagaluru).
3. Click **Notify donor** on one of them — their phone number appears,
   simulating what would trigger a real SMS/call integration.
4. Try **Request blood** to post a new request yourself, or **Become a
   donor** to register a new donor and see them appear in search.

## Extending this for a resume-ready pilot

- Swap the "Notify donor" simulation for a real SMS API (e.g. Twilio,
  Fast2SMS for India) — the hook is already isolated in `notify_donor()`
  in `app.py`.
- Add hospital/blood-bank verification before a request goes live.
- Deploy on Render/Railway/PythonAnywhere (all have free tiers) and get
  a handful of real donors from your own college to register — a live
  link with real users is a far stronger interview story than a local demo.

## Honesty note

This is a portfolio/demo project, not a certified medical system — donor
eligibility rules here are simplified for demonstration. A production
version would need proper medical oversight, verification, and data
protection review before real-world deployment.
