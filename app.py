from flask import Flask, render_template, request, jsonify
from datetime import datetime
from geopy.distance import geodesic
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

app = Flask(__name__)

# =========================================
# OFFICE LOCATION
# =========================================
OFFICE_LAT = 13.056600
OFFICE_LON = 80.2541370
ALLOWED_RADIUS = 30  # meters

# =========================================
# GOOGLE SHEETS SETUP
# =========================================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

if os.environ.get("GOOGLE_CREDENTIALS"):
    service_account_info = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
else:
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)

client = gspread.authorize(creds)

SHEET_ID = "1Ryj_plY3dJ6v9ZCE_QJXuR7vXdFHqFOHWwJb0ODQ6Js"
sheet = client.open_by_key(SHEET_ID).sheet1

# =========================================
# EMPLOYEE DATA
# =========================================
with open('employees.json', 'r') as f:
    employees = json.load(f)

# =========================================
# HOME
# =========================================
@app.route('/')
def home():
    return render_template('index.html')

# =========================================
# GET EMPLOYEE
# =========================================
@app.route('/get_employee', methods=['POST'])
def get_employee():
    emp_id = request.json.get('emp_id')

    emp = employees.get(emp_id)

    if emp:
        return jsonify({
            'success': True,
            'name': emp['name'],
            'phone': emp['phone']
        })

    return jsonify({'success': False})

# =========================================
# ATTENDANCE
# =========================================
@app.route('/attendance', methods=['POST'])
def attendance():

    try:
        data = request.json

        emp_id = data.get('emp_id')
        otp = data.get('otp')
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        action = data.get('action')
        device_id = data.get('device_id')

        # EMP CHECK
        employee = employees.get(emp_id)
        if not employee:
            return jsonify({'success': False, 'message': 'Invalid Employee ID ❌'})

        # OTP CHECK
        if otp.strip().upper() != employee['otp'].upper():
            return jsonify({'success': False, 'message': 'Wrong OTP ❌'})

        # LOCATION CHECK
        distance = geodesic(
            (OFFICE_LAT, OFFICE_LON),
            (lat, lon)
        ).meters

        if distance > ALLOWED_RADIUS:
            return jsonify({
                'success': False,
                'message': f'Outside Office Radius ({int(distance)}m) ❌'
            })

        now = datetime.now()
        date_str = now.strftime('%d-%m-%Y')
        time_str = now.strftime('%I:%M %p')

        records = sheet.get_all_records()

        found_row = None

        # FIND TODAY RECORD
        for i, rec in enumerate(records, start=2):
            if str(rec.get('Employee ID')) == emp_id and str(rec.get('Date')) == date_str:
                found_row = i
                break

        # DEVICE CHECK (SAFE)
        for rec in records:
            if rec.get('Device ID') == device_id:
                if str(rec.get('Employee ID')) != emp_id:
                    return jsonify({
                        'success': False,
                        'message': 'This mobile already used by another employee ❌'
                    })

        # PUNCH IN
        if action == 'in':

            if found_row:
                return jsonify({'success': False, 'message': 'Already Punched IN Today ✅'})

            current_minutes = now.hour * 60 + now.minute
            office_in = 9 * 60

            if current_minutes <= office_in:
                in_status = 'On Time'
            else:
                in_status = f'{current_minutes - office_in} mins Late'

            sheet.append_row([
                date_str,
                emp_id,
                employee['name'],
                time_str,
                '',
                in_status,
                '',
                '',
                device_id,
                ''
            ])

            return jsonify({
                'success': True,
                'name': employee['name'],
                'date': date_str,
                'time': time_str,
                'status': in_status,
                'message': 'Punch IN Success ✅'
            })

        # PUNCH OUT
        elif action == 'out':

            if not found_row:
                return jsonify({'success': False, 'message': 'Punch IN not found ❌'})

            out_time_existing = sheet.cell(found_row, 5).value

            if out_time_existing:
                return jsonify({'success': False, 'message': 'Already Punched OUT Today ✅'})

            in_time = sheet.cell(found_row, 4).value

            current_minutes = now.hour * 60 + now.minute
            office_out = 17 * 60 + 30

            if current_minutes < office_out:
                out_status = f'{office_out - current_minutes} mins Early Exit'
            else:
                extra = current_minutes - office_out
                out_status = 'On Time Exit' if extra == 0 else f'{extra} mins Extra Stay'

            in_datetime = datetime.strptime(in_time, '%I:%M %p')
            out_datetime = datetime.strptime(time_str, '%I:%M %p')

            diff = out_datetime - in_datetime

            sheet.update_cell(found_row, 5, time_str)
            sheet.update_cell(found_row, 7, out_status)
            sheet.update_cell(found_row, 8, str(diff))

            return jsonify({
                'success': True,
                'name': employee['name'],
                'date': date_str,
                'time': time_str,
                'status': out_status,
                'message': 'Punch OUT Success ✅'
            })

        return jsonify({'success': False})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({'success': False, 'message': 'Server Error ❌'})

# =========================================
# RUN
# =========================================
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)