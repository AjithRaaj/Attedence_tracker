// ✅ Generate or reuse device ID
function getDeviceId() {
    let deviceId = localStorage.getItem("device_id");
    if (!deviceId) {
        // Use crypto for stronger unique ID
        deviceId = 'DEV-' + crypto.randomUUID();
        localStorage.setItem("device_id", deviceId);
    }
    return deviceId;
}

// ✅ Load employee details
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

        if (!response.ok) {
            throw new Error("Server error: " + response.status);
        }

        const data = await response.json();

        if (data.success) {
            document.getElementById("name").value = data.name;
            document.getElementById("phone").value = data.phone;
        } else {
            alert("Employee not found ❌");
        }
    } catch (err) {
        alert("Error loading employee ❌");
        console.error(err);
    }
}

// ✅ Mark attendance (Punch IN / OUT)
function markAttendance(action) {
    if (!navigator.geolocation) {
        alert("Geolocation not supported ❌");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async function (position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const emp_id = document.getElementById('emp_id').value;

            if (!emp_id) {
                alert("Employee ID required ❌");
                return;
            }

            // Get OTP from input field instead of prompt
            const otp = document.getElementById("otp") ? document.getElementById("otp").value : null;
            if (!otp) {
                alert("OTP required ❌");
                return;
            }

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

                if (!response.ok) {
                    throw new Error("Server error: " + response.status);
                }

                const data = await response.json();

                if (data.success) {
                    // Show result inside page if #status exists, else fallback to alert
                    const statusDiv = document.getElementById("status");
                    const message = `${data.name}\n${data.message}\nDate : ${data.date}\nTime : ${data.time}\nStatus : ${data.status}`;
                    if (statusDiv) {
                        statusDiv.innerText = message;
                    } else {
                        alert(message);
                    }
                } else {
                    alert(data.message || "Attendance failed ❌");
                }
            } catch (err) {
                alert("Error marking attendance ❌");
                console.error(err);
            }
        },
        function (error) {
            if (error.code === 1) {
                alert("Please Allow Location Permission ❌");
            } else if (error.code === 2) {
                alert("Location unavailable ❌");
            } else if (error.code === 3) {
                alert("Location request timeout ❌");
            } else {
                alert("Location error ❌");
            }
        },
        {
            enableHighAccuracy: true,
            timeout: 10000, // 10 seconds
            maximumAge: 0
        }
    );
}