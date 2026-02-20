from flask import Flask, request, render_template, redirect
from twilio.rest import Client
from datetime import datetime
import os

app = Flask(__name__)

# ---------------- TWILIO CONFIG ----------------
account_sid = ""
auth_token = ""
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

    name = request.form["name"]
    room = request.form["room"]
    reason = request.form["reason"]
    start = request.form["start"]
    end = request.form["end"]
    days = request.form["days"]
    father = request.form["father"]
    principal = request.form["principal"]
    student = request.form["student"]

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
    for number in [father, principal, student]:
        client.messages.create(
            from_=twilio_number,
            body=message_body,
            to=f"whatsapp:{number}"
        )

    return redirect("/")


if __name__ == "__main__":
    app.run()
