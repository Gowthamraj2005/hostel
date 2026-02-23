import gspread
from google.oauth2.service_account import Credentials
import json 
from flask import Flask, request, render_template, redirect
from twilio.rest import Client
from datetime import datetime
import os

app = Flask(__name__)
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

# ---------------- TWILIO CONFIG ----------------
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_number = "whatsapp:+14155238886"

client = Client(account_sid, auth_token)

# Temporary storage
leave_requests = []

# ---------------- RECEIVE STUDENT MESSAGE ----------------
@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    msg = request.form.get("Body")
    sender = request.form.get("From")

    leave_requests.append({
        "message": msg,
        "sender": sender
    })

    return "Received", 200


# ---------------- WARDEN PANEL ----------------
@app.route("/")
def home():
    return render_template("warden.html", requests=leave_requests)


# ---------------- APPROVAL ----------------
@app.route("/approve", methods=["POST"])
def approve():

    name = request.form.get("name")
    room = request.form.get("room")
    reason = request.form.get("reason")
    start = request.form.get("start")
    end = request.form.get("end")
    days = request.form.get("days")
    father = request.form.get("father")
    principal = request.form.get("principal")
    student = request.form.get("student")

    message_body = f"""
LEAVE APPROVED ✅

Student: {name}
Room: {room}
Reason: {reason}
Days: {days}
Start Date: {start}
End Date: {end}

Approved by Warden.
"""

    # Send WhatsApp
    # Send WhatsApp
for number in [father, principal, student]:
    if number:
        number = number.strip()

        # Remove + if user added it
        if number.startswith("+"):
            number = number[1:]

        # If already has 91 prefix
        if number.startswith("91") and len(number) == 12:
            final_number = f"+{number}"
        else:
            final_number = f"+91{number}"

        client.messages.create(
            from_=twilio_number,
            body=message_body,
            to=f"whatsapp:{final_number}"
        )
    # ✅ Save to Google Sheets (INSIDE FUNCTION)
    save_to_google_sheets([
        name,
        room,
        reason,
        days,
        start,
        end,
        father,
        principal,
        student,
        "Approved"
    ])

    return redirect("/")


if __name__ == "__main__":
    app.run()





