import os
import smtplib
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_validator import validate_email, EmailNotValidError
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Store user reminder status in memory (for demo; use DB for production)
users = {}

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

scheduler = BackgroundScheduler()
scheduler.start()

# --- Helper to send email ---
def send_reminder_email(to_email):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = 'Task Reminder'
    body = 'This is your 12-hour reminder to check your tasks.'
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

# --- Scheduler job ---
def schedule_reminder(email):
    job_id = f"reminder_{email}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(lambda: send_reminder_email(email), 'interval', hours=12, id=job_id, replace_existing=True)

def stop_reminder(email):
    job_id = f"reminder_{email}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

# --- API Endpoints ---
@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    email = data.get('email')
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    users[email] = {'reminders': True}
    schedule_reminder(email)
    return jsonify({'success': True, 'message': 'Signed in and reminders started.'})

@app.route('/stop-reminders', methods=['POST'])
def stop_reminders():
    data = request.get_json()
    email = data.get('email')
    if email in users:
        users[email]['reminders'] = False
        stop_reminder(email)
        return jsonify({'success': True, 'message': 'Reminders stopped.'})
    return jsonify({'success': False, 'message': 'Email not found.'}), 400

@app.route('/status', methods=['GET'])
def status():
    return jsonify({'users': users})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
