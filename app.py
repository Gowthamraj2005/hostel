import os
import json
from datetime import datetime

from flask import Flask, request, render_template, redirect
import psycopg2
from psycopg2.extras import DictCursor
import gspread
from google.oauth2.service_account import Credentials
from twilio.rest import Client


app = Flask(__name__)

# ==============================
# DATABASE CONNECTION (PostgreSQL)
# ==============================

def get_db_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            roll_number VARCHAR(20) PRIMARY KEY,
            name VARCHAR(100),
            department VARCHAR(20),
            room VARCHAR(20),
            student_phone VARCHAR(15),
            parent_phone VARCHAR(15)
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


# Initialize table at startup
init_db()
def get_student_details(roll_number):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("""
        SELECT name, room, department,student_phone, parent_phone
        FROM students
        WHERE roll_number = %s
    """, (roll_number,))

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result
# ==============================
# GOOGLE SHEETS CONFIG
# ==============================

def save_to_google_sheets(data):

    creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))

    credentials = Credentials.from_service_account_info(
        creds_json,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )

    gc = gspread.authorize(credentials)
    sheet = gc.open("Hostel Leave Records").sheet1
    sheet.append_row(data)


# ==============================
# TWILIO CONFIG
# ==============================

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_number = "whatsapp:+14155238886"

client = Client(account_sid, auth_token)


# ==============================
# TEMP STORAGE (Webhook Messages)
# ==============================

leave_requests = []


# ==============================
# RECEIVE STUDENT WHATSAPP MESSAGE
# ==============================

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():

    msg = request.form.get("Body")
    sender = request.form.get("From")

    leave_requests.append({
        "message": msg,
        "sender": sender,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    return "Received", 200


# ==============================
# WARDEN PANEL
# ==============================

@app.route("/", methods=["GET", "POST"])
def home():

    student_data = None

    if request.method == "POST":
        roll = request.form.get("roll")

        if roll:
            student = get_student_details(roll)
            if student:
                student_data = student

    return render_template("warden.html", 
                           requests=leave_requests,
                           student=student_data)


# ==============================
# APPROVE / REJECT LEAVE
# ==============================

@app.route("/approve", methods=["POST"])
def approve():

    roll_number = request.form.get("roll")
    reason = request.form.get("reason")
    start = request.form.get("start")
    end = request.form.get("end")
    days = request.form.get("days")
    principal = request.form.get("principal")
    action = request.form.get("action")

    student_data = get_student_details(roll_number)

    if not student_data:
        return "Student not found"

    name, room,department, student_phone, parent_phone = student_data

    message_body = f"""
LEAVE {action.upper()}

Student: {name}
Roll No: {roll_number}
Department&Year:{department}
Room: {room}
Reason: {reason}
Days: {days}
Start: {start}
End: {end}

By Warden
"""

    # Send WhatsApp only if Approved
    if action == "Approved":
        for number in [parent_phone, principal, student_phone]:
            if number:
                client.messages.create(
                    from_=twilio_number,
                    body=message_body,
                    to=f"whatsapp:+91{number}"
                )

    # Save to Google Sheets (for both Approved & Rejected)
    save_to_google_sheets([
        roll_number,
        name,
        department,
        room,
        reason,
        days,
        start,
        end,
        parent_phone,
        student_phone,
        action,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ])

    return redirect("/")


# ==============================
# ADD STUDENT (Admin Route)
# ==============================

@app.route("/add-student", methods=["POST"])
def add_student():

    roll = request.form.get("roll")
    name = request.form.get("name")
    department= request.form.get("department")
    room = request.form.get("room")
    student_phone = request.form.get("student_phone")
    parent_phone = request.form.get("parent_phone")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO students (roll_number, name,department, room, student_phone, parent_phone)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (roll_number) DO UPDATE
        SET name = EXCLUDED.name,
            room = EXCLUDED.room,
            student_phone = EXCLUDED.student_phone,
            parent_phone = EXCLUDED.parent_phone
    """, (roll, name, room, student_phone, parent_phone))

    conn.commit()
    cur.close()
    conn.close()

    return "Student Added / Updated Successfully"


# ==============================
# RUN APP
# ==============================

if __name__ == "__main__":
    app.run()





