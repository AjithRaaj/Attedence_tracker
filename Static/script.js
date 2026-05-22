// SAFE DEVICE ID
function getDeviceId() {
    let deviceId = localStorage.getItem("device_id");
    if (!deviceId) {
        deviceId = 'DEV-' + Math.random().toString(36).substring(2) + Date.now();
        localStorage.setItem("device_id", deviceId);
    }
    return deviceId;
}

// LOAD EMPLOYEE
async function loadEmployee() {
    const empId = document.getElementById("emp_id").value;

    if (!empId) {
        alert("Employee ID required ❌");
        return;
    }

    try {
        const response = await fetch("/get_employee", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ emp_id: empId })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById("name").value = data.name;
            document.getElementById("phone").value = data.phone;
        } else {
            alert("Employee not found ❌");
        }
    } catch (err) {
        console.error(err);
        alert("Server error ❌");
    }
}

// ATTENDANCE
function markAttendance(action) {

    const emp_id = document.getElementById("emp_id").value;
    const otp = document.getElementById("otp").value;

    if (!emp_id) {
        alert("Employee ID required ❌");
        return;
    }

    if (!otp) {
        alert("OTP required ❌");
        return;
    }

    if (!navigator.geolocation) {
        alert("Geolocation not supported ❌");
        return;
    }

    navigator.geolocation.getCurrentPosition(async function (position) {

        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const device_id = getDeviceId();

        try {
            const response = await fetch('/attendance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    emp_id,
                    otp,
                    lat,
                    lon,
                    action,
                    device_id
                })
            });

            const data = await response.json();

            const statusDiv = document.getElementById("status");

            if (data.success) {
                statusDiv.innerText =
                    `${data.name}\n${data.message}\n${data.date} ${data.time}`;
            } else {
                alert(data.message || "Attendance failed ❌");
            }

        } catch (err) {
            console.error(err);
            alert("Server error ❌");
        }

    }, function (error) {
        alert("Location permission required ❌");
    });
}