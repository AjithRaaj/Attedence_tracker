from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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

    service_account_info = json.loads(
        os.environ["GOOGLE_CREDENTIALS"]
    )

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        service_account_info,
        scope
    )

else:

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json",
        scope
    )

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

    return jsonify({
        'success': False
    })

# =========================================
# ATTENDANCE
# =========================================
@app.route('/attendance', methods=['POST'])
def attendance():

    try:

        data = request.json

        emp_id = str(data.get('emp_id')).strip()
        otp = str(data.get('otp')).strip()
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        action = str(data.get('action')).strip()
        device_id = str(data.get('device_id')).strip()

        # =========================================
        # EMPLOYEE CHECK
        # =========================================
        employee = employees.get(emp_id)

        if not employee:

            return jsonify({
                'success': False,
                'message': 'Invalid Employee ID ❌'
            })

        # =========================================
        # OTP CHECK
        # =========================================
        if otp.upper() != employee['otp'].strip().upper():

            return jsonify({
                'success': False,
                'message': 'Wrong OTP ❌'
            })

        # =========================================
        # LOCATION CHECK
        # =========================================
        distance = geodesic(
            (OFFICE_LAT, OFFICE_LON),
            (lat, lon)
        ).meters

        if distance > ALLOWED_RADIUS:

            return jsonify({
                'success': False,
                'message': f'Outside Office Radius ({int(distance)}m) ❌'
            })

        # =========================================
        # INDIA TIME
        # =========================================
        now = datetime.now(ZoneInfo("Asia/Kolkata"))

        date_str = now.strftime('%d-%m-%Y')
        time_str = now.strftime('%I:%M %p')

        # =========================================
        # GET RECORDS
        # =========================================
        records = sheet.get_all_records()

        found_row = None

        # =========================================
        # FIND TODAY RECORD
        # =========================================
        for i, rec in enumerate(records, start=2):

            existing_emp = str(
                rec.get('Employee ID')
            ).strip()

            existing_date = str(
                rec.get('Date')
            ).strip()

            if existing_emp == emp_id and existing_date == date_str:

                found_row = i
                break

        # =========================================
        # DEVICE CHECK
        # =========================================
        for rec in records:

            existing_device = str(
                rec.get('Device ID')
            ).strip()

            existing_emp = str(
                rec.get('Employee ID')
            ).strip()

            if existing_device == device_id:

                if existing_emp != emp_id:

                    return jsonify({
                        'success': False,
                        'message': '❌ This mobile already used by another employee'
                    })

        # =========================================
        # PUNCH IN
        # =========================================
        if action == 'in':

            if found_row:

                return jsonify({
                    'success': False,
                    'message': 'Already Punched IN Today ✅'
                })

            current_minutes = now.hour * 60 + now.minute

            office_in = 9 * 60

            # =========================================
            # LATE CHECK
            # =========================================
            if current_minutes <= office_in:

                in_status = 'On Time'

            else:

                late = current_minutes - office_in

                in_status = f'{late} mins Late'

            # =========================================
            # SAVE TO SHEET
            # =========================================
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
                f"{lat}, {lon}"
            ])

            return jsonify({
                'success': True,
                'name': employee['name'],
                'date': date_str,
                'time': time_str,
                'status': in_status,
                'message': 'Punch IN Success ✅'
            })

        # =========================================
        # PUNCH OUT
        # =========================================
        elif action == 'out':

            if not found_row:

                return jsonify({
                    'success': False,
                    'message': 'Punch IN not found ❌'
                })

            out_time_existing = sheet.cell(
                found_row,
                5
            ).value

            if out_time_existing:

                return jsonify({
                    'success': False,
                    'message': 'Already Punched OUT Today ✅'
                })

            in_time = sheet.cell(
                found_row,
                4
            ).value

            current_minutes = now.hour * 60 + now.minute

            office_out = 17 * 60 + 30

            # =========================================
            # EARLY / EXTRA CHECK
            # =========================================
            if current_minutes < office_out:

                early = office_out - current_minutes

                out_status = f'{early} mins Early Exit'

            else:

                extra = current_minutes - office_out

                if extra == 0:

                    out_status = 'On Time Exit'

                else:

                    out_status = f'{extra} mins Extra Stay'

            # =========================================
            # WORKING HOURS CALCULATION
            # =========================================
            if not in_time:

                return jsonify({
                    'success': False,
                    'message': 'Punch IN time missing ❌'
                })

            in_datetime = datetime.strptime(
                in_time,
                '%I:%M %p'
            )

            out_datetime = datetime.strptime(
                time_str,
                '%I:%M %p'
            )

            # SAFE DIFFERENCE
            if out_datetime < in_datetime:

                out_datetime += timedelta(days=1)

            diff = out_datetime - in_datetime

            # =========================================
            # UPDATE SHEET
            # =========================================
            sheet.update_cell(found_row, 5, time_str)
            sheet.update_cell(found_row, 7, out_status)
            sheet.update_cell(found_row, 8, str(diff))

            return jsonify({
                'success': True,
                'name': employee['name'],
                'date': date_str,
                'time': time_str,
                'status': out_status,
                'working_hours': str(diff),
                'message': 'Punch OUT Success ✅'
            })

        # =========================================
        # INVALID ACTION
        # =========================================
        return jsonify({
            'success': False,
            'message': 'Invalid Action ❌'
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# =========================================
# RUN
# =========================================
if __name__ == '__main__':

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )