from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from geopy.distance import geodesic
import json
import gspread
import os
import json

from oauth2client.service_account import (
    ServiceAccountCredentials
)

# =========================================
# FLASK APP
# =========================================

app = Flask(__name__)

# =========================================
# OFFICE LOCATION
# =========================================

OFFICE_LAT = 13.056600
OFFICE_LON = 80.2541370

ALLOWED_RADIUS = 35

# =========================================
# GOOGLE SHEETS SETUP
# =========================================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

google_creds = json.loads(
    os.environ['GOOGLE_CREDS']
)

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    google_creds,
    scope
)

client = gspread.authorize(creds)

# =========================================
# GOOGLE SHEET
# =========================================

SHEET_ID = "1Ryj_plY3dJ6v9ZCE_QJXuR7vXdFHqFOHWwJb0ODQ6Js"

sheet = client.open_by_key(
    SHEET_ID
).sheet1

# =========================================
# LOAD EMPLOYEES
# =========================================

with open("employees.json", "r") as f:
    employees = json.load(f)

# =========================================
# HOME PAGE
# =========================================

@app.route('/')
def home():

    return render_template('index.html')

# =========================================
# GET EMPLOYEE
# =========================================

@app.route('/get_employee', methods=['POST'])
def get_employee():

    data = request.json

    emp_id = data.get('emp_id')

    if emp_id in employees:

        emp = employees[emp_id]

        return jsonify({
            'success': True,
            'name': emp['name'],
            'phone': emp['phone']
        })

    return jsonify({
        'success': False,
        'message': 'Employee Not Found ❌'
    })

# =========================================
# LIVE EMPLOYEE COUNT
# =========================================

@app.route('/live_count')
def live_count():

    records = sheet.get_all_records()

    today = datetime.now().strftime('%d-%m-%Y')

    count = 0

    for rec in records:

        if rec['Date'] == today:
            count += 1

    return jsonify({
        'count': count
    })

# =========================================
# ATTENDANCE
# =========================================

@app.route('/attendance', methods=['POST'])
def attendance():

    data = request.json

    emp_id = data.get('emp_id')
    otp = data.get('otp')
    lat = float(data.get('lat'))
    lon = float(data.get('lon'))
    action = data.get('action')
    device_id = data.get('device_id')

    # =====================================
    # EMPLOYEE CHECK
    # =====================================

    if emp_id not in employees:

        return jsonify({
            'success': False,
            'message': 'Invalid Employee ID ❌'
        })

    employee = employees[emp_id]

    # =====================================
    # OTP CHECK
    # =====================================

    if otp.strip() != employee['otp']:

        return jsonify({
            'success': False,
            'message': 'Wrong OTP ❌'
        })

    # =====================================
    # LOCATION CHECK
    # =====================================

    office = (
        OFFICE_LAT,
        OFFICE_LON
    )

    employee_loc = (
        lat,
        lon
    )

    distance = geodesic(
        office,
        employee_loc
    ).meters

    if distance > ALLOWED_RADIUS:

        return jsonify({
            'success': False,
            'message': f'Outside Office Radius ({int(distance)}m) ❌'
        })

    # =====================================
    # DATE & TIME
    # =====================================

    now = datetime.now()

    date_str = now.strftime('%d-%m-%Y')

    time_str = now.strftime('%I:%M %p')

    records = sheet.get_all_records()

    found_row = None

    # =====================================
    # FIND TODAY RECORD
    # =====================================

    for i, rec in enumerate(records, start=2):

        if (
            str(rec['Employee ID']) == emp_id
            and rec['Date'] == date_str
        ):

            found_row = i
            break

    # =====================================
    # DEVICE CHECK
    # =====================================
    
    today = datetime.now().strftime('%d-%m-%Y')
    
    for rec in records:
    
        if (
        rec.get('Device ID') == device_id
        and str(rec['Employee ID']) != emp_id
        and rec['Date'] == today
        ):

            return jsonify({
                'success': False,
                'message': 'This Mobile Already Used ❌'
            })

    # =====================================
    # PUNCH IN
    # =====================================

    if action == 'in':

        if found_row:

            return jsonify({
                'success': False,
                'message': 'Already Punched IN ✅'
            })

        current_minutes = (
            now.hour * 60
            + now.minute
        )

        office_in = 9 * 60

        grace_limit = office_in + 5

        # =================================
        # IN STATUS
        # =================================

        if current_minutes <= grace_limit:

            in_status = 'On Time ✅'

        else:

            late = (
                current_minutes
                - office_in
            )

            in_status = (
                f'{late} mins Late ⏰'
            )

        # =================================
        # SAVE TO SHEET
        # =================================

        sheet.append_row([
            date_str,
            emp_id,
            employee['name'],
            time_str,
            '',
            in_status,
            '',
            '',
            device_id
        ])

        return jsonify({
            'success': True,
            'name': employee['name'],
            'date': date_str,
            'time': time_str,
            'status': in_status,
            'message': 'Punch IN Success ✅'
        })

    # =====================================
    # PUNCH OUT
    # =====================================

    elif action == 'out':

        if not found_row:

            return jsonify({
                'success': False,
                'message': 'Punch IN Not Found ❌'
            })

        out_time_existing = sheet.cell(
            found_row,
            5
        ).value

        if out_time_existing:

            return jsonify({
                'success': False,
                'message': 'Already Punched OUT ✅'
            })

        in_time = sheet.cell(
            found_row,
            4
        ).value

        current_minutes = (
            now.hour * 60
            + now.minute
        )

        office_out = (
            17 * 60
            + 30
        )

        grace_out = (
            office_out
            + 20
        )

        # =================================
        # OUT STATUS
        # =================================

        if current_minutes < office_out:

            early = (
                office_out
                - current_minutes
            )

            out_status = (
                f'{early} mins Early Exit 🚶'
            )

        elif current_minutes <= grace_out:

            out_status = 'On Time Exit ✅'

        else:

            extra = (
                current_minutes
                - office_out
            )

            out_status = (
                f'{extra} mins Additional Stay 🔥'
            )

        # =================================
        # WORKING HOURS
        # =================================

        try:

            in_datetime = datetime.strptime(
                in_time.strip(),
                '%I:%M %p'
            )

            out_datetime = datetime.strptime(
                time_str.strip(),
                '%I:%M %p'
            )

        except Exception:

            return jsonify({
                'success': False,
                'message': 'Time Format Error ❌'
            })

        # =================================
        # HANDLE NEXT DAY
        # =================================

        if out_datetime < in_datetime:

            out_datetime += timedelta(days=1)

        diff = out_datetime - in_datetime

        total_seconds = int(
            diff.total_seconds()
        )

        hours = total_seconds // 3600

        minutes = (
            total_seconds % 3600
        ) // 60

        working_hours = (
            f"{hours} hrs {minutes} mins"
        )

        # =================================
        # UPDATE SHEET
        # =================================

        sheet.update_cell(
            found_row,
            5,
            time_str
        )

        sheet.update_cell(
            found_row,
            7,
            out_status
        )

        sheet.update_cell(
            found_row,
            8,
            working_hours
        )

        return jsonify({
            'success': True,
            'name': employee['name'],
            'date': date_str,
            'time': time_str,
            'status': out_status,
            'working_hours': working_hours,
            'message': 'Punch OUT Success ✅'
        })

    # =====================================
    # INVALID ACTION
    # =====================================

    return jsonify({
        'success': False,
        'message': 'Invalid Action ❌'
    })

# =========================================
# RUN APP
# =========================================

if __name__ == '__main__':

    app.run(
        host='0.0.0.0',
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )